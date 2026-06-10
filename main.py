import uvicorn
from fastapi import FastAPI, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import os

from ev_fleet_management.config.settings import HOST, PORT, DEBUG
from ev_fleet_management.utils.db import get_db, engine
from ev_fleet_management.src.data_ingestion import seed_database
from ev_fleet_management.logger import get_logger

# Import routers
from ev_fleet_management.src.auth import router as auth_router
from ev_fleet_management.src.telemetry import router as telemetry_router
from ev_fleet_management.src.analytics import router as analytics_router
from ev_fleet_management.src.alerts import router as alerts_router
from ev_fleet_management.src.vehicles import router as vehicles_router
from ev_fleet_management.src.drivers import router as drivers_router

logger = get_logger(__name__)

app = FastAPI(
    title="EV Fleet Management & Predictive Analytics Platform",
    description="Smart EV Data Monitoring & Performance Analysis Platform",
    version="1.0.0"
)

# Ingest and Seed DB on startup
@app.on_event("startup")
def startup_event():
    logger.info("Application starting up...")
    db = next(get_db())
    try:
        seed_database(db)
    except Exception as e:
        logger.error(f"Error seeding database: {str(e)}")
    finally:
        db.close()

# Include Routers
app.include_router(auth_router)
app.include_router(telemetry_router)
app.include_router(analytics_router)
app.include_router(alerts_router)
app.include_router(vehicles_router)
app.include_router(drivers_router)

# Mount static folder (create if not exists)
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=templates_dir)

# HTML Views
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/index.html", response_class=HTMLResponse)
def index_redirect(request: Request):
    return RedirectResponse(url="/")

@app.get("/admin-dashboard.html", response_class=HTMLResponse)
def admin_dashboard_page(request: Request):
    # Verify cookie to check session before rendering dashboard
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/#portal-card")
    return templates.TemplateResponse(request=request, name="admin-dashboard.html")

@app.get("/driver-dashboard.html", response_class=HTMLResponse)
def driver_dashboard_page(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return RedirectResponse(url="/#portal-card")
    return templates.TemplateResponse(request=request, name="driver-dashboard.html")

if __name__ == "__main__":
    logger.info(f"Starting server at http://{HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=DEBUG)
