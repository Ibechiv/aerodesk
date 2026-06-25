# =============================================================
# AeroDesk — Bookings, Seats, Tickets, Payments Router
# backend/routers/bookings_router.py
# =============================================================
# BR-001: No duplicate seat on same flight
# BR-002: Seat status updates atomically with booking
# BR-003: Ticket issued only after payment confirmed
# BR-005: One booking per passenger per flight
# BR-008: Cancellation atomically frees seat
# BR-009: Refund only on Completed payment cancellation
# BR-011: Capacity check before booking
# BR-012: final_fare = base_fare x class multiplier
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional
import uuid
import random
import string

from backend.database import get_db
from backend.models.models import (
    Booking, Ticket, Payment, Seat, Flight, Passenger,
    Staff, StaffRoleEnum,
    BookingStatusEnum, SeatStatusEnum,
    PaymentStatusEnum, PaymentMethodEnum
)
from backend.auth.auth import require_roles
from backend.schemas.booking_schemas import (
    BookingCreate, BookingResponse, CancellationRequest,
    TicketResponse, PaymentCreate, PaymentResponse,
    SeatResponse, SeatAvailabilityResponse
)

router = APIRouter()

BOOKING_ROLES = (
    StaffRoleEnum.Super_Admin,
    StaffRoleEnum.Reservation_Agent,
)

PAYMENT_ROLES = (
    StaffRoleEnum.Super_Admin,
    StaffRoleEnum.Reservation_Agent,
    StaffRoleEnum.Finance_Officer,
)


