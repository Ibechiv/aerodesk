# =============================================================
# AeroDesk — Staff Schemas
# backend/schemas/staff_schemas.py
# =============================================================

from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional
from backend.models.models import StaffRoleEnum


class StaffCreate(BaseModel):
    full_name:  str
    email:      EmailStr
    role:       StaffRoleEnum
    password:   str

    model_config = {"from_attributes": True}


class StaffUpdate(BaseModel):
    full_name:  Optional[str]           = None
    role:       Optional[StaffRoleEnum] = None
    is_active:  Optional[bool]          = None


class StaffResponse(BaseModel):
    staff_id:   int
    full_name:  str
    email:      str
    role:       StaffRoleEnum
    is_active:  bool
    created_at: datetime

    model_config = {"from_attributes": True}


class StaffListResponse(BaseModel):
    total:  int
    staff:  list[StaffResponse]
