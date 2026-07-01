# =============================================================
# AeroDesk — Auth Router
# backend/routers/auth_router.py
# =============================================================
# Endpoints:
#   POST /auth/login  — authenticate staff, return JWT token
#   GET  /auth/me     — return current logged-in staff profile
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Staff
from backend.auth.auth import (
    verify_password,
    create_access_token,
    get_current_user
)
from backend.schemas.auth_schemas import LoginRequest, TokenResponse

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate a staff member with email and password.
    Returns a JWT access token and staff profile on success.
    Returns HTTP 401 if credentials are invalid or account is inactive.
    """
    # Find staff by email
    staff = db.query(Staff).filter(Staff.email == payload.email).first()

    # Validate credentials
    if not staff or not verify_password(payload.password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account is active
    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your administrator.",
        )

    # Create JWT token
    access_token = create_access_token(data={
        "sub":      staff.email,
        "role":     staff.role.value,
        "staff_id": staff.staff_id,
    })

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        staff_id=staff.staff_id,
        full_name=staff.full_name,
        email=staff.email,
        role=staff.role,
    )

@router.post("/token", response_model=TokenResponse)
def login_for_swagger(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    OAuth2 login endpoint for Swagger Authorize.
    Accepts form data instead of JSON.
    """

    # Find staff by email (Swagger sends email in the username field)
    staff = db.query(Staff).filter(
        Staff.email == form_data.username
    ).first()

    # Validate credentials
    if not staff or not verify_password(
        form_data.password,
        staff.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check account is active
    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your administrator.",
        )

    # Create JWT token
    access_token = create_access_token(
        data={
            "sub": staff.email,
            "role": staff.role.value,
            "staff_id": staff.staff_id,
        }
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        staff_id=staff.staff_id,
        full_name=staff.full_name,
        email=staff.email,
        role=staff.role,
    )

@router.get("/me", response_model=dict)
def get_me(current_user: Staff = Depends(get_current_user)):
    """
    Returns the currently authenticated staff member's profile.
    Useful for the frontend to restore session state on page refresh.
    """
    return {
        "staff_id":  current_user.staff_id,
        "full_name": current_user.full_name,
        "email":     current_user.email,
        "role":      current_user.role.value,
        "is_active": current_user.is_active,
    }
