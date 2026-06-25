# =============================================================
# AeroDesk — Aircraft Schemas
# backend/schemas/aircraft_schemas.py
# =============================================================

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from backend.models.models import AircraftStatusEnum


class AircraftCreate(BaseModel):
    registration_no:    str
    model:              str
    seat_capacity:      int
    status:             AircraftStatusEnum = AircraftStatusEnum.Active

    model_config = {"from_attributes": True}


class AircraftUpdate(BaseModel):
    model:          Optional[str]                   = None
    seat_capacity:  Optional[int]                   = None
    status:         Optional[AircraftStatusEnum]    = None


class AircraftResponse(BaseModel):
    aircraft_id:        int
    registration_no:    str
    model:              str
    seat_capacity:      int
    status:             AircraftStatusEnum
    created_at:         datetime

    model_config = {"from_attributes": True}


class AircraftListResponse(BaseModel):
    total:      int
    aircraft:   list[AircraftResponse]
