import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/ev_fleet.db")

# Excel Files
ADMIN_EXCEL_PATH = DATA_DIR / "EV_Admin.xlsx"
FLEET_EXCEL_PATH = DATA_DIR / "EV_Fleet_Drivers.xlsx"

# Security
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super_secret_ev_fleet_key_12345")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 1 day

# Server
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "True").lower() == "true"
