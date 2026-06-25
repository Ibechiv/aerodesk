# =============================================================
# AeroDesk — Staff Router
# backend/routers/staff_router.py
# =============================================================
# Access: Super_Admin only (except GET /me which is open)
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Staff, StaffRoleEnum
from backend.auth.auth import require_roles, hash_password
from backend.schemas.staff_schemas import (
    StaffCreate, StaffUpdate,
    StaffResponse, StaffListResponse
)

router = APIRouter()


@router.post("/", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload:        StaffCreate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(StaffRoleEnum.Super_Admin))
):
    existing = db.query(Staff).filter(Staff.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Staff with email '{payload.email}' already exists."
        )
    staff = Staff(
        full_name=payload.full_name,
        email=payload.email,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.get("/", response_model=StaffListResponse)
def list_staff(
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(StaffRoleEnum.Super_Admin))
):
    staff_list = db.query(Staff).order_by(Staff.full_name).all()
    return StaffListResponse(total=len(staff_list), staff=staff_list)


@router.get("/{staff_id}", response_model=StaffResponse)
def get_staff(
    staff_id:       int,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(StaffRoleEnum.Super_Admin))
):
    staff = db.query(Staff).filter(Staff.staff_id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail=f"Staff {staff_id} not found.")
    return staff


@router.put("/{staff_id}", response_model=StaffResponse)
def update_staff(
    staff_id:       int,
    payload:        StaffUpdate,
    db:             Session = Depends(get_db),
    current_user:   Staff   = Depends(require_roles(StaffRoleEnum.Super_Admin))
):
    staff = db.query(Staff).filter(Staff.staff_id == staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail=f"Staff {staff_id} not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(staff, field, value)
    db.commit()
    db.refresh(staff)
    return staff
