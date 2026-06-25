# =============================================================
# AeroDesk — Passengers Router
# backend/routers/passengers_router.py
# =============================================================
# Endpoints:
#   POST   /passengers/           — register new passenger
#   GET    /passengers/           — list all passengers (search/filter)
#   GET    /passengers/{id}       — get single passenger
#   PUT    /passengers/{id}       — update passenger
#   DELETE /passengers/{id}       — deactivate passenger
#   GET    /passengers/{id}/history — travel history
# =============================================================
# Access: Super_Admin, Operations_Manager, Reservation_Agent
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional

from backend.database import get_db
from backend.models.models import (
    Passenger, Booking, Flight, FlightSchedule,
    Ticket, Staff, StaffRoleEnum
)
from backend.auth.auth import require_roles
from backend.schemas.passenger_schemas import (
    PassengerCreate, PassengerUpdate,
    PassengerResponse, PassengerListResponse
)

router = APIRouter()

ALLOWED_ROLES = (
    StaffRoleEnum.Super_Admin,
    StaffRoleEnum.Operations_Manager,
    StaffRoleEnum.Reservation_Agent,
)


# =============================================================
# POST /passengers/ — Register new passenger
# =============================================================

@router.post(
    "/",
    response_model=PassengerResponse,
    status_code=status.HTTP_201_CREATED
)
def register_passenger(
    payload:        PassengerCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """Register a new passenger into the system."""

    # Check passport uniqueness
    existing_passport = db.query(Passenger).filter(
        Passenger.passport_no == payload.passport_no
    ).first()
    if existing_passport:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A passenger with passport number '{payload.passport_no}' already exists."
        )

    # Check email uniqueness
    existing_email = db.query(Passenger).filter(
        Passenger.email == payload.email
    ).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A passenger with email '{payload.email}' already exists."
        )

    # Validate gender
    if payload.gender not in ("Male", "Female", "Other"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Gender must be one of: Male, Female, Other"
        )

    passenger = Passenger(**payload.model_dump())
    db.add(passenger)
    db.commit()
    db.refresh(passenger)
    return passenger


# =============================================================
# GET /passengers/ — List all passengers with search/filter
# =============================================================

@router.get("/", response_model=PassengerListResponse)
def list_passengers(
    search:         Optional[str] = Query(None, description="Search by name, passport, or email"),
    skip:           int = Query(0,   ge=0),
    limit:          int = Query(50,  ge=1, le=200),
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """List all passengers. Supports search by name, passport number, or email."""

    query = db.query(Passenger)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            Passenger.full_name.ilike(search_term)  |
            Passenger.passport_no.ilike(search_term) |
            Passenger.email.ilike(search_term)       |
            Passenger.phone.ilike(search_term)
        )

    total       = query.count()
    passengers  = query.order_by(Passenger.created_at.desc()).offset(skip).limit(limit).all()

    return PassengerListResponse(total=total, passengers=passengers)


# =============================================================
# GET /passengers/{passenger_id} — Get single passenger
# =============================================================

@router.get("/{passenger_id}", response_model=PassengerResponse)
def get_passenger(
    passenger_id:   int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """Get a single passenger by ID."""

    passenger = db.query(Passenger).filter(
        Passenger.passenger_id == passenger_id
    ).first()

    if not passenger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passenger with ID {passenger_id} not found."
        )
    return passenger


# =============================================================
# PUT /passengers/{passenger_id} — Update passenger
# =============================================================

@router.put("/{passenger_id}", response_model=PassengerResponse)
def update_passenger(
    passenger_id:   int,
    payload:        PassengerUpdate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """Update passenger details. Only provided fields are updated."""

    passenger = db.query(Passenger).filter(
        Passenger.passenger_id == passenger_id
    ).first()

    if not passenger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passenger with ID {passenger_id} not found."
        )

    # Check email uniqueness if being updated
    if payload.email and payload.email != passenger.email:
        existing = db.query(Passenger).filter(
            Passenger.email == payload.email
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Email '{payload.email}' is already in use."
            )

    # Validate gender if being updated
    if payload.gender and payload.gender not in ("Male", "Female", "Other"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Gender must be one of: Male, Female, Other"
        )

    # Apply only provided fields
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(passenger, field, value)

    db.commit()
    db.refresh(passenger)
    return passenger


# =============================================================
# DELETE /passengers/{passenger_id} — Delete passenger
# =============================================================

@router.delete("/{passenger_id}", status_code=status.HTTP_200_OK)
def delete_passenger(
    passenger_id:   int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(StaffRoleEnum.Super_Admin))
):
    """
    Delete a passenger record.
    Restricted to Super_Admin only.
    Will fail if passenger has existing bookings (FK constraint).
    """

    passenger = db.query(Passenger).filter(
        Passenger.passenger_id == passenger_id
    ).first()

    if not passenger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passenger with ID {passenger_id} not found."
        )

    # Check for existing bookings
    has_bookings = db.query(Booking).filter(
        Booking.passenger_id == passenger_id
    ).first()

    if has_bookings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete passenger with existing booking records."
        )

    db.delete(passenger)
    db.commit()
    return {"message": f"Passenger {passenger_id} deleted successfully."}


# =============================================================
# GET /passengers/{passenger_id}/history — Travel history
# =============================================================

@router.get("/{passenger_id}/history")
def get_travel_history(
    passenger_id:   int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*ALLOWED_ROLES))
):
    """
    Returns full travel history for a passenger.
    Includes all bookings with flight, ticket, and payment details.
    """

    passenger = db.query(Passenger).filter(
        Passenger.passenger_id == passenger_id
    ).first()

    if not passenger:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passenger with ID {passenger_id} not found."
        )

    bookings = (
        db.query(Booking)
        .filter(Booking.passenger_id == passenger_id)
        .order_by(Booking.booked_at.desc())
        .all()
    )

    history = []
    for booking in bookings:
        flight      = booking.flight
        schedule    = flight.schedule
        ticket      = booking.ticket
        payment     = booking.payment

        history.append({
            "booking_id":           booking.booking_id,
            "pnr":                  booking.pnr,
            "booking_status":       booking.status.value,
            "booked_at":            booking.booked_at,
            "cancelled_at":         booking.cancelled_at,
            "flight_no":            flight.flight_no,
            "origin":               flight.origin_airport.iata_code,
            "destination":          flight.dest_airport.iata_code,
            "scheduled_departure":  schedule.dep_datetime if schedule else None,
            "scheduled_arrival":    schedule.arr_datetime if schedule else None,
            "flight_status":        flight.status.value,
            "seat_number":          booking.seat.seat_number,
            "travel_class":         booking.seat.fare_class.class_name,
            "ticket_no":            ticket.ticket_no    if ticket  else None,
            "final_fare":           float(ticket.final_fare) if ticket else None,
            "payment_status":       payment.status.value if payment else None,
            "payment_method":       payment.method.value if payment else None,
        })

    return {
        "passenger_id":     passenger.passenger_id,
        "full_name":        passenger.full_name,
        "passport_no":      passenger.passport_no,
        "total_trips":      len(history),
        "travel_history":   history,
    }
