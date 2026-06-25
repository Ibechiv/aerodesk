# =============================================================
# AeroDesk — Airports Router
# backend/routers/airports_router.py
# =============================================================
# Access: Super_Admin, Operations_Manager
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.models import Airport, Staff, StaffRoleEnum
from backend.auth.auth import require_roles
from backend.schemas.airport_schemas import (
    AirportCreate, AirportUpdate,
    AirportResponse, AirportListResponse
)

router = APIRouter()
ALLOWED_ROLES = (StaffRoleEnum.Super_Admin, StaffRoleEnum.Operations_Manager)


@router.post("/", response_model=AirportResponse, status_code=status.HTTP_201_CREATED)
def create_airport(
    payload:        AirportCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    existing = db.query(Airport).filter(Airport.iata_code == payload.iata_code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Airport with IATA code '{payload.iata_code}' already exists."
        )
    airport = Airport(**payload.model_dump())
    db.add(airport)
    db.commit()
    db.refresh(airport)
    return airport


@router.get("/", response_model=AirportListResponse)
def list_airports(
    search:         Optional[str]   = Query(None, description="Search by name, IATA, or city"),
    country:        Optional[str]   = Query(None),
    is_active:      Optional[bool]  = Query(None),
    skip:           int             = Query(0,  ge=0),
    limit:          int             = Query(50, ge=1, le=200),
    db:             Session         = Depends(get_db),
    current_user:   Staff           = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    query = db.query(Airport)
    if search:
        term = f"%{search}%"
        query = query.filter(
            Airport.airport_name.ilike(term) |
            Airport.iata_code.ilike(term)    |
            Airport.city.ilike(term)
        )
    if country:
        query = query.filter(Airport.country.ilike(f"%{country}%"))
    if is_active is not None:
        query = query.filter(Airport.is_active == is_active)

    total    = query.count()
    airports = query.order_by(Airport.iata_code).offset(skip).limit(limit).all()
    return AirportListResponse(total=total, airports=airports)


@router.get("/{airport_id}", response_model=AirportResponse)
def get_airport(
    airport_id:     int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    airport = db.query(Airport).filter(Airport.airport_id == airport_id).first()
    if not airport:
        raise HTTPException(status_code=404, detail=f"Airport {airport_id} not found.")
    return airport


@router.put("/{airport_id}", response_model=AirportResponse)
def update_airport(
    airport_id:     int,
    payload:        AirportUpdate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    airport = db.query(Airport).filter(Airport.airport_id == airport_id).first()
    if not airport:
        raise HTTPException(status_code=404, detail=f"Airport {airport_id} not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(airport, field, value)
    db.commit()
    db.refresh(airport)
    return airport


@router.delete("/{airport_id}", status_code=status.HTTP_200_OK)
def delete_airport(
    airport_id:     int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(StaffRoleEnum.Super_Admin))
):
    airport = db.query(Airport).filter(Airport.airport_id == airport_id).first()
    if not airport:
        raise HTTPException(status_code=404, detail=f"Airport {airport_id} not found.")
    airport.is_active = False
    db.commit()
    return {"message": f"Airport {airport.iata_code} deactivated successfully."}
