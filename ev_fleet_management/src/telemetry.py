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
        idx = sim_indices.get(d.id, 0)
        if idx >= len(records):
            idx = 0
        record = records[idx]
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

    # 2. Get current simulation step index
    idx = sim_indices.get(driver_id, 0)
    if idx >= len(records):
        idx = 0
    
    record = records[idx]
    
    # 3. Update active indices
    sim_indices[driver_id] = idx + 1

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
        "longitude": record.longitude
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
    ).order_by(TelemetryModel.datetime.desc()).limit(5).all()
    
    history = []
    for r in records:
        history.append({
            "date": r.datetime.strftime("%b %d, %Y"),
            "time": r.datetime.strftime("%H:%M"),
            "station": "EV Hub Central",
            "kwh": round(r.battery_pct * 0.52, 1), # mock energy added
            "cost": f"₹{int(r.charging_cost)}",
            "dur": "45 min",
            "type": "Fast DC"
        })
    return history
