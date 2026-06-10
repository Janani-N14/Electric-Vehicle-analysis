from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from ev_fleet_management.utils.db import get_db
from ev_fleet_management.utils.jwt_helper import get_current_user_from_cookie, get_optional_current_user
from ev_fleet_management.model.models import DriverModel, DriverCreate, DriverOut, UserModel, EVModel
from ev_fleet_management.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/drivers", tags=["drivers"])

@router.get("", response_model=List[DriverOut])
def get_all_drivers(
    current_user: dict = Depends(get_optional_current_user),
    db: Session = Depends(get_db)
):
    if current_user and current_user.get("role") == "admin":
        return db.query(DriverModel).filter(DriverModel.admin_id == current_user["sub"]).all()
    return db.query(DriverModel).all()

@router.post("", response_model=DriverOut, status_code=status.HTTP_201_CREATED)
def register_driver(driver_data: DriverCreate, db: Session = Depends(get_db)):
    existing = db.query(DriverModel).filter(DriverModel.id == driver_data.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Driver ID already registered")

    # Check if vehicle exists if provided
    if driver_data.vehicle_id:
        ev = db.query(EVModel).filter(EVModel.id == driver_data.vehicle_id).first()
        if not ev:
            raise HTTPException(status_code=404, detail="Assigned vehicle not found")

    new_driver = DriverModel(
        id=driver_data.id,
        name=driver_data.name,
        email=driver_data.email,
        vehicle_id=driver_data.vehicle_id,
        status="Idle"
    )
    db.add(new_driver)
    db.commit()
    db.refresh(new_driver)
    logger.info(f"Registered new driver: {new_driver.id} - {new_driver.name}")
    return new_driver

@router.get("/me")
def get_my_driver_profile(current_user: dict = Depends(get_current_user_from_cookie), db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(DriverModel.id == current_user["sub"]).first()
    if not driver:
        # Check if the user is an admin
        user = db.query(UserModel).filter(UserModel.id == current_user["sub"]).first()
        if user and user.role == "admin":
            return {"id": user.id, "name": "System Administrator", "email": user.email, "role": "admin"}
        raise HTTPException(status_code=404, detail="Driver profile not found")
        
    ev = None
    if driver.vehicle_id:
        ev = db.query(EVModel).filter(EVModel.id == driver.vehicle_id).first()
        
    return {
        "id": driver.id,
        "name": driver.name,
        "email": driver.email,
        "role": "driver",
        "status": driver.status,
        "vehicle": {
            "id": ev.id if ev else None,
            "make": ev.make if ev else None,
            "model": ev.model if ev else None,
            "plate_no": ev.plate_no if ev else None,
            "odometer_km": ev.odometer_km if ev else 0.0,
            "battery_capacity_kwh": ev.battery_capacity_kwh if ev else 0.0,
            "battery_health_soh": ev.battery_health_soh if ev else 100.0,
            "next_service_km": ev.next_service_km if ev else 5000.0,
            "status": ev.status if ev else "Idle"
        } if ev else None
    }

@router.delete("/{driver_id}")
def delete_driver(driver_id: str, db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(DriverModel.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
        
    # Unassign vehicle
    if driver.vehicle_id:
        ev = db.query(EVModel).filter(EVModel.id == driver.vehicle_id).first()
        if ev:
            ev.status = "Idle"
            
    # Delete associated user if exists
    user = db.query(UserModel).filter(UserModel.id == driver_id).first()
    if user:
        db.delete(user)
        
    db.delete(driver)
    db.commit()
    logger.info(f"Deleted driver: {driver_id}")
    return {"message": f"Driver {driver_id} deleted successfully"}

@router.put("/{driver_id}")
def update_driver(driver_id: str, data: dict, db: Session = Depends(get_db)):
    driver = db.query(DriverModel).filter(DriverModel.id == driver_id).first()
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
        
    if "status" in data:
        driver.status = data["status"]
    if "vehicle_id" in data:
        vehicle_id = data["vehicle_id"]
        if vehicle_id == "None" or not vehicle_id:
            # Unlink previous vehicle status if any
            if driver.vehicle_id:
                prev_ev = db.query(EVModel).filter(EVModel.id == driver.vehicle_id).first()
                if prev_ev:
                    prev_ev.status = "Idle"
            driver.vehicle_id = None
        else:
            # Check if vehicle exists
            ev = db.query(EVModel).filter(EVModel.id == vehicle_id).first()
            if not ev:
                raise HTTPException(status_code=404, detail="Vehicle not found")
            # Unassign previous driver's vehicle assignment if any
            if driver.vehicle_id and driver.vehicle_id != vehicle_id:
                prev_ev = db.query(EVModel).filter(EVModel.id == driver.vehicle_id).first()
                if prev_ev:
                    prev_ev.status = "Idle"
            driver.vehicle_id = vehicle_id
            ev.status = "Active"
            
    db.commit()
    logger.info(f"Updated driver {driver_id}")
    return {"message": "Driver updated successfully"}
