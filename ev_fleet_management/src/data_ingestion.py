import os
import pandas as pd
from datetime import datetime
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from ev_fleet_management.config.settings import ADMIN_EXCEL_PATH, FLEET_EXCEL_PATH
from ev_fleet_management.logger import get_logger
from ev_fleet_management.utils.db import Base, engine
from ev_fleet_management.model.models import UserModel, EVModel, DriverModel, TelemetryModel, AlertModel

logger = get_logger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def seed_database(db: Session):
    # 1. Create tables
    logger.info("Creating database tables if not exist...")
    Base.metadata.create_all(bind=engine)

    # Check if database is already seeded
    if db.query(UserModel).count() > 0:
        logger.info("Database already seeded. Skipping ingestion.")
        return

    logger.info("Starting database seeding from Excel files...")

    # Load Excel Files
    if not os.path.exists(ADMIN_EXCEL_PATH) or not os.path.exists(FLEET_EXCEL_PATH):
        logger.error(f"Excel files not found. Ingestion failed.\nPaths:\n{ADMIN_EXCEL_PATH}\n{FLEET_EXCEL_PATH}")
        return

    admin_df = pd.read_excel(ADMIN_EXCEL_PATH)
    fleet_df = pd.read_excel(FLEET_EXCEL_PATH, sheet_name="Driver_Fleet_Data")

    logger.info("Excel files loaded successfully.")

    # 2. Seed Admin and Driver Accounts & EVs
    # We will hash passwords for A001-A004 and D001-D010
    default_pw_hash = hash_password("Pass1234")

    # Add Admins
    admins_seen = set()
    for _, row in admin_df.iterrows():
        admin_id = str(row["Admin Id"]).strip()
        admin_name = str(row["Admin Name"]).strip()
        if admin_id not in admins_seen:
            admins_seen.add(admin_id)
            user = UserModel(
                id=admin_id,
                email=f"{admin_id.lower()}@evfleet.com",
                password_hash=default_pw_hash,
                role="admin",
                is_verified=True
            )
            db.add(user)
            logger.info(f"Added Admin User: {admin_id}")

    # Add EVs and Drivers
    drivers_seen = set()
    for _, row in admin_df.iterrows():
        driver_id = str(row["Driver Id"]).strip()
        driver_name = str(row["Driver Name"]).strip()
        
        # In the excel, Vehicle Id might be 0, so we synthesize a unique code like EV-D001, etc.
        vehicle_excel_id = row["Vehicle Id"]
        vehicle_id = f"EV-{driver_id}"
        
        brand = str(row["Brand"]).strip()
        motor_spec = str(row["Motor Spec"]).strip()
        capacity = float(row["Battery Capacity Kwh"])
        odometer = float(row["Max Odometer Km"])
        health = float(row["Avg Battery Health Pct"])
        
        # Add EV
        ev = EVModel(
            id=vehicle_id,
            make=brand,
            model=f"{brand} Fleet Spec",
            plate_no=f"EV-{driver_id}-TN",
            battery_capacity_kwh=capacity,
            year=2024,
            color="Pearl White",
            vin=f"5YJ3E1EA4NF0000{driver_id[1:]}",
            odometer_km=odometer,
            battery_health_soh=health,
            next_service_km=odometer + 1818,
            status="Idle"
        )
        db.add(ev)
        
        # Add Driver User Account
        user = UserModel(
            id=driver_id,
            email=f"{driver_id.lower()}@evfleet.com",
            password_hash=default_pw_hash,
            role="driver",
            is_verified=True
        )
        db.add(user)
        
        # Add Driver details
        driver = DriverModel(
            id=driver_id,
            name=driver_name,
            email=f"{driver_id.lower()}@evfleet.com",
            user_id=driver_id,
            vehicle_id=vehicle_id,
            status="Idle"
        )
        db.add(driver)
        logger.info(f"Added Driver: {driver_id} linked to EV: {vehicle_id}")

    db.commit()

    # 3. Seed Telemetry (Bulk insert)
    logger.info("Ingesting timeseries telemetry data (15,000 records)...")
    
    telemetry_list = []
    # Base location in Chennai (driver pos)
    base_lat, base_lng = 13.0810, 80.2680
    
    # Sort fleet data by Datetime
    fleet_df = fleet_df.sort_values(by="Datetime")

    # Group telemetry by driver to synthesize routes (adding small changes to lat/lng for smooth pathing)
    driver_positions = {}
    
    for idx, row in fleet_df.iterrows():
        driver_id = str(row["Driver Id"]).strip()
        vehicle_id = f"EV-{driver_id}"
        dt_val = row["Datetime"]
        if isinstance(dt_val, str):
            dt_val = datetime.strptime(dt_val, "%Y-%m-%d %H:%M:%S")
            
        # Synthesize latitude and longitude centered around Chennai
        if driver_id not in driver_positions:
            # Random starting position near base
            import random
            random.seed(hash(driver_id))
            driver_positions[driver_id] = (
                base_lat + (random.random() - 0.5) * 0.02,
                base_lng + (random.random() - 0.5) * 0.02
            )
        
        # Get current coords and slightly perturb based on speed & direction
        lat, lng = driver_positions[driver_id]
        speed = float(row["Speed"])
        if speed > 0:
            import math
            angle = (idx % 360) * (math.pi / 180.0)
            # Move coordinates
            lat += (speed / 100000.0) * math.cos(angle)
            lng += (speed / 100000.0) * math.sin(angle)
            driver_positions[driver_id] = (lat, lng)

        telemetry_list.append({
            "driver_id": driver_id,
            "vehicle_id": vehicle_id,
            "datetime": dt_val,
            "speed": float(row["Speed"]),
            "acceleration": float(row["Acceleration"]),
            "harsh_braking": int(row["Harsh Braking"]),
            "harsh_acceleration": int(row["Harsh Acceleration"]),
            "overspeed_violation": int(row["Overspeed Violation"]),
            "working_status": str(row["Working Status"]).strip(),
            "passenger_count": int(row["Passenger Count"]),
            "distance_travelled": float(row["Distance Travelled"]),
            "odometer_distance": float(row["Odometer Distance Travelled"]),
            "is_charging": int(row["Is Charging"]),
            "is_discharging": int(row["Is Discharging"]),
            "charging_cost": float(row["Charging Cost"]),
            "energy_efficiency": float(row["Energy Efficiency Km Per Kwh"]),
            "income": float(row["Income"]),
            "maintenance_cost": float(row["Maintenance Cost"]),
            "maintenance_type": str(row["Maintenance Type"]).strip(),
            "breakdown": int(row["Breakdown"]),
            "cost_per_km": float(row.get("Cost Per Km", 0.0) if not pd.isna(row.get("Cost Per Km")) else 0.0),
            "battery_pct": float(row["Battery Percentage"]),
            "battery_health": float(row["Battery Health"]),
            "battery_stress": int(row["Battery Stress"]),
            "estimated_range": float(row["Estimated Range Km"]),
            "latitude": lat,
            "longitude": lng
        })

    # Bulk insert
    logger.info("Executing bulk insert for Telemetry...")
    db.bulk_insert_mappings(TelemetryModel, telemetry_list)
    db.commit()
    logger.info(f"Ingested {len(telemetry_list)} telemetry records successfully!")

    # Set some initial alerts based on health, charging, or breakdown metrics
    logger.info("Generating initial alerts...")
    
    # 1. Critical battery stress / health alert
    alert1 = AlertModel(
        title="Critical Battery Stress — EV-D001",
        description="Hyundai Fleet Spec · 84% Health · D001 (Aakash) · High battery stress detected.",
        type="crit",
        icon="🪫",
        driver_id="D001",
        vehicle_id="EV-D001",
        timestamp=datetime.utcnow()
    )
    db.add(alert1)

    # 2. Overspeed violation alert
    alert2 = AlertModel(
        title="Overspeed Violation — EV-D005",
        description="Tata Fleet Spec · D005 (Pranav) overspeeding in city limit.",
        type="warn",
        icon="⚠️",
        driver_id="D005",
        vehicle_id="EV-D005",
        timestamp=datetime.utcnow()
    )
    db.add(alert2)

    # 3. Maintenance due alert
    alert3 = AlertModel(
        title="Service Due — EV-D003",
        description="Volkswagen Fleet Spec · D003 (Sanjay) · Next service due in 120 km.",
        type="info",
        icon="🔧",
        driver_id="D003",
        vehicle_id="EV-D003",
        timestamp=datetime.utcnow()
    )
    db.add(alert3)
    db.commit()
    logger.info("Initial alerts seeded successfully.")
