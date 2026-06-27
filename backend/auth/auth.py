# =============================================================
# AeroDesk — Authentication Utilities
# backend/auth/auth.py
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
# Fix: use bcrypt__rounds to suppress bcrypt version warnings
# Fix: handle passlib + bcrypt 4.x compatibility explicitly
# =============================================================

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.
    Passwords are encoded to UTF-8 and safely handled.
    """
    if not password:
        raise ValueError("Password cannot be empty.")
    # bcrypt hard limit is 72 bytes — encode and slice safely
    password_bytes = password.encode("utf-8")[:72]
    return pwd_context.hash(password_bytes.decode("utf-8", errors="ignore"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Applies the same 72-byte truncation used during hashing.
    """
    if not plain_password or not hashed_password:
        return False
    try:
        password_bytes = plain_password.encode("utf-8")[:72]
        return pwd_context.verify(
            password_bytes.decode("utf-8", errors="ignore"),
            hashed_password
        )
    except Exception:
        return False


# =============================================================
# JWT TOKEN UTILITIES
# =============================================================

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a signed JWT access token.
    Payload includes: email (sub), role, staff_id.
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
    Raises HTTP 401 if token is invalid or expired.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# =============================================================
# FASTAPI DEPENDENCIES
# =============================================================

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Staff:
    """
    Extracts and validates the current logged-in staff member
    from the JWT Bearer token.

    Usage in routers:
        current_user: Staff = Depends(get_current_user)
    """
    payload     = decode_token(token)
    email: Optional[str] = payload.get("sub")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload."
        )

    staff = db.query(Staff).filter(Staff.email == email).first()

    if staff is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Staff account not found."
        )

    if not staff.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Contact your administrator."
        )

    return staff


def require_roles(*allowed_roles: StaffRoleEnum):
    """
    FastAPI dependency factory — enforces role-based access control.
    Implements BR-013.

    Returns HTTP 403 with clear role and permission detail
    when access is denied — surfaces as Access Denied screen in UI.

    Usage:
        current_user: Staff = Depends(
            require_roles(
                StaffRoleEnum.Super_Admin,
                StaffRoleEnum.Operations_Manager
            )
        )
    """
    def role_checker(
        current_user: Staff = Depends(get_current_user)
    ) -> Staff:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "message":      "Access Denied",
                    "your_role":    current_user.role.value,
                    "allowed_roles": [r.value for r in allowed_roles],
                    "action":       "Contact your system administrator if you believe this is an error."
                }
            )
        return current_user

    return role_checker
