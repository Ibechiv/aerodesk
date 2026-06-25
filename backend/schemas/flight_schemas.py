# =============================================================
# AeroDesk — Flight + Schedule Schemas
# backend/schemas/flight_schemas.py
# =============================================================

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
from decimal import Decimal
from backend.models.models import FlightStatusEnum


class FlightCreate(BaseModel):
    flight_no:          str
    origin_airport_id:  int
    dest_airport_id:    int
    aircraft_id:        int
    base_fare:          Decimal
    model_config = {"from_attributes": True}


class FlightUpdate(BaseModel):
    aircraft_id:    Optional[int]               = None
    base_fare:      Optional[Decimal]           = None
    status:         Optional[FlightStatusEnum]  = None


class FlightResponse(BaseModel):
    flight_id:          int
    flight_no:          str
    origin_airport_id:  int
    dest_airport_id:    int
    aircraft_id:        int
    base_fare:          Decimal
    status:             FlightStatusEnum
    created_at:         datetime
    origin_iata:        Optional[str] = None
    dest_iata:          Optional[str] = None
    aircraft_model:     Optional[str] = None
    model_config = {"from_attributes": True}


class FlightListResponse(BaseModel):
    total:   int
    flights: list[FlightResponse]


class ScheduleCreate(BaseModel):
    flight_id:      int
    dep_datetime:   datetime
    arr_datetime:   datetime
    terminal:       Optional[str] = None
    gate:           Optional[str] = None

    @field_validator("arr_datetime")
    @classmethod
    def arr_must_be_after_dep(cls, arr, info):
        dep = info.data.get("dep_datetime")
        if dep and arr <= dep:
            raise ValueError("Arrival datetime must be after departure datetime (BR-007)")
        return arr

    model_config = {"from_attributes": True}


class ScheduleUpdate(BaseModel):
    dep_datetime:   Optional[datetime] = None
    arr_datetime:   Optional[datetime] = None
    actual_dep:     Optional[datetime] = None
    actual_arr:     Optional[datetime] = None
    terminal:       Optional[str]      = None
    gate:           Optional[str]      = None


class ScheduleResponse(BaseModel):
    schedule_id:    int
    flight_id:      int
    dep_datetime:   datetime
    arr_datetime:   datetime
    actual_dep:     Optional[datetime]
    actual_arr:     Optional[datetime]
    terminal:       Optional[str]
    gate:           Optional[str]
    created_at:     datetime
    model_config = {"from_attributes": True}
