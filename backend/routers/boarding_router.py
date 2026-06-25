# =============================================================
# AeroDesk — Boarding + Manifest Router
# backend/routers/boarding_router.py
# =============================================================
# BR-006: Only Confirmed bookings can be boarded
# Manifest served from vw_flight_manifest VIEW
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional

from backend.database import get_db
from backend.models.models import (
    BoardingRecord, Booking, Flight,
    Staff, StaffRoleEnum,
    BookingStatusEnum, BoardingStatusEnum, SeatStatusEnum
)
from backend.auth.auth import require_roles

router = APIRouter()

BOARDING_ROLES = (
    StaffRoleEnum.Super_Admin,
    StaffRoleEnum.Ground_Staff,
)


# =============================================================
# BOARDING MANAGEMENT
# =============================================================

@router.get("/flight/{flight_id}")
def get_boarding_list(
    flight_id:      int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*BOARDING_ROLES))
):
    """
    Returns all confirmed passengers for a flight
    with their current boarding status.
    Used to populate the Boarding Management screen.
    """
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")

    confirmed_bookings = db.query(Booking).filter(
        Booking.flight_id   == flight_id,
        Booking.status      == BookingStatusEnum.Confirmed
    ).all()

    boarding_list = []
    for booking in confirmed_bookings:
        boarding_record = booking.boarding_record
        boarding_list.append({
            "booking_id":       booking.booking_id,
            "pnr":              booking.pnr,
            "passenger_id":     booking.passenger.passenger_id,
            "passenger_name":   booking.passenger.full_name,
            "passport_no":      booking.passenger.passport_no,
            "seat_number":      booking.seat.seat_number,
            "travel_class":     booking.seat.fare_class.class_name,
            "ticket_no":        booking.ticket.ticket_no if booking.ticket else None,
            "boarding_status":  boarding_record.status.value if boarding_record else "Not Boarded",
            "boarded_at":       boarding_record.boarded_at if boarding_record else None,
        })

    total_confirmed = len(confirmed_bookings)
    total_boarded   = sum(1 for b in boarding_list if b["boarding_status"] == "Boarded")

    return {
        "flight_id":        flight_id,
        "flight_no":        flight.flight_no,
        "flight_status":    flight.status.value,
        "total_confirmed":  total_confirmed,
        "total_boarded":    total_boarded,
        "boarding_percent": round((total_boarded / total_confirmed * 100) if total_confirmed > 0 else 0, 1),
        "passengers":       boarding_list,
    }


@router.post("/record", status_code=status.HTTP_201_CREATED)
def record_boarding(
    booking_id:     int,
    board_status:   BoardingStatusEnum,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*BOARDING_ROLES))
):
    """
    Record boarding status for a passenger.
    BR-006: Only Confirmed bookings can be boarded.
    """
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    # BR-006: Must be Confirmed
    if booking.status != BookingStatusEnum.Confirmed:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot board passenger. Booking status is '{booking.status.value}'. Must be Confirmed (BR-006)."
        )

    # Check if already boarded
    existing = db.query(BoardingRecord).filter(
        BoardingRecord.booking_id == booking_id
    ).first()
    if existing:
        existing.status = board_status
        db.commit()
        db.refresh(existing)
        return {"message": f"Boarding status updated to '{board_status.value}'.", "boarding_id": existing.boarding_id}

    # Update seat to Occupied if boarded
    if board_status == BoardingStatusEnum.Boarded:
        booking.seat.status = SeatStatusEnum.Occupied

    boarding = BoardingRecord(
        booking_id=booking_id,
        passenger_id=booking.passenger_id,
        flight_id=booking.flight_id,
        status=board_status,
    )
    db.add(boarding)
    db.commit()
    db.refresh(boarding)

    return {
        "message":      f"Passenger '{booking.passenger.full_name}' marked as {board_status.value}.",
        "boarding_id":  boarding.boarding_id,
        "boarded_at":   boarding.boarded_at,
    }


# =============================================================
# FLIGHT MANIFEST — from vw_flight_manifest VIEW
# =============================================================

@router.get("/manifest/{flight_id}")
def get_flight_manifest(
    flight_id:          int,
    boarding_status:    Optional[str] = Query(
                            None,
                            description="Filter: Boarded, No_Show, Not Boarded"
                        ),
    db:                 Session = Depends(get_db),
    current_user:       Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Ground_Staff,
    ))
):
    """
    Returns the live flight manifest from vw_flight_manifest VIEW.
    Optionally filter by boarding_status.
    """
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")

    # Query the PostgreSQL view directly
    sql = text("""
        SELECT
            flight_no,
            flight_id,
            scheduled_departure,
            scheduled_arrival,
            origin_iata,
            destination_iata,
            passenger_id,
            passenger_name,
            passport_no,
            seat_number,
            travel_class,
            ticket_no,
            pnr,
            booking_id,
            booking_status,
            boarding_status,
            boarded_at,
            final_fare
        FROM vw_flight_manifest
        WHERE flight_id = :flight_id
        ORDER BY seat_number
    """)

    results = db.execute(sql, {"flight_id": flight_id}).mappings().all()

    manifest = [dict(row) for row in results]

    # Filter by boarding status if requested
    if boarding_status:
        manifest = [
            r for r in manifest
            if r["boarding_status"].lower() == boarding_status.lower()
        ]

    return {
        "flight_id":            flight_id,
        "flight_no":            flight.flight_no,
        "origin":               flight.origin_airport.iata_code,
        "destination":          flight.dest_airport.iata_code,
        "total_passengers":     len(manifest),
        "generated_at":         db.execute(text("SELECT NOW()")).scalar(),
        "manifest":             manifest,
    }
