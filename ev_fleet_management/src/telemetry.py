from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict
from datetime import datetime
from ev_fleet_management.utils.db import get_db
from ev_fleet_management.model.models import TelemetryModel, EVModel, DriverModel
from ev_fleet_management.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])

# In-memory index to track real-time simulation step for each driver
sim_indices: Dict[str, int] = {}

# Charging stations list (Chennai coordinates matching dashboard Leaflet maps)
EV_STATIONS = [
    {"id": "ST001", "lat": 13.0827, "lng": 80.2707, "name": "EV Hub Central", "ports": 12, "kw": 150, "free": 4, "cost": "₹15/kWh", "type": "Fast DC"},
    {"id": "ST002", "lat": 13.0750, "lng": 80.2600, "name": "Green Point Station", "ports": 6, "kw": 22, "free": 1, "cost": "₹10/kWh", "type": "AC"},
    {"id": "ST003", "lat": 13.0900, "lng": 80.2780, "name": "Tesla Supercharger", "ports": 16, "kw": 250, "free": 8, "cost": "₹18/kWh", "type": "Tesla SC"},
    {"id": "ST004", "lat": 13.0680, "lng": 80.2820, "name": "City Mall Charger", "ports": 8, "kw": 11, "free": 3, "cost": "₹8/kWh", "type": "AC"},
    {"id": "ST005", "lat": 13.0950, "lng": 80.2550, "name": "Depot Fast Charger", "ports": 4, "kw": 120, "free": 0, "cost": "₹13/kWh", "type": "Fast DC"},
    {"id": "ST006", "lat": 13.0600, "lng": 80.2650, "name": "Highway Station", "ports": 10, "kw": 22, "free": 6, "cost": "₹10/kWh", "type": "AC"},
]

@router.get("/latest")
def get_all_latest_telemetry(db: Session = Depends(get_db)):
    drivers = db.query(DriverModel).all()
    latest = {}
    for d in drivers:
        records = db.query(TelemetryModel).filter(TelemetryModel.driver_id == d.id).order_by(TelemetryModel.datetime).all()
        if not records:
            continue
        # Use the most recent record (static snapshot)
        record = records[-1]
        latest[d.id] = {
            "driver_id": d.id,
            "driver_name": d.name,
            "vehicle_id": d.vehicle_id,
            "battery_pct": record.battery_pct,
            "speed": record.speed,
            "latitude": record.latitude,
            "longitude": record.longitude,
            "status": "charging" if record.working_status == "Charging" else ("active" if record.working_status == "Working" else ("idle" if record.working_status == "Idle" else "offline")),
            "breakdown": record.breakdown,
            "overspeed": record.overspeed_violation,
            "efficiency": record.energy_efficiency,
            "range": record.estimated_range,
            "odometer": record.odometer_distance
        }
    return latest

@router.get("/stations")
def get_stations():
    return EV_STATIONS

@router.get("/live/{driver_id}")
def get_live_telemetry(driver_id: str, db: Session = Depends(get_db)):
    # 1. Fetch all telemetry records for this driver
    records = db.query(TelemetryModel).filter(TelemetryModel.driver_id == driver_id).order_by(TelemetryModel.datetime).all()
    if not records:
        raise HTTPException(status_code=404, detail=f"No telemetry records found for driver {driver_id}")

    # 2. Return the most recent record (static snapshot, not cycling)
    record = records[-1]

    # 4. Sync current vehicle status in db based on live telemetry status
    # This keeps EVModel status (Idle/Active/Charging) in sync with simulated real-time data
    driver = db.query(DriverModel).filter(DriverModel.id == driver_id).first()
    if driver and driver.vehicle_id:
        ev = db.query(EVModel).filter(EVModel.id == driver.vehicle_id).first()
        if ev:
            # map working status to EV status
            status_map = {
                "Working": "Active",
                "Idle": "Idle",
                "Charging": "Charging",
                "Garage": "Offline"
            }
            ev.status = status_map.get(record.working_status, "Idle")
            ev.odometer_km = record.odometer_distance
            db.commit()

    return {
        "id": record.id,
        "driver_id": record.driver_id,
        "vehicle_id": record.vehicle_id,
        "datetime": record.datetime.isoformat(),
        "speed": record.speed,
        "acceleration": record.acceleration,
        "harsh_braking": record.harsh_braking,
        "harsh_acceleration": record.harsh_acceleration,
        "overspeed_violation": record.overspeed_violation,
        "working_status": record.working_status,
        "passenger_count": record.passenger_count,
        "distance_travelled": record.distance_travelled,
        "odometer_distance": record.odometer_distance,
        "is_charging": record.is_charging,
        "is_discharging": record.is_discharging,
        "charging_cost": record.charging_cost,
        "energy_efficiency": record.energy_efficiency,
        "income": record.income,
        "maintenance_cost": record.maintenance_cost,
        "maintenance_type": record.maintenance_type,
        "breakdown": record.breakdown,
        "battery_pct": record.battery_pct,
        "battery_health": record.battery_health,
        "battery_stress": record.battery_stress,
        "estimated_range": record.estimated_range,
        "latitude": record.latitude,
        "longitude": record.longitude,
        "city_highway": record.city_highway
    }

