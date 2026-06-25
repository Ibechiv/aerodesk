# =============================================================
# AeroDesk — Flights + Schedules Router
# backend/routers/flights_router.py
# =============================================================
# Access: Super_Admin, Operations_Manager
# BR-004: Only Active aircraft can be assigned
# BR-007: arr_datetime must be > dep_datetime
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.models import (
    Flight, FlightSchedule, Aircraft, Airport,
    Staff, StaffRoleEnum, AircraftStatusEnum, FlightStatusEnum
)
from backend.auth.auth import require_roles
from backend.schemas.flight_schemas import (
    FlightCreate, FlightUpdate, FlightResponse, FlightListResponse,
    ScheduleCreate, ScheduleUpdate, ScheduleResponse
)

router = APIRouter()
ALLOWED_ROLES = (StaffRoleEnum.Super_Admin, StaffRoleEnum.Operations_Manager)


# ── Flights ───────────────────────────────────────────────────

@router.post("/", response_model=FlightResponse, status_code=status.HTTP_201_CREATED)
def create_flight(
    payload:        FlightCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """Create a new flight. BR-004: aircraft must be Active."""

    # Check flight number uniqueness
    if db.query(Flight).filter(Flight.flight_no == payload.flight_no).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Flight number '{payload.flight_no}' already exists."
        )

    # Validate origin airport exists
    origin = db.query(Airport).filter(Airport.airport_id == payload.origin_airport_id).first()
    if not origin:
        raise HTTPException(status_code=404, detail="Origin airport not found.")

    # Validate destination airport exists
    dest = db.query(Airport).filter(Airport.airport_id == payload.dest_airport_id).first()
    if not dest:
        raise HTTPException(status_code=404, detail="Destination airport not found.")

    # Validate airports are different
    if payload.origin_airport_id == payload.dest_airport_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Origin and destination airports must be different."
        )

    # BR-004: Aircraft must be Active
    aircraft = db.query(Aircraft).filter(Aircraft.aircraft_id == payload.aircraft_id).first()
    if not aircraft:
        raise HTTPException(status_code=404, detail="Aircraft not found.")
    if aircraft.status != AircraftStatusEnum.Active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Aircraft '{aircraft.registration_no}' is not Active (BR-004). Current status: {aircraft.status.value}"
        )

    flight = Flight(**payload.model_dump())
    db.add(flight)
    db.commit()
    db.refresh(flight)

    return FlightResponse(
        **{c.name: getattr(flight, c.name) for c in Flight.__table__.columns},
        origin_iata=origin.iata_code,
        dest_iata=dest.iata_code,
        aircraft_model=aircraft.model,
    )


@router.get("/", response_model=FlightListResponse)
def list_flights(
    status_filter:  Optional[FlightStatusEnum] = Query(None, alias="status"),
    origin:         Optional[str]   = Query(None, description="Origin IATA code"),
    destination:    Optional[str]   = Query(None, description="Destination IATA code"),
    skip:           int             = Query(0,  ge=0),
    limit:          int             = Query(50, ge=1, le=200),
    db:             Session         = Depends(get_db),
    current_user:   Staff           = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    query = db.query(Flight)
    if status_filter:
        query = query.filter(Flight.status == status_filter)
    if origin:
        origin_airport = db.query(Airport).filter(
            Airport.iata_code == origin.upper()
        ).first()
        if origin_airport:
            query = query.filter(Flight.origin_airport_id == origin_airport.airport_id)
    if destination:
        dest_airport = db.query(Airport).filter(
            Airport.iata_code == destination.upper()
        ).first()
        if dest_airport:
            query = query.filter(Flight.dest_airport_id == dest_airport.airport_id)

    total   = query.count()
    flights = query.order_by(Flight.created_at.desc()).offset(skip).limit(limit).all()

    result = []
    for f in flights:
        result.append(FlightResponse(
            **{c.name: getattr(f, c.name) for c in Flight.__table__.columns},
            origin_iata=f.origin_airport.iata_code,
            dest_iata=f.dest_airport.iata_code,
            aircraft_model=f.aircraft.model,
        ))
    return FlightListResponse(total=total, flights=result)


@router.get("/{flight_id}", response_model=FlightResponse)
def get_flight(
    flight_id:      int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
        StaffRoleEnum.Ground_Staff,
    ))
):
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")
    return FlightResponse(
        **{c.name: getattr(flight, c.name) for c in Flight.__table__.columns},
        origin_iata=flight.origin_airport.iata_code,
        dest_iata=flight.dest_airport.iata_code,
        aircraft_model=flight.aircraft.model,
    )


@router.put("/{flight_id}", response_model=FlightResponse)
def update_flight(
    flight_id:      int,
    payload:        FlightUpdate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")

    # BR-004 check if aircraft is being changed
    if payload.aircraft_id:
        aircraft = db.query(Aircraft).filter(
            Aircraft.aircraft_id == payload.aircraft_id
        ).first()
        if not aircraft:
            raise HTTPException(status_code=404, detail="Aircraft not found.")
        if aircraft.status != AircraftStatusEnum.Active:
            raise HTTPException(
                status_code=422,
                detail=f"Aircraft '{aircraft.registration_no}' is not Active (BR-004)."
            )

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(flight, field, value)
    db.commit()
    db.refresh(flight)

    return FlightResponse(
        **{c.name: getattr(flight, c.name) for c in Flight.__table__.columns},
        origin_iata=flight.origin_airport.iata_code,
        dest_iata=flight.dest_airport.iata_code,
        aircraft_model=flight.aircraft.model,
    )


# ── Schedules ─────────────────────────────────────────────────

@router.post("/{flight_id}/schedule", response_model=ScheduleResponse, status_code=201)
def create_schedule(
    flight_id:      int,
    payload:        ScheduleCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """Set departure/arrival schedule for a flight. BR-007: arr must be > dep."""
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")

    if db.query(FlightSchedule).filter(FlightSchedule.flight_id == flight_id).first():
        raise HTTPException(
            status_code=409,
            detail=f"Flight {flight_id} already has a schedule. Use PUT to update."
        )

    schedule = FlightSchedule(
        flight_id=flight_id,
        dep_datetime=payload.dep_datetime,
        arr_datetime=payload.arr_datetime,
        terminal=payload.terminal,
        gate=payload.gate,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return schedule


@router.get("/{flight_id}/schedule", response_model=ScheduleResponse)
def get_schedule(
    flight_id:      int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
        StaffRoleEnum.Ground_Staff,
    ))
):
    schedule = db.query(FlightSchedule).filter(
        FlightSchedule.flight_id == flight_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule found for flight {flight_id}.")
    return schedule


@router.put("/{flight_id}/schedule", response_model=ScheduleResponse)
def update_schedule(
    flight_id:      int,
    payload:        ScheduleUpdate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    schedule = db.query(FlightSchedule).filter(
        FlightSchedule.flight_id == flight_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail=f"No schedule found for flight {flight_id}.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, field, value)

    # Re-validate BR-007 after update
    if schedule.arr_datetime <= schedule.dep_datetime:
        raise HTTPException(
            status_code=422,
            detail="Arrival datetime must be after departure datetime (BR-007)."
        )

    db.commit()
    db.refresh(schedule)
    return schedule
