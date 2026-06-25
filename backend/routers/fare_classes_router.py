# =============================================================
# AeroDesk — Fare Classes Router
# backend/routers/fare_classes_router.py
# =============================================================
# Read-only for most roles — data seeded at setup
# Access: All authenticated staff
# =============================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import FareClass, Staff, StaffRoleEnum
from backend.auth.auth import get_current_user
from backend.schemas.fare_class_schemas import FareClassResponse, FareClassListResponse

router = APIRouter()


@router.get("/", response_model=FareClassListResponse)
def list_fare_classes(
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(get_current_user)
):
    """Returns all fare classes. Used to populate dropdowns in booking screens."""
    fare_classes = db.query(FareClass).order_by(FareClass.multiplier).all()
    return FareClassListResponse(total=len(fare_classes), fare_classes=fare_classes)


@router.get("/{fare_class_id}", response_model=FareClassResponse)
def get_fare_class(
    fare_class_id:  int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(get_current_user)
):
    from fastapi import HTTPException
    fc = db.query(FareClass).filter(FareClass.fare_class_id == fare_class_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail=f"Fare class {fare_class_id} not found.")
    return fc