@router.get("/history/{driver_id}")
def get_driver_history(driver_id: str, db: Session = Depends(get_db)):
    # Return recent telemetry logs that had non-zero distance (representing trips)
    records = db.query(TelemetryModel).filter(
        TelemetryModel.driver_id == driver_id,
        TelemetryModel.distance_travelled > 0
    ).order_by(TelemetryModel.datetime.desc()).limit(10).all()
    
    trips = []
    for idx, r in enumerate(records):
        trips.append({
            "n": idx + 1,
            "date": r.datetime.strftime("%b %d, %Y"),
            "time": r.datetime.strftime("%H:%M"),
            "route": f"Trip Segment {idx+1}",
            "dist": f"{r.distance_travelled:.1f} km",
            "speed": f"{r.speed:.0f} km/h",
            "energy": f"{(r.distance_travelled / max(0.1, r.energy_efficiency)):.1f} kWh",
            "fare": f"₹{int(r.income)}",
            "cost": f"₹{int(r.charging_cost)}",
            "overspeed": "Overspeed" if r.overspeed_violation > 0 else "None",
            "status": "Completed"
        })
    return trips

@router.get("/charging")
def get_all_charging_history(db: Session = Depends(get_db)):
    records = db.query(TelemetryModel).filter(
        TelemetryModel.is_charging == 1
    ).order_by(TelemetryModel.datetime.desc()).limit(15).all()
    
    history = []
    for r in records:
        driver = db.query(DriverModel).filter(DriverModel.id == r.driver_id).first()
        driver_name = driver.name if driver else r.driver_id
        history.append({
            "time": r.datetime.strftime("%H:%M"),
            "date": r.datetime.strftime("%b %d, %Y"),
            "vid": r.vehicle_id,
            "driver": driver_name,
            "station": "EV Hub Central",
            "kwh": round(r.battery_pct * 0.52, 1),
            "cost": f"₹{int(r.charging_cost)}",
            "dur": "45 min",
            "status": "active" if r.working_status == "Charging" else "completed"
        })
    return history

@router.get("/charging/{driver_id}")
def get_driver_charging_history(driver_id: str, db: Session = Depends(get_db)):
    # Fetch charging logs
    records = db.query(TelemetryModel).filter(
        TelemetryModel.driver_id == driver_id,
        TelemetryModel.is_charging == 1
    ).order_by(TelemetryModel.datetime.desc()).limit(100).all()
    
    history = []
    for r in records:
        station = "EV Hub Central"
        c_type = "Fast DC"
        if r.charging_cost < 50:
            station = "Green Point Station"
            c_type = "AC"
        elif r.charging_cost > 150:
            station = "Tesla Supercharger"
            c_type = "Tesla SC"
        history.append({
            "date": r.datetime.strftime("%b %d, %Y"),
            "time": r.datetime.strftime("%H:%M"),
            "station": station,
            "kwh": round(r.battery_pct * 0.52, 1),
            "cost": f"₹{int(r.charging_cost)}",
            "dur": "45 min",
            "type": c_type
        })
    return history

from typing import Optional

