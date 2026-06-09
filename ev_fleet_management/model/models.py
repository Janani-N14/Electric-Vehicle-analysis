from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from ev_fleet_management.utils.db import Base

# ==========================================
# SQLAlchemy ORM Models
# ==========================================

class UserModel(Base):
    __tablename__ = "users"

    id = Column(String(50), primary_key=True, index=True)  # ID (e.g. ADM001, DRV001, D001)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(String(20), nullable=False)  # admin / driver
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    driver = relationship("DriverModel", back_populates="user", uselist=False)


class EVModel(Base):
    __tablename__ = "evs"

    id = Column(String(50), primary_key=True, index=True)  # E.g. EV-3017, EV-4021
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    plate_no = Column(String(50), nullable=False, unique=True)
    battery_capacity_kwh = Column(Float, nullable=False)
    year = Column(Integer, nullable=False)
    color = Column(String(50), nullable=True)
    vin = Column(String(50), nullable=True)
    odometer_km = Column(Float, default=0.0)
    battery_health_soh = Column(Float, default=100.0)
    next_service_km = Column(Float, default=5000.0)
    status = Column(String(20), default="Idle")  # Active, Idle, Charging, Offline

    drivers = relationship("DriverModel", back_populates="vehicle")


class DriverModel(Base):
    __tablename__ = "drivers"

    id = Column(String(50), primary_key=True, index=True)  # E.g. D001
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=True)
    vehicle_id = Column(String(50), ForeignKey("evs.id"), nullable=True)
    status = Column(String(20), default="Idle")  # Working, Idle, Charging, Garage

    user = relationship("UserModel", back_populates="driver")
    vehicle = relationship("EVModel", back_populates="drivers")


class AlertModel(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    type = Column(String(20), nullable=False)  # crit, warn, info
    icon = Column(String(10), nullable=True)  # 🪫, 🔧, 🔩, ⚠️, 🔋
    driver_id = Column(String(50), nullable=True)
    vehicle_id = Column(String(50), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    is_dismissed = Column(Boolean, default=False)


class TelemetryModel(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    driver_id = Column(String(50), index=True)
    vehicle_id = Column(String(50), index=True)
    datetime = Column(DateTime, index=True)
    speed = Column(Float)
    acceleration = Column(Float)
    harsh_braking = Column(Integer, default=0)
    harsh_acceleration = Column(Integer, default=0)
    overspeed_violation = Column(Integer, default=0)
    working_status = Column(String(20))
    passenger_count = Column(Integer)
    distance_travelled = Column(Float)
    odometer_distance = Column(Float)
    is_charging = Column(Integer, default=0)
    is_discharging = Column(Integer, default=0)
    charging_cost = Column(Float, default=0.0)
    energy_efficiency = Column(Float, default=0.0)
    income = Column(Float, default=0.0)
    maintenance_cost = Column(Float, default=0.0)
    maintenance_type = Column(String(50), default="Other")
    breakdown = Column(Integer, default=0)
    cost_per_km = Column(Float, default=0.0)
    battery_pct = Column(Float)
    battery_health = Column(Float)
    battery_stress = Column(Integer, default=0)
    estimated_range = Column(Float)
    latitude = Column(Float)
    longitude = Column(Float)


# ==========================================
# Pydantic Validation Schemas
# ==========================================

class UserRegister(BaseModel):
    id: str
    email: EmailStr
    password: str
    role: str  # admin / driver
    name: str
    vehicle_id: Optional[str] = None

class UserLogin(BaseModel):
    id: str
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    role: str
    is_verified: bool

    class Config:
        from_attributes = True


class EVCreate(BaseModel):
    id: str
    make: str
    model: str
    plate_no: str
    battery_capacity_kwh: float
    year: int
    color: Optional[str] = None
    vin: Optional[str] = None
    odometer_km: Optional[float] = 0.0
    battery_health_soh: Optional[float] = 100.0

class EVOut(BaseModel):
    id: str
    make: str
    model: str
    plate_no: str
    battery_capacity_kwh: float
    year: int
    color: Optional[str]
    vin: Optional[str]
    odometer_km: float
    battery_health_soh: float
    next_service_km: float
    status: str

    class Config:
        from_attributes = True


class DriverCreate(BaseModel):
    id: str
    name: str
    email: EmailStr
    vehicle_id: Optional[str] = None

class DriverOut(BaseModel):
    id: str
    name: str
    email: str
    vehicle_id: Optional[str]
    status: str

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    type: str
    icon: Optional[str]
    driver_id: Optional[str]
    vehicle_id: Optional[str]
    timestamp: datetime
    is_dismissed: bool

    class Config:
        from_attributes = True
