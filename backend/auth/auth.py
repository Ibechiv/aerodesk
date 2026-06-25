# =============================================================
# AeroDesk — Authentication Utilities
# backend/auth/auth.py
# =============================================================
# Handles:
#   - Password hashing and verification (bcrypt via passlib)
#   - JWT token creation and decoding (python-jose)
#   - Current user extraction from token
# =============================================================

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import os

from backend.database import get_db
from backend.models.models import Staff, StaffRoleEnum

load_dotenv()

# =============================================================
# CONFIGURATION
# =============================================================

SECRET_KEY                  = os.getenv("SECRET_KEY", "changethisinsecretkey")
ALGORITHM                   = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 480))

# =============================================================
# PASSWORD HASHING
# Using bcrypt — matches pgcrypto hashing used in seed script
# =============================================================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# =============================================================
# JWT TOKEN UTILITIES
# =============================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    Includes staff_id, email, and role in the payload.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises HTTPException 401 if token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# =============================================================
# DEPENDENCIES
# Used in FastAPI route functions via Depends()
# =============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Staff:
    """
    FastAPI dependency — extracts and validates the current
    logged-in staff member from the JWT token.

    Usage:
        @router.get("/protected")
        def protected(current_user: Staff = Depends(get_current_user)):
            ...
    """
    payload = decode_token(token)
    email: str = payload.get("sub")

    staff = db.query(Staff).filter(Staff.email == email).first()
    if staff is None or not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff account not found or deactivated."
        )
    return staff


def require_roles(*allowed_roles: StaffRoleEnum):
    """
    FastAPI dependency factory — restricts endpoint access
    to specific staff roles. Implements BR-013 RBAC.

    Returns HTTP 403 with role and module info if access is denied.

    Usage:
        @router.post("/flights")
        def create_flight(
            current_user: Staff = Depends(
                require_roles(
                    StaffRoleEnum.Super_Admin,
                    StaffRoleEnum.Operations_Manager
                )
            )
        ):
            ...
    """
    def role_checker(current_user: Staff = Depends(get_current_user)) -> Staff:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message": "Access Denied",
                    "your_role": current_user.role,
                    "allowed_roles": [r.value for r in allowed_roles],
                    "action": "Contact your system administrator if you believe this is an error."
                }
            )
        return current_user
    return role_checker
