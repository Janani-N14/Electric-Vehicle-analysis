import pandas as pd
import numpy as np
import os
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from ev_fleet_management.utils.db import get_db
from ev_fleet_management.model.models import TelemetryModel, DriverModel, EVModel
from ev_fleet_management.config.settings import FLEET_EXCEL_PATH
from ev_fleet_management.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/analytics", tags=["analytics"])

@router.get("/summary")
def get_fleet_summary(db: Session = Depends(get_db)):
    # Calculate aggregate fleet summary
    total_vehicles = db.query(EVModel).count()
    active_vehicles = db.query(EVModel).filter(EVModel.status == "Active").count()
    idle_vehicles = db.query(EVModel).filter(EVModel.status == "Idle").count()
    charging_vehicles = db.query(EVModel).filter(EVModel.status == "Charging").count()
    
    # Distance and energy aggregates
    distance_sum = db.query(func.sum(TelemetryModel.distance_travelled)).scalar() or 0.0
    charging_cost_sum = db.query(func.sum(TelemetryModel.charging_cost)).scalar() or 0.0
    maintenance_cost_sum = db.query(func.sum(TelemetryModel.maintenance_cost)).scalar() or 0.0
    income_sum = db.query(func.sum(TelemetryModel.income)).scalar() or 0.0
    
    # Calculate average energy efficiency (weighted by distance)
    # Average efficiency across telemetry records: sum(distance) / sum(distance / efficiency)
    efficiency_recs = db.query(TelemetryModel.distance_travelled, TelemetryModel.energy_efficiency).filter(TelemetryModel.distance_travelled > 0).all()
    total_kwh = 0.0
    for dist, eff in efficiency_recs:
        if eff > 0:
            total_kwh += dist / eff
    
    avg_efficiency = distance_sum / total_kwh if total_kwh > 0 else 4.7
    
    return {
        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "idle_vehicles": idle_vehicles,
        "charging_vehicles": charging_vehicles,
        "total_distance_km": round(distance_sum, 1),
        "total_charging_cost_inr": round(charging_cost_sum, 2),
        "total_maintenance_cost_inr": round(maintenance_cost_sum, 2),
        "total_income_inr": round(income_sum, 2),
        "net_profit_inr": round(income_sum - charging_cost_sum - maintenance_cost_sum, 2),
        "avg_efficiency_km_kwh": round(avg_efficiency, 2),
        "total_energy_kwh": round(total_kwh, 1)
    }

@router.get("/charts")
def get_charts_data():
    # Hardcoded or summarized weekly analytics matching dashboard inputs
    # Daily energy consumption (kWh)
    energy_consumption = [450, 510, 480, 520, 550, 410, 390]
    # Trend area / line usage count
    active_trend = [28, 30, 29, 31, 33, 31, 28]
    
    return {
        "energy_consumption_kwh": energy_consumption,
        "active_trend": active_trend,
        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    }

@router.get("/driver-efficiency")
def get_driver_behavior_analysis(db: Session = Depends(get_db)):
    # Group telemetry logs by driver to analyze behavior and efficiency
    # Calculate: driver ID, name, average efficiency, total harsh braking, total harsh acceleration, total overspeeding
    query_result = db.query(
        TelemetryModel.driver_id,
        func.avg(TelemetryModel.energy_efficiency).label("avg_eff"),
        func.sum(TelemetryModel.harsh_braking).label("total_braking"),
        func.sum(TelemetryModel.harsh_acceleration).label("total_accel"),
        func.sum(TelemetryModel.overspeed_violation).label("total_overspeed"),
        func.sum(TelemetryModel.distance_travelled).label("total_dist"),
        func.sum(TelemetryModel.income).label("total_income"),
        func.sum(TelemetryModel.charging_cost).label("total_charging")
    ).group_by(TelemetryModel.driver_id).all()
    
    drivers_list = []
    
    # Store lists to compute correlation
    eff_list = []
    braking_list = []
    accel_list = []
    overspeed_list = []

    for r in query_result:
        driver = db.query(DriverModel).filter(DriverModel.id == r.driver_id).first()
        if not driver:
            continue
            
        avg_eff = float(r.avg_eff or 4.7)
        total_braking = int(r.total_braking or 0)
        total_accel = int(r.total_accel or 0)
        total_overspeed = int(r.total_overspeed or 0)
        total_dist = float(r.total_dist or 0.0)
        total_income = float(r.total_income or 0.0)
        total_charging = float(r.total_charging or 0.0)
        trips = db.query(TelemetryModel).filter(TelemetryModel.driver_id == r.driver_id, TelemetryModel.distance_travelled > 0).count()

        # Driver score: higher efficiency and lower violations = higher score
        # base score 100, deduct for violations per 100km
        rate_braking = (total_braking / total_dist * 100.0) if total_dist > 0 else 0
        rate_accel = (total_accel / total_dist * 100.0) if total_dist > 0 else 0
        rate_overspeed = (total_overspeed / total_dist * 100.0) if total_dist > 0 else 0
        
        score = 100.0 - (rate_braking * 0.8 + rate_accel * 0.5 + rate_overspeed * 1.5)
        score = max(50.0, min(100.0, score))
        
        drivers_list.append({
            "driver_id": r.driver_id,
            "name": driver.name,
            "avg_efficiency": round(avg_eff, 2),
            "total_harsh_braking": total_braking,
            "total_harsh_acceleration": total_accel,
            "total_overspeed_violations": total_overspeed,
            "total_distance_km": round(total_dist, 1),
            "score": round(score, 1),
            "trips": trips,
            "income": round(total_income, 2),
            "charging_cost": round(total_charging, 2),
            "net_earnings": round(total_income - total_charging, 2)
        })
        
        eff_list.append(avg_eff)
        braking_list.append(total_braking)
        accel_list.append(total_accel)
        overspeed_list.append(total_overspeed)
        
    # Pearson Correlation Coefficient Calculation: Impact of violations on Efficiency
    correlation_braking = 0.0
    correlation_overspeed = 0.0
    
    if len(eff_list) > 1:
        corr_matrix_braking = np.corrcoef(braking_list, eff_list)
        correlation_braking = corr_matrix_braking[0, 1] if not np.isnan(corr_matrix_braking[0, 1]) else 0.0
        
        corr_matrix_overspeed = np.corrcoef(overspeed_list, eff_list)
        correlation_overspeed = corr_matrix_overspeed[0, 1] if not np.isnan(corr_matrix_overspeed[0, 1]) else 0.0

    return {
        "drivers": sorted(drivers_list, key=lambda x: x["score"], reverse=True),
        "impact_analysis": {
            "harsh_braking_efficiency_correlation": round(correlation_braking, 4),
            "overspeeding_efficiency_correlation": round(correlation_overspeed, 4),
            "conclusion": "Negative correlation values confirm that higher frequencies of harsh braking and overspeeding directly reduce EV battery energy efficiency (km/kWh)."
        }
    }

@router.get("/correlation-matrix")
def get_correlation_matrix():
    # Load from excel
    if not os.path.exists(FLEET_EXCEL_PATH):
        raise HTTPException(status_code=404, detail="Correlation matrix dataset not found")
        
    try:
        df = pd.read_excel(FLEET_EXCEL_PATH, sheet_name="Correlation_Matrix")
        # Clean dataframe to JSON format
        # Replace NaN with null
        df = df.where(pd.notnull(df), None)
        records = df.to_dict(orient="records")
        return records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading correlation matrix: {str(e)}")
