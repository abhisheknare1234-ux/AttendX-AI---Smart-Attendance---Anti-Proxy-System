"""Health and readiness endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.db import get_db
from app.schemas.accounts import HealthOut

router = APIRouter(prefix="/health", tags=["health"])
VERSION = "0.1.0"


@router.get("/live")
def live():
    return {"status": "ok", "version": VERSION}


@router.get("/ready", response_model=HealthOut)
def ready(db: Session = Depends(get_db), settings: Settings = Depends(get_settings)):
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unavailable"
    return HealthOut(
        status="ok" if database_status == "ok" else "degraded",
        database=database_status,
        face_provider=settings.face_provider,
        liveness_provider=settings.liveness_provider,
        environment=settings.app_env,
        version=VERSION,
    )
