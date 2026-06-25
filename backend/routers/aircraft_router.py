# =============================================================
# AeroDesk — Aircraft Router
# backend/routers/aircraft_router.py
# =============================================================
# Access: Super_Admin, Operations_Manager
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.models import Aircraft, Staff, StaffRoleEnum, AircraftStatusEnum
from backend.auth.auth import require_roles
from backend.schemas.aircraft_schemas import (
    AircraftCreate, AircraftUpdate,
    AircraftResponse, AircraftListResponse
)

router = APIRouter()
ALLOWED_ROLES = (StaffRoleEnum.Super_Admin, StaffRoleEnum.Operations_Manager)


@router.post("/", response_model=AircraftResponse, status_code=status.HTTP_201_CREATED)
def register_aircraft(
    payload:        AircraftCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    existing = db.query(Aircraft).filter(
        Aircraft.registration_no == payload.registration_no
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Aircraft '{payload.registration_no}' already registered."
        )
    aircraft = Aircraft(**payload.model_dump())
    db.add(aircraft)
    db.commit()
    db.refresh(aircraft)
    return aircraft


@router.get("/", response_model=AircraftListResponse)
def list_aircraft(
    status_filter:  Optional[AircraftStatusEnum] = Query(None, alias="status"),
    skip:           int     = Query(0,  ge=0),
    limit:          int     = Query(50, ge=1, le=200),
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    query = db.query(Aircraft)
    if status_filter:
        query = query.filter(Aircraft.status == status_filter)
    total    = query.count()
    aircraft = query.order_by(Aircraft.registration_no).offset(skip).limit(limit).all()
    return AircraftListResponse(total=total, aircraft=aircraft)


@router.get("/{aircraft_id}", response_model=AircraftResponse)
def get_aircraft(
    aircraft_id:    int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=404, detail=f"Aircraft {aircraft_id} not found.")
    return aircraft


@router.put("/{aircraft_id}", response_model=AircraftResponse)
def update_aircraft(
    aircraft_id:    int,
    payload:        AircraftUpdate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=404, detail=f"Aircraft {aircraft_id} not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(aircraft, field, value)
    db.commit()
    db.refresh(aircraft)
    return aircraft