@router.get("/driver-stats/{driver_id}")
def get_driver_statistics(
    driver_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    route_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(TelemetryModel).filter(TelemetryModel.driver_id == driver_id)
    
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(TelemetryModel.datetime >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(TelemetryModel.datetime <= ed)
        except ValueError:
            pass
            
    if route_type and route_type != "All":
        flag = 1 if route_type == "Highway" else 0
        query = query.filter(TelemetryModel.city_highway == flag)
        
    records = query.all()
    
    if not records:
        return {
            "total_distance": 0.0,
            "avg_speed": 0.0,
            "total_energy": 0.0,
            "avg_efficiency": 0.0,
            "safety_score": 100.0,
            "overspeed_violations": 0,
            "harsh_braking": 0,
            "harsh_acceleration": 0,
            "total_income": 0.0,
            "charging_cost": 0.0,
            "net_earnings": 0.0,
            "charging_sessions": 0,
            "energy_charged": 0.0,
            "charts": {
                "dates": [],
                "distance": [],
                "efficiency": [],
                "safety": [],
                "income": []
            }
        }
        
    total_distance = sum(r.distance_travelled for r in records if r.distance_travelled)
    speeds = [r.speed for r in records if r.speed is not None]
    avg_speed = sum(speeds) / len(speeds) if speeds else 0.0
    
    total_energy = sum((r.distance_travelled / r.energy_efficiency) for r in records if r.distance_travelled and r.energy_efficiency and r.energy_efficiency > 0)
    avg_efficiency = total_distance / total_energy if total_energy > 0 else 4.7
    
    harsh_braking = sum(r.harsh_braking for r in records if r.harsh_braking)
    harsh_acceleration = sum(r.harsh_acceleration for r in records if r.harsh_acceleration)
    overspeed_violations = sum(r.overspeed_violation for r in records if r.overspeed_violation)
    
    safety_score = max(0, min(100, 100 - harsh_braking * 5 - harsh_acceleration * 5 - overspeed_violations * 10))
    
    total_income = sum(r.income for r in records if r.income)
    charging_cost = sum(r.charging_cost for r in records if r.charging_cost)
    net_earnings = total_income - charging_cost
    
    charging_sessions = sum(1 for r in records if r.is_charging == 1)
    energy_charged = sum(round(r.battery_pct * 0.52, 1) for r in records if r.is_charging == 1)
    
    daily_data = {}
    for r in records:
        d_str = r.datetime.strftime("%Y-%m-%d")
        if d_str not in daily_data:
            daily_data[d_str] = {
                "distance": 0.0,
                "energy": 0.0,
                "income": 0.0,
                "brakes": 0,
                "accels": 0,
                "overspeeds": 0,
                "health_sum": 0.0,
                "health_count": 0,
                "range_sum": 0.0,
                "range_count": 0
            }
        daily_data[d_str]["distance"] += r.distance_travelled or 0.0
        if r.distance_travelled and r.energy_efficiency and r.energy_efficiency > 0:
            daily_data[d_str]["energy"] += r.distance_travelled / r.energy_efficiency
        daily_data[d_str]["income"] += r.income or 0.0
        daily_data[d_str]["brakes"] += r.harsh_braking or 0
        daily_data[d_str]["accels"] += r.harsh_acceleration or 0
        daily_data[d_str]["overspeeds"] += r.overspeed_violation or 0
        if r.battery_health is not None:
            daily_data[d_str]["health_sum"] += r.battery_health
            daily_data[d_str]["health_count"] += 1
        if r.estimated_range is not None:
            daily_data[d_str]["range_sum"] += r.estimated_range
            daily_data[d_str]["range_count"] += 1
        
    sorted_dates = sorted(daily_data.keys())
    chart_dates = []
    chart_dist = []
    chart_eff = []
    chart_safety = []
    chart_income = []
    chart_health = []
    chart_range = []
    
    for d in sorted_dates:
        dt = datetime.strptime(d, "%Y-%m-%d")
        chart_dates.append(dt.strftime("%b %d"))
        day_dist = daily_data[d]["distance"]
        day_energy = daily_data[d]["energy"]
        day_eff = day_dist / day_energy if day_energy > 0 else 4.7
        day_safety = max(0, min(100, 100 - daily_data[d]["brakes"] * 5 - daily_data[d]["accels"] * 5 - daily_data[d]["overspeeds"] * 10))
        day_health = daily_data[d]["health_sum"] / daily_data[d]["health_count"] if daily_data[d]["health_count"] > 0 else 94.0
        
        range_cnt = daily_data[d]["range_count"]
        day_range = daily_data[d]["range_sum"] / range_cnt if range_cnt > 0 else 312.0
        
        chart_dist.append(round(day_dist, 1))
        chart_eff.append(round(day_eff, 2))
        chart_safety.append(day_safety)
        chart_income.append(round(daily_data[d]["income"], 2))
        chart_health.append(round(day_health, 1))
        chart_range.append(round(day_range, 1))
        
    return {
        "total_distance": round(total_distance, 1),
        "avg_speed": round(avg_speed, 1),
        "total_energy": round(total_energy, 1),
        "avg_efficiency": round(avg_efficiency, 2),
        "safety_score": round(safety_score, 1),
        "overspeed_violations": overspeed_violations,
        "harsh_braking": harsh_braking,
        "harsh_acceleration": harsh_acceleration,
        "total_income": round(total_income, 2),
        "charging_cost": round(charging_cost, 2),
        "net_earnings": round(net_earnings, 2),
        "charging_sessions": charging_sessions,
        "energy_charged": round(energy_charged, 1),
        "charts": {
            "dates": chart_dates,
            "distance": chart_dist,
            "efficiency": chart_eff,
            "safety": chart_safety,
            "income": chart_income,
            "health": chart_health,
            "range": chart_range
        }
    }


@router.get("/driver-trips/{driver_id}")
def get_driver_trips(
    driver_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    route_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(TelemetryModel).filter(
        TelemetryModel.driver_id == driver_id,
        TelemetryModel.distance_travelled > 0
    )
    
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(TelemetryModel.datetime >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(TelemetryModel.datetime <= ed)
        except ValueError:
            pass
            
    if route_type and route_type != "All":
        flag = 1 if route_type == "Highway" else 0
        query = query.filter(TelemetryModel.city_highway == flag)
        
    records = query.order_by(TelemetryModel.datetime.desc()).all()
    
    trips = []
    for idx, r in enumerate(records):
        trips.append({
            "n": idx + 1,
            "date": r.datetime.strftime("%b %d, %Y"),
            "time": r.datetime.strftime("%H:%M"),
            "route": "Segment to " + ("Highway" if r.city_highway == 1 else "City Depot"),
            "dist": f"{r.distance_travelled:.1f} km",
            "speed": f"{r.speed:.0f} km/h",
            "energy": f"{(r.distance_travelled / max(0.1, r.energy_efficiency)):.1f} kWh",
            "fare": f"₹{int(r.income)}",
            "cost": f"₹{int(r.charging_cost)}",
            "overspeed": "Overspeed" if r.overspeed_violation > 0 else "None",
            "status": "Completed"
        })
    return trips

@router.get("/driver-charging/{driver_id}")
def get_driver_charging(
    driver_id: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    charger_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    query = db.query(TelemetryModel).filter(
        TelemetryModel.driver_id == driver_id,
        TelemetryModel.is_charging == 1
    )
    
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(TelemetryModel.datetime >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date + " 23:59:59", "%Y-%m-%d %H:%M:%S")
            query = query.filter(TelemetryModel.datetime <= ed)
        except ValueError:
            pass
            
    records = query.order_by(TelemetryModel.datetime.desc()).all()
    
    history = []
    for r in records:
        station = "EV Hub Central"
        c_type = "Fast DC"
        if r.charging_cost < 50:
            station = "Green Point Station"
            c_type = "AC"
        elif r.charging_cost > 150:
            station = "Tesla Supercharger"
            c_type = "Tesla SC"
            
        if charger_type and charger_type != "All":
            if charger_type == "AC" and c_type != "AC":
                continue
            if charger_type == "Fast DC" and c_type != "Fast DC":
                continue
            if charger_type == "Tesla SC" and c_type != "Tesla SC":
                continue
            if charger_type == "Home" and c_type != "Home":
                continue
                
        history.append({
            "date": r.datetime.strftime("%b %d, %Y"),
            "time": r.datetime.strftime("%H:%M"),
            "station": station,
            "kwh": round(r.battery_pct * 0.52, 1),
            "cost": f"₹{int(r.charging_cost)}",
            "dur": "45 min",
            "type": c_type
        })
    return history
