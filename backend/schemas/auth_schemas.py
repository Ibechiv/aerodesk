# =============================================================
# AeroDesk — Auth Schemas
# backend/schemas/auth_schemas.py
# =============================================================

from pydantic import BaseModel, EmailStr
from backend.models.models import StaffRoleEnum


class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token:   str
    token_type:     str = "bearer"
    staff_id:       int
    full_name:      str
    email:          str
    role:           StaffRoleEnum


class TokenData(BaseModel):
    email:  str | None = None
    role:   StaffRoleEnum | None = None
