from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from ev_fleet_management.utils.db import get_db
from ev_fleet_management.model.models import AlertModel, AlertOut
from ev_fleet_management.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/alerts", tags=["alerts"])

@router.get("", response_model=List[AlertOut])
def get_active_alerts(db: Session = Depends(get_db)):
    return db.query(AlertModel).filter(AlertModel.is_dismissed == False).order_by(AlertModel.timestamp.desc()).all()

@router.post("/dismiss/{alert_id}")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)):
    alert = db.query(AlertModel).filter(AlertModel.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.is_dismissed = True
    db.commit()
    return {"message": f"Alert {alert_id} dismissed successfully"}

@router.post("/dismiss-all")
def dismiss_all_alerts(db: Session = Depends(get_db)):
    active_alerts = db.query(AlertModel).filter(AlertModel.is_dismissed == False).all()
    for alert in active_alerts:
        alert.is_dismissed = True
    db.commit()
    return {"message": "All active alerts dismissed successfully"}
