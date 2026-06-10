from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from ev_fleet_management.utils.db import get_db
from ev_fleet_management.model.models import EVModel, EVCreate, EVOut, TelemetryModel
from ev_fleet_management.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/vehicles", tags=["vehicles"])

@router.get("", response_model=List[EVOut])
def get_all_vehicles(db: Session = Depends(get_db)):
    vehicles = db.query(EVModel).all()
    for v in vehicles:
        maint_cost = db.query(func.sum(TelemetryModel.maintenance_cost)).filter(TelemetryModel.vehicle_id == v.id).scalar() or 0.0
        v.maintenance_cost = float(maint_cost)
    return vehicles

@router.post("", response_model=EVOut, status_code=status.HTTP_201_CREATED)
def register_vehicle(ev_data: EVCreate, db: Session = Depends(get_db)):
    existing = db.query(EVModel).filter(EVModel.id == ev_data.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Vehicle ID already registered")
        
    existing_plate = db.query(EVModel).filter(EVModel.plate_no == ev_data.plate_no).first()
    if existing_plate:
        raise HTTPException(status_code=400, detail="Plate number already registered")

    new_ev = EVModel(
        id=ev_data.id,
        make=ev_data.make,
        model=ev_data.model,
        plate_no=ev_data.plate_no,
        battery_capacity_kwh=ev_data.battery_capacity_kwh,
        year=ev_data.year,
        color=ev_data.color or "Pearl White",
        vin=ev_data.vin,
        odometer_km=ev_data.odometer_km or 0.0,
        battery_health_soh=ev_data.battery_health_soh or 100.0,
        next_service_km=(ev_data.odometer_km or 0.0) + 5000.0,
        status="Idle"
    )
    db.add(new_ev)
    db.commit()
    db.refresh(new_ev)
    logger.info(f"Registered new EV: {new_ev.id} - {new_ev.make} {new_ev.model}")
    return new_ev

@router.get("/{vehicle_id}", response_model=EVOut)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    ev = db.query(EVModel).filter(EVModel.id == vehicle_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    maint_cost = db.query(func.sum(TelemetryModel.maintenance_cost)).filter(TelemetryModel.vehicle_id == vehicle_id).scalar() or 0.0
    ev.maintenance_cost = float(maint_cost)
    return ev

@router.delete("/{vehicle_id}")
def delete_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    ev = db.query(EVModel).filter(EVModel.id == vehicle_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    # Unlink drivers
    drivers = db.query(DriverModel).filter(DriverModel.vehicle_id == vehicle_id).all()
    for d in drivers:
        d.vehicle_id = None
        
    db.delete(ev)
    db.commit()
    logger.info(f"Deleted EV: {vehicle_id}")
    return {"message": f"Vehicle {vehicle_id} deleted successfully"}