def generate_pnr() -> str:
    """Generate a unique 6-character alphanumeric PNR."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def generate_ticket_no() -> str:
    """Generate a unique ticket number in format TKT-XXXXXXXX."""
    return f"TKT-{''.join(random.choices(string.digits, k=8))}"


# =============================================================
# SEATS
# =============================================================

@router.get("/seats/{flight_id}", response_model=SeatAvailabilityResponse)
def get_seat_availability(
    flight_id:      int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    """
    Returns all seats for a flight with their current status.
    Used to populate the seat map on the booking screen.
    """
    flight = db.query(Flight).filter(Flight.flight_id == flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail=f"Flight {flight_id} not found.")

    seats = db.query(Seat).filter(Seat.flight_id == flight_id).all()

    seat_responses = [
        SeatResponse(
            seat_id=s.seat_id,
            flight_id=s.flight_id,
            fare_class_id=s.fare_class_id,
            seat_number=s.seat_number,
            status=s.status,
            class_name=s.fare_class.class_name,
        )
        for s in seats
    ]

    return SeatAvailabilityResponse(
        flight_id=flight_id,
        total_seats=len(seats),
        available_seats=sum(1 for s in seats if s.status == SeatStatusEnum.Available),
        reserved_seats=sum(1 for s in seats if s.status == SeatStatusEnum.Reserved),
        occupied_seats=sum(1 for s in seats if s.status == SeatStatusEnum.Occupied),
        seats=seat_responses,
    )


# =============================================================
# BOOKINGS
# =============================================================

@router.post("/", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload:        BookingCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*BOOKING_ROLES))
):
    """
    Create a new booking — reserves a seat atomically.
    Enforces: BR-001, BR-002, BR-005, BR-011
    """

    # Validate passenger exists
    passenger = db.query(Passenger).filter(
        Passenger.passenger_id == payload.passenger_id
    ).first()
    if not passenger:
        raise HTTPException(status_code=404, detail="Passenger not found.")

    # Validate flight exists
    flight = db.query(Flight).filter(Flight.flight_id == payload.flight_id).first()
    if not flight:
        raise HTTPException(status_code=404, detail="Flight not found.")

    # Check flight is not cancelled or departed
    if flight.status.value in ("Departed", "Arrived", "Cancelled"):
        raise HTTPException(
            status_code=422,
            detail=f"Cannot book a flight with status '{flight.status.value}'."
        )

    # BR-005: One booking per passenger per flight
    existing_booking = db.query(Booking).filter(
        Booking.flight_id   == payload.flight_id,
        Booking.passenger_id == payload.passenger_id,
        Booking.status      != BookingStatusEnum.Cancelled
    ).first()
    if existing_booking:
        raise HTTPException(
            status_code=409,
            detail="This passenger already has an active booking on this flight (BR-005)."
        )

    # Validate seat exists and belongs to this flight
    seat = db.query(Seat).filter(
        Seat.seat_id    == payload.seat_id,
        Seat.flight_id  == payload.flight_id
    ).first()
    if not seat:
        raise HTTPException(
            status_code=404,
            detail="Seat not found on this flight."
        )

    # BR-001: Seat must be Available
    if seat.status != SeatStatusEnum.Available:
        raise HTTPException(
            status_code=409,
            detail=f"Seat '{seat.seat_number}' is not available. Current status: {seat.status.value} (BR-001)."
        )

    # BR-011: Capacity check
    confirmed_count = db.query(Booking).filter(
        Booking.flight_id == payload.flight_id,
        Booking.status.in_([BookingStatusEnum.Pending, BookingStatusEnum.Confirmed])
    ).count()

    if confirmed_count >= flight.aircraft.seat_capacity:
        raise HTTPException(
            status_code=409,
            detail=f"Flight is at full capacity ({flight.aircraft.seat_capacity} seats). No new bookings allowed (BR-011)."
        )

    # Generate unique PNR
    pnr = generate_pnr()
    while db.query(Booking).filter(Booking.pnr == pnr).first():
        pnr = generate_pnr()

    # BR-002: Update seat status atomically in same transaction
    seat.status = SeatStatusEnum.Reserved

    booking = Booking(
        passenger_id=payload.passenger_id,
        flight_id=payload.flight_id,
        seat_id=payload.seat_id,
        staff_id=current_user.staff_id,
        pnr=pnr,
        status=BookingStatusEnum.Pending,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/", response_model=list[BookingResponse])
def list_bookings(
    flight_id:      Optional[int]               = Query(None),
    passenger_id:   Optional[int]               = Query(None),
    status_filter:  Optional[BookingStatusEnum] = Query(None, alias="status"),
    skip:           int                         = Query(0,  ge=0),
    limit:          int                         = Query(50, ge=1, le=200),
    db:             Session                     = Depends(get_db),
    current_user:   Staff                       = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    query = db.query(Booking)
    if flight_id:
        query = query.filter(Booking.flight_id == flight_id)
    if passenger_id:
        query = query.filter(Booking.passenger_id == passenger_id)
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    return query.order_by(Booking.booked_at.desc()).offset(skip).limit(limit).all()


@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id:     int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found.")
    return booking


@router.get("/pnr/{pnr}", response_model=BookingResponse)
def get_booking_by_pnr(
    pnr:            str,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Operations_Manager,
        StaffRoleEnum.Reservation_Agent,
    ))
):
    """Search booking by PNR — used in ticket cancellation screen."""
    booking = db.query(Booking).filter(Booking.pnr == pnr.upper()).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"No booking found with PNR '{pnr}'.")
    return booking


# =============================================================
# CANCELLATION
# BR-008: Seat freed atomically
# BR-009: Refund created if payment was Completed
# =============================================================

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id:     int,
    payload:        CancellationRequest,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*BOOKING_ROLES))
):
    """
    Cancel a booking. Atomically:
    - Sets booking status to Cancelled
    - Frees the seat back to Available (BR-008)
    - Creates refund record if payment was Completed (BR-009)
    """
    from datetime import datetime, timezone

    booking = db.query(Booking).filter(Booking.booking_id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail=f"Booking {booking_id} not found.")

    if booking.status == BookingStatusEnum.Cancelled:
        raise HTTPException(status_code=409, detail="Booking is already cancelled.")

    # BR-008: Free the seat atomically
    seat = db.query(Seat).filter(Seat.seat_id == booking.seat_id).first()
    if seat:
        seat.status = SeatStatusEnum.Available

    # BR-009: Handle refund if payment was Completed
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if payment and payment.status == PaymentStatusEnum.Completed:
        payment.status          = PaymentStatusEnum.Refunded
        payment.refund_amount   = payment.amount

    # Cancelled the ticket
    ticket = db.query(Ticket).filter(Ticket.booking_id == booking_id).first()
    if ticket:
        ticket.is_cancelled = True

    # Update booking
    booking.status          = BookingStatusEnum.Cancelled
    booking.cancel_reason   = payload.cancel_reason
    booking.cancelled_at    = datetime.now(timezone.utc)

    db.commit()
    db.refresh(booking)
    return booking


# =============================================================
# PAYMENTS
# BR-003: Ticket issued only after Completed payment
# =============================================================

@router.post("/payments/", response_model=PaymentResponse, status_code=201)
def process_payment(
    payload:        PaymentCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*PAYMENT_ROLES))
):
    """
    Process payment for a booking.
    On Completed payment: booking → Confirmed, ticket auto-issued (BR-003).
    """

    booking = db.query(Booking).filter(Booking.booking_id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if booking.status == BookingStatusEnum.Cancelled:
        raise HTTPException(status_code=409, detail="Cannot process payment for a cancelled booking.")

    # Check no existing payment
    existing_payment = db.query(Payment).filter(
        Payment.booking_id == payload.booking_id
    ).first()
    if existing_payment:
        raise HTTPException(
            status_code=409,
            detail="A payment record already exists for this booking."
        )

    # Create payment
    payment = Payment(
        booking_id=payload.booking_id,
        method=payload.method,
        amount=payload.amount,
        status=PaymentStatusEnum.Completed,
        refund_amount=0,
    )
    db.add(payment)

    # BR-003: Confirm booking and issue ticket
    booking.status = BookingStatusEnum.Confirmed

    # BR-012: Calculate final_fare = base_fare x multiplier
    seat        = booking.seat
    fare_class  = seat.fare_class
    flight      = booking.flight
    final_fare  = float(flight.base_fare) * float(fare_class.multiplier)

    # Generate unique ticket number
    ticket_no = generate_ticket_no()
    while db.query(Ticket).filter(Ticket.ticket_no == ticket_no).first():
        ticket_no = generate_ticket_no()

    ticket = Ticket(
        booking_id=booking.booking_id,
        fare_class_id=fare_class.fare_class_id,
        ticket_no=ticket_no,
        base_fare=flight.base_fare,
        multiplier_snapshot=fare_class.multiplier,
        final_fare=final_fare,
        is_cancelled=False,
    )
    db.add(ticket)
    db.commit()
    db.refresh(payment)
    return payment


@router.get("/payments/{booking_id}", response_model=PaymentResponse)
def get_payment(
    booking_id:     int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(*PAYMENT_ROLES))
):
    payment = db.query(Payment).filter(Payment.booking_id == booking_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail=f"No payment found for booking {booking_id}.")
    return payment


# =============================================================
# TICKETS
# =============================================================

@router.get("/tickets/{booking_id}", response_model=TicketResponse)
def get_ticket(
    booking_id:     int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Reservation_Agent,
        StaffRoleEnum.Ground_Staff,
    ))
):
    ticket = db.query(Ticket).filter(Ticket.booking_id == booking_id).first()
    if not ticket:
        raise HTTPException(
            status_code=404,
            detail=f"No ticket found for booking {booking_id}. Payment may not have been completed yet."
        )
    return ticket


@router.get("/tickets/number/{ticket_no}", response_model=TicketResponse)
def get_ticket_by_number(
    ticket_no:      str,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(
        StaffRoleEnum.Super_Admin,
        StaffRoleEnum.Reservation_Agent,
        StaffRoleEnum.Ground_Staff,
    ))
):
    """Search ticket by ticket number — used in cancellation screen."""
    ticket = db.query(Ticket).filter(Ticket.ticket_no == ticket_no.upper()).first()
    if not ticket:
        raise HTTPException(status_code=404, detail=f"Ticket '{ticket_no}' not found.")
    return ticket
