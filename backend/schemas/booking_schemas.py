# =============================================================
# AeroDesk — Booking, Ticket, Payment, Seat Schemas
# backend/schemas/booking_schemas.py
# =============================================================

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from decimal import Decimal
from backend.models.models import (
    BookingStatusEnum, PaymentStatusEnum,
    PaymentMethodEnum, SeatStatusEnum
)


# ── Seat ──────────────────────────────────────────────────────

class SeatResponse(BaseModel):
    seat_id:        int
    flight_id:      int
    fare_class_id:  int
    seat_number:    str
    status:         SeatStatusEnum
    class_name:     Optional[str] = None
    model_config = {"from_attributes": True}


class SeatAvailabilityResponse(BaseModel):
    flight_id:          int
    total_seats:        int
    available_seats:    int
    reserved_seats:     int
    occupied_seats:     int
    seats:              list[SeatResponse]


# ── Booking ───────────────────────────────────────────────────

class BookingCreate(BaseModel):
    passenger_id:   int
    flight_id:      int
    seat_id:        int
    model_config = {"from_attributes": True}


class BookingResponse(BaseModel):
    booking_id:     int
    passenger_id:   int
    flight_id:      int
    seat_id:        int
    staff_id:       int
    pnr:            str
    status:         BookingStatusEnum
    cancel_reason:  Optional[str]
    cancelled_at:   Optional[datetime]
    booked_at:      datetime
    model_config = {"from_attributes": True}


class CancellationRequest(BaseModel):
    cancel_reason: str


# ── Ticket ────────────────────────────────────────────────────

class TicketResponse(BaseModel):
    ticket_id:              int
    booking_id:             int
    fare_class_id:          int
    ticket_no:              str
    base_fare:              Decimal
    multiplier_snapshot:    Decimal
    final_fare:             Decimal
    issue_date:             datetime
    is_cancelled:           bool
    model_config = {"from_attributes": True}


# ── Payment ───────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    booking_id: int
    method:     PaymentMethodEnum
    amount:     Decimal
    model_config = {"from_attributes": True}


class PaymentResponse(BaseModel):
    payment_id:     int
    booking_id:     int
    method:         PaymentMethodEnum
    amount:         Decimal
    status:         PaymentStatusEnum
    refund_amount:  Decimal
    payment_date:   datetime
    updated_at:     datetime
    model_config = {"from_attributes": True}
