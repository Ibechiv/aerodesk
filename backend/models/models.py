# =============================================================
# AeroDesk — SQLAlchemy Models
# backend/models/models.py
# =============================================================
# 12 base table models + 1 view helper
# Mirrors the PostgreSQL 17.6 schema exactly
# All ENUMs, constraints, and relationships defined here
# =============================================================

from sqlalchemy import (
    Column, Integer, SmallInteger, String, Text,
    Boolean, Date, DateTime, Numeric,
    ForeignKey, UniqueConstraint, CheckConstraint,
    Enum as SAEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import enum


# =============================================================
# PYTHON ENUMS
# Mirror the PostgreSQL ENUM types
# =============================================================

class AircraftStatusEnum(str, enum.Enum):
    Active      = "Active"
    Maintenance = "Maintenance"
    Retired     = "Retired"

class FlightStatusEnum(str, enum.Enum):
    Scheduled   = "Scheduled"
    Boarding    = "Boarding"
    Departed    = "Departed"
    Arrived     = "Arrived"
    Cancelled   = "Cancelled"

class SeatStatusEnum(str, enum.Enum):
    Available   = "Available"
    Reserved    = "Reserved"
    Occupied    = "Occupied"

class BookingStatusEnum(str, enum.Enum):
    Pending     = "Pending"
    Confirmed   = "Confirmed"
    Cancelled   = "Cancelled"

class PaymentStatusEnum(str, enum.Enum):
    Pending     = "Pending"
    Completed   = "Completed"
    Refunded    = "Refunded"

class PaymentMethodEnum(str, enum.Enum):
    Cash            = "Cash"
    Card            = "Card"
    Bank_Transfer   = "Bank_Transfer"

class BoardingStatusEnum(str, enum.Enum):
    Boarded     = "Boarded"
    No_Show     = "No_Show"

class StaffRoleEnum(str, enum.Enum):
    Super_Admin         = "Super_Admin"
    Operations_Manager  = "Operations_Manager"
    Reservation_Agent   = "Reservation_Agent"
    Ground_Staff        = "Ground_Staff"
    Finance_Officer     = "Finance_Officer"


# =============================================================
# TABLE 1 — Passenger
# =============================================================

class Passenger(Base):
    __tablename__ = "passengers"

    passenger_id    = Column(Integer,       primary_key=True, autoincrement=True)
    full_name       = Column(String(150),   nullable=False)
    date_of_birth   = Column(Date,          nullable=False)
    gender          = Column(String(20),    nullable=False)
    nationality     = Column(String(100),   nullable=False)
    passport_no     = Column(String(50),    nullable=False, unique=True)
    phone           = Column(String(20),    nullable=False)
    email           = Column(String(150),   nullable=False, unique=True)
    created_at      = Column(DateTime,      nullable=False, server_default=func.now())

    # Relationships
    bookings            = relationship("Booking",         back_populates="passenger")
    boarding_records    = relationship("BoardingRecord",  back_populates="passenger")

    __table_args__ = (
        CheckConstraint("gender IN ('Male', 'Female', 'Other')", name="chk_gender"),
        UniqueConstraint("passport_no",  name="uq_passenger_passport"),
        UniqueConstraint("email",        name="uq_passenger_email"),
    )

    def __repr__(self):
        return f"<Passenger id={self.passenger_id} name={self.full_name}>"


# =============================================================
# TABLE 2 — Airport
# =============================================================

class Airport(Base):
    __tablename__ = "airports"

    airport_id      = Column(Integer,       primary_key=True, autoincrement=True)
    airport_name    = Column(String(200),   nullable=False)
    iata_code       = Column(String(3),     nullable=False, unique=True)
    city            = Column(String(100),   nullable=False)
    country         = Column(String(100),   nullable=False)
    terminals       = Column(SmallInteger,  nullable=False, default=1)
    is_active       = Column(Boolean,       nullable=False, default=True)
    created_at      = Column(DateTime,      nullable=False, server_default=func.now())

    # Relationships
    origin_flights  = relationship(
        "Flight",
        foreign_keys="Flight.origin_airport_id",
        back_populates="origin_airport"
    )
    dest_flights    = relationship(
        "Flight",
        foreign_keys="Flight.dest_airport_id",
        back_populates="dest_airport"
    )

    __table_args__ = (
        UniqueConstraint("iata_code", name="uq_airport_iata"),
        CheckConstraint("terminals >= 1", name="chk_terminals"),
    )

    def __repr__(self):
        return f"<Airport {self.iata_code} — {self.city}>"


# =============================================================
# TABLE 3 — Aircraft
# =============================================================

class Aircraft(Base):
    __tablename__ = "aircraft"

    aircraft_id     = Column(Integer,       primary_key=True, autoincrement=True)
    registration_no = Column(String(20),    nullable=False, unique=True)
    model           = Column(String(100),   nullable=False)
    seat_capacity   = Column(SmallInteger,  nullable=False)
    status          = Column(
                        SAEnum(AircraftStatusEnum, name="aircraft_status"),
                        nullable=False,
                        default=AircraftStatusEnum.Active
                      )
    created_at      = Column(DateTime,      nullable=False, server_default=func.now())

    # Relationships
    flights         = relationship("Flight", back_populates="aircraft")

    __table_args__ = (
        UniqueConstraint("registration_no", name="uq_aircraft_registration"),
        CheckConstraint("seat_capacity > 0", name="chk_seat_capacity"),
    )

    def __repr__(self):
        return f"<Aircraft {self.registration_no} — {self.model}>"


# =============================================================
# TABLE 4 — FareClass
# =============================================================

class FareClass(Base):
    __tablename__ = "fare_classes"

    fare_class_id           = Column(Integer,       primary_key=True, autoincrement=True)
    class_name              = Column(String(50),    nullable=False, unique=True)
    multiplier              = Column(Numeric(4, 2), nullable=False)
    baggage_allowance_kg    = Column(SmallInteger,  nullable=False)
    description             = Column(Text)
    created_at              = Column(DateTime,      nullable=False, server_default=func.now())

    # Relationships
    seats   = relationship("Seat",   back_populates="fare_class")
    tickets = relationship("Ticket", back_populates="fare_class")

    __table_args__ = (
        UniqueConstraint("class_name",  name="uq_fare_class_name"),
        CheckConstraint("multiplier > 0",               name="chk_multiplier"),
        CheckConstraint("baggage_allowance_kg >= 0",    name="chk_baggage"),
    )

    def __repr__(self):
        return f"<FareClass {self.class_name} x{self.multiplier}>"


# =============================================================
# TABLE 5 — Staff
# =============================================================

class Staff(Base):
    __tablename__ = "staff"

    staff_id        = Column(Integer,       primary_key=True, autoincrement=True)
    full_name       = Column(String(150),   nullable=False)
    email           = Column(String(150),   nullable=False, unique=True)
    role            = Column(
                        SAEnum(StaffRoleEnum, name="staff_role"),
                        nullable=False
                      )
    password_hash   = Column(String(255),   nullable=False)
    is_active       = Column(Boolean,       nullable=False, default=True)
    created_at      = Column(DateTime,      nullable=False, server_default=func.now())

    # Relationships
    bookings        = relationship("Booking", back_populates="staff")

    __table_args__ = (
        UniqueConstraint("email", name="uq_staff_email"),
    )

    def __repr__(self):
        return f"<Staff {self.email} — {self.role}>"


# =============================================================
# TABLE 6 — Flight
# =============================================================

class Flight(Base):
    __tablename__ = "flights"

    flight_id           = Column(Integer,       primary_key=True, autoincrement=True)
    flight_no           = Column(String(20),    nullable=False, unique=True)
    origin_airport_id   = Column(Integer,       ForeignKey("airports.airport_id",  onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    dest_airport_id     = Column(Integer,       ForeignKey("airports.airport_id",  onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    aircraft_id         = Column(Integer,       ForeignKey("aircraft.aircraft_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    base_fare           = Column(Numeric(12,2), nullable=False)
    status              = Column(
                            SAEnum(FlightStatusEnum, name="flight_status"),
                            nullable=False,
                            default=FlightStatusEnum.Scheduled
                          )
    created_at          = Column(DateTime,      nullable=False, server_default=func.now())

    # Relationships
    origin_airport  = relationship("Airport",        foreign_keys=[origin_airport_id], back_populates="origin_flights")
    dest_airport    = relationship("Airport",        foreign_keys=[dest_airport_id],   back_populates="dest_flights")
    aircraft        = relationship("Aircraft",       back_populates="flights")
    schedule        = relationship("FlightSchedule", back_populates="flight",          uselist=False)
    seats           = relationship("Seat",           back_populates="flight")
    bookings        = relationship("Booking",        back_populates="flight")
    boarding_records = relationship("BoardingRecord", back_populates="flight")

    __table_args__ = (
        UniqueConstraint("flight_no", name="uq_flight_no"),
        CheckConstraint("origin_airport_id <> dest_airport_id", name="chk_different_airports"),
        CheckConstraint("base_fare > 0",                        name="chk_base_fare"),
    )

    def __repr__(self):
        return f"<Flight {self.flight_no} — {self.status}>"


# =============================================================
# TABLE 7 — FlightSchedule
# =============================================================

class FlightSchedule(Base):
    __tablename__ = "flight_schedules"

    schedule_id     = Column(Integer,   primary_key=True, autoincrement=True)
    flight_id       = Column(Integer,   ForeignKey("flights.flight_id", onupdate="CASCADE", ondelete="CASCADE"), nullable=False, unique=True)
    dep_datetime    = Column(DateTime,  nullable=False)
    arr_datetime    = Column(DateTime,  nullable=False)
    actual_dep      = Column(DateTime,  nullable=True)
    actual_arr      = Column(DateTime,  nullable=True)
    terminal        = Column(String(20),nullable=True)
    gate            = Column(String(20),nullable=True)
    created_at      = Column(DateTime,  nullable=False, server_default=func.now())

    # Relationships
    flight          = relationship("Flight", back_populates="schedule")

    __table_args__ = (
        UniqueConstraint("flight_id", name="uq_schedule_flight"),
        CheckConstraint("arr_datetime > dep_datetime",  name="chk_arr_after_dep"),
    )

    def __repr__(self):
        return f"<FlightSchedule flight_id={self.flight_id} dep={self.dep_datetime}>"


# =============================================================
# TABLE 8 — Seat
# =============================================================

class Seat(Base):
    __tablename__ = "seats"

    seat_id         = Column(Integer,   primary_key=True, autoincrement=True)
    flight_id       = Column(Integer,   ForeignKey("flights.flight_id",          onupdate="CASCADE", ondelete="CASCADE"),  nullable=False)
    fare_class_id   = Column(Integer,   ForeignKey("fare_classes.fare_class_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    seat_number     = Column(String(10),nullable=False)
    status          = Column(
                        SAEnum(SeatStatusEnum, name="seat_status"),
                        nullable=False,
                        default=SeatStatusEnum.Available
                      )
    created_at      = Column(DateTime,  nullable=False, server_default=func.now())

    # Relationships
    flight          = relationship("Flight",    back_populates="seats")
    fare_class      = relationship("FareClass", back_populates="seats")
    booking         = relationship("Booking",   back_populates="seat", uselist=False)

    __table_args__ = (
        # BR-001 — primary integrity rule
        UniqueConstraint("flight_id", "seat_number", name="uq_seat_per_flight"),
    )

    def __repr__(self):
        return f"<Seat {self.seat_number} flight_id={self.flight_id} — {self.status}>"


# =============================================================
# TABLE 9 — Booking
# =============================================================

class Booking(Base):
    __tablename__ = "bookings"

    booking_id      = Column(Integer,   primary_key=True, autoincrement=True)
    passenger_id    = Column(Integer,   ForeignKey("passengers.passenger_id",   onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    flight_id       = Column(Integer,   ForeignKey("flights.flight_id",         onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    seat_id         = Column(Integer,   ForeignKey("seats.seat_id",             onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    staff_id        = Column(Integer,   ForeignKey("staff.staff_id",            onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    pnr             = Column(String(20),nullable=False, unique=True)
    status          = Column(
                        SAEnum(BookingStatusEnum, name="booking_status"),
                        nullable=False,
                        default=BookingStatusEnum.Pending
                      )
    cancel_reason   = Column(Text,      nullable=True)
    cancelled_at    = Column(DateTime,  nullable=True)
    booked_at       = Column(DateTime,  nullable=False, server_default=func.now())

    # Relationships
    passenger       = relationship("Passenger",     back_populates="bookings")
    flight          = relationship("Flight",        back_populates="bookings")
    seat            = relationship("Seat",          back_populates="booking")
    staff           = relationship("Staff",         back_populates="bookings")
    ticket          = relationship("Ticket",        back_populates="booking",  uselist=False)
    payment         = relationship("Payment",       back_populates="booking",  uselist=False)
    boarding_record = relationship("BoardingRecord",back_populates="booking",  uselist=False)

    __table_args__ = (
        UniqueConstraint("pnr",                       name="uq_booking_pnr"),
        # BR-005 — one booking per passenger per flight
        UniqueConstraint("flight_id", "passenger_id", name="uq_passenger_per_flight"),
        CheckConstraint(
            "status != 'Cancelled' OR cancel_reason IS NOT NULL",
            name="chk_cancel_reason"
        ),
    )

    def __repr__(self):
        return f"<Booking {self.pnr} — {self.status}>"


# =============================================================
# TABLE 10 — Ticket
# =============================================================

class Ticket(Base):
    __tablename__ = "tickets"

    ticket_id           = Column(Integer,       primary_key=True, autoincrement=True)
    booking_id          = Column(Integer,       ForeignKey("bookings.booking_id",         onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, unique=True)
    fare_class_id       = Column(Integer,       ForeignKey("fare_classes.fare_class_id",  onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    ticket_no           = Column(String(30),    nullable=False, unique=True)
    base_fare           = Column(Numeric(12,2), nullable=False)
    multiplier_snapshot = Column(Numeric(4,2),  nullable=False)
    final_fare          = Column(Numeric(12,2), nullable=False)
    issue_date          = Column(DateTime,      nullable=False, server_default=func.now())
    is_cancelled        = Column(Boolean,       nullable=False, default=False)

    # Relationships
    booking     = relationship("Booking",   back_populates="ticket")
    fare_class  = relationship("FareClass", back_populates="tickets")

    __table_args__ = (
        UniqueConstraint("booking_id",  name="uq_ticket_booking"),
        UniqueConstraint("ticket_no",   name="uq_ticket_no"),
        CheckConstraint("final_fare > 0",           name="chk_final_fare"),
        CheckConstraint("base_fare > 0",            name="chk_base_fare"),
        CheckConstraint("multiplier_snapshot > 0",  name="chk_multiplier"),
    )

    def __repr__(self):
        return f"<Ticket {self.ticket_no} final_fare={self.final_fare}>"


# =============================================================
# TABLE 11 — Payment
# =============================================================

class Payment(Base):
    __tablename__ = "payments"

    payment_id      = Column(Integer,       primary_key=True, autoincrement=True)
    booking_id      = Column(Integer,       ForeignKey("bookings.booking_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, unique=True)
    method          = Column(
                        SAEnum(PaymentMethodEnum, name="payment_method"),
                        nullable=False
                      )
    amount          = Column(Numeric(12,2), nullable=False)
    status          = Column(
                        SAEnum(PaymentStatusEnum, name="payment_status"),
                        nullable=False,
                        default=PaymentStatusEnum.Pending
                      )
    refund_amount   = Column(Numeric(12,2), nullable=False, default=0)
    payment_date    = Column(DateTime,      nullable=False, server_default=func.now())
    updated_at      = Column(DateTime,      nullable=False, server_default=func.now(), onupdate=func.now())

    # Relationships
    booking         = relationship("Booking", back_populates="payment")

    __table_args__ = (
        UniqueConstraint("booking_id",  name="uq_payment_booking"),
        CheckConstraint("amount > 0",           name="chk_amount"),
        CheckConstraint("refund_amount >= 0",   name="chk_refund_amount"),
        CheckConstraint(
            "status != 'Refunded' OR refund_amount > 0",
            name="chk_refund_on_cancel"
        ),
    )

    def __repr__(self):
        return f"<Payment booking_id={self.booking_id} amount={self.amount} — {self.status}>"


# =============================================================
# TABLE 12 — BoardingRecord
# =============================================================

class BoardingRecord(Base):
    __tablename__ = "boarding_records"

    boarding_id     = Column(Integer,   primary_key=True, autoincrement=True)
    booking_id      = Column(Integer,   ForeignKey("bookings.booking_id",     onupdate="CASCADE", ondelete="RESTRICT"), nullable=False, unique=True)
    passenger_id    = Column(Integer,   ForeignKey("passengers.passenger_id", onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    flight_id       = Column(Integer,   ForeignKey("flights.flight_id",       onupdate="CASCADE", ondelete="RESTRICT"), nullable=False)
    status          = Column(
                        SAEnum(BoardingStatusEnum, name="boarding_status"),
                        nullable=False
                      )
    boarded_at      = Column(DateTime,  nullable=False, server_default=func.now())

    # Relationships
    booking     = relationship("Booking",   back_populates="boarding_record")
    passenger   = relationship("Passenger", back_populates="boarding_records")
    flight      = relationship("Flight",    back_populates="boarding_records")

    __table_args__ = (
        UniqueConstraint("booking_id", name="uq_boarding_booking"),
    )

    def __repr__(self):
        return f"<BoardingRecord booking_id={self.booking_id} — {self.status}>"
