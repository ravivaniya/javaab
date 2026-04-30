import secrets
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

from app.config import get_settings, Settings
from app.repositories.cosmos_repo import CosmosRepo
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory dictionary for mock local development users.
# Seed a teacher account so you can test teacher-only routes locally.
MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "9999999999": {
        "id": "teacher_dev",
        "phone": "9999999999",
        "tier": "pro",
        "role": "teacher",
    },
}

cosmos_repo = CosmosRepo()
referral_service = ReferralService()


class LoginRequest(BaseModel):
    phone: str

class VerifyRequest(BaseModel):
    phone: str
    otp: str

class RegisterRequest(BaseModel):
    phone: str
    name: Optional[str] = None
    class_level: Optional[int] = None
    board: Optional[str] = None
    language: Optional[str] = "en"
    referral_code: Optional[str] = None


def create_jwt(user_id: str, phone: str, tier: str, settings: Settings, role: str = "student") -> str:
    """
    Generate a JWT token for the authenticated user.
    """
    expiration = datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": user_id,
        "phone": phone,
        "tier": tier,
        "role": role,
        "exp": expiration
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_jwt(token: str, settings: Settings) -> dict:
    """
    Verify the provided JWT token.
    Raises HTTPException 401 if invalid.
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _generate_referral_code(phone: str) -> str:
    """Short, mostly-unique referral code derived from phone + random."""
    suffix = secrets.token_hex(3).upper()
    tail = phone[-4:] if len(phone) >= 4 else phone
    return f"JV{tail}{suffix}"


@router.post("/login")
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)):
    """
    Authenticate a user and send an OTP.
    """
    if settings.AUTH_MODE == "mock":
        return {
            "status": "otp_sent",
            "message": "Mock mode: any OTP will be accepted (e.g., 123456)",
        }

    logger.warning(
        "Real auth flow requested but Azure AD B2C is not configured. "
        "Set AZURE_AD_B2C_* env vars and implement the OTP provider integration."
    )
    raise HTTPException(
        status_code=501,
        detail=(
            "Real auth flow not implemented. Configure Azure AD B2C "
            "(or another OTP provider) and set AUTH_MODE != 'mock'."
        ),
    )


@router.post("/verify")
async def verify(body: VerifyRequest, settings: Settings = Depends(get_settings)):
    """
    Verify OTP and return a JWT.
    """
    if settings.AUTH_MODE == "mock":
        if body.otp != settings.MOCK_OTP:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        if body.phone not in MOCK_USERS:
            MOCK_USERS[body.phone] = {
                "id": f"mock_{body.phone}",
                "phone": body.phone,
                "tier": "free",
            }

        user = MOCK_USERS[body.phone]
        # Mirror the mock user into Cosmos so the rest of the API can read it.
        await cosmos_repo.upsert_user(
            {
                "id": user["id"],
                "phone": body.phone,
                "tier": user.get("tier", "free"),
                "monthly_queries_used": 0,
            }
        )
        token = create_jwt(user["id"], user["phone"], user["tier"], settings, role=user.get("role", "student"))
        return {"access_token": token, "token_type": "bearer", "token": token}

    raise HTTPException(
        status_code=501,
        detail="Real OTP verification not implemented (configure Azure AD B2C).",
    )


@router.post("/register")
async def register(body: RegisterRequest, settings: Settings = Depends(get_settings)):
    """
    Register a new student and persist their profile.
    Issues a JWT immediately so the client can call authenticated endpoints.
    """
    if not body.phone or len(body.phone) < 6:
        raise HTTPException(status_code=400, detail="Valid phone number required.")

    user_id = f"user_{body.phone}"
    referral_code = _generate_referral_code(body.phone)
    now = datetime.now(timezone.utc).isoformat()

    user_doc = {
        "id": user_id,
        "phone": body.phone,
        "name": body.name,
        "class_level": body.class_level,
        "board": body.board,
        "language": body.language or "en",
        "tier": "Free",
        "monthly_queries_used": 0,
        "referral_code": referral_code,
        "referred_by": body.referral_code,
        "created_at": now,
    }
    await cosmos_repo.upsert_user(user_doc)

    if body.referral_code:
        try:
            await referral_service.process_referral(body.referral_code, user_id)
        except Exception as e:
            logger.error(f"Referral processing failed (non-fatal): {e}")

    token = create_jwt(user_id, body.phone, "Free", settings)
    return {
        "status": "registered",
        "user_id": user_id,
        "referral_code": referral_code,
        "access_token": token,
        "token_type": "bearer",
    }


@router.get("/profile")
async def get_profile(request: Request):
    """
    Return the authenticated user's profile. Requires a valid JWT
    (the AuthMiddleware will have populated request.state.user_id).
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    user = await cosmos_repo.get_user(user_id)
    return {"user": user}
