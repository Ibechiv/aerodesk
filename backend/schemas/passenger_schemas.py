# =============================================================
# AeroDesk — Passenger Schemas
# backend/schemas/passenger_schemas.py
# =============================================================

from pydantic import BaseModel, EmailStr
from datetime import date, datetime
from typing import Optional


class PassengerCreate(BaseModel):
    full_name:      str
    date_of_birth:  date
    gender:         str
    nationality:    str
    passport_no:    str
    phone:          str
    email:          EmailStr

    model_config = {"from_attributes": True}


class PassengerUpdate(BaseModel):
    full_name:      Optional[str]       = None
    date_of_birth:  Optional[date]      = None
    gender:         Optional[str]       = None
    nationality:    Optional[str]       = None
    phone:          Optional[str]       = None
    email:          Optional[EmailStr]  = None


class PassengerResponse(BaseModel):
    passenger_id:   int
    full_name:      str
    date_of_birth:  date
    gender:         str
    nationality:    str
    passport_no:    str
    phone:          str
    email:          str
    created_at:     datetime

    model_config = {"from_attributes": True}


class PassengerListResponse(BaseModel):
    total:      int
    passengers: list[PassengerResponse]
