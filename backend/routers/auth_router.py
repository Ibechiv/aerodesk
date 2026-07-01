# =============================================================
# AeroDesk — Auth Router
# backend/routers/auth_router.py
# =============================================================
# Endpoints:
#   POST /auth/login  — authenticate staff, return JWT token
#   GET  /auth/me     — return current logged-in staff profile
# =============================================================

from fastapi import APIRouter, Depends, HTTPException, Request, status
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


def _build_token_response(staff: Staff) -> TokenResponse:
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


def _authenticate_staff(email: str, password: str, db: Session) -> Staff:
    staff = db.query(Staff).filter(Staff.email == email).first()

    if not staff or not verify_password(password, staff.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your administrator.",
        )

    return staff


@router.post("/login", response_model=TokenResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    """
    Authenticate a staff member with email and password.
    Supports both JSON payloads and Swagger-style form data.
    """
    content_type = request.headers.get("content-type", "").lower()

    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")
    else:
        payload = await request.json()
        email = payload.get("email")
        password = payload.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Both email and password are required.",
        )

    staff = _authenticate_staff(email, password, db)
    return _build_token_response(staff)

@router.post("/token", response_model=TokenResponse)
async def login_for_swagger(request: Request, db: Session = Depends(get_db)):
    """
    Compatibility endpoint for OAuth2 clients that submit form data.
    """
    return await login(request, db)

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
