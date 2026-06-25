# =============================================================
# AeroDesk — Airport Schemas
# backend/schemas/airport_schemas.py
# =============================================================

from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional


class AirportCreate(BaseModel):
    airport_name:   str
    iata_code:      str
    city:           str
    country:        str
    terminals:      int = 1

    @field_validator("iata_code")
    @classmethod
    def iata_must_be_three_letters(cls, v):
        v = v.upper().strip()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("IATA code must be exactly 3 letters e.g. LOS")
        return v

    model_config = {"from_attributes": True}


class AirportUpdate(BaseModel):
    airport_name:   Optional[str]   = None
    city:           Optional[str]   = None
    country:        Optional[str]   = None
    terminals:      Optional[int]   = None
    is_active:      Optional[bool]  = None


class AirportResponse(BaseModel):
    airport_id:     int
    airport_name:   str
    iata_code:      str
    city:           str
    country:        str
    terminals:      int
    is_active:      bool
    created_at:     datetime

    model_config = {"from_attributes": True}


class AirportListResponse(BaseModel):
    total:      int
    airports:   list[AirportResponse]
