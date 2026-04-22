from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from jose import jwt, JWTError

from app.config import get_settings, Settings

router = APIRouter()

# In-memory dictionary for mock local development users
MOCK_USERS: Dict[str, Dict[str, Any]] = {}

class LoginRequest(BaseModel):
    phone: str

class VerifyRequest(BaseModel):
    phone: str
    otp: str

def create_jwt(user_id: str, phone: str, tier: str, settings: Settings) -> str:
    """
    Generate a JWT token for the authenticated user.
    """
    expiration = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRY_HOURS)
    payload = {
        "sub": user_id,
        "phone": phone,
        "tier": tier,
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

@router.post("/login")
async def login(body: LoginRequest, settings: Settings = Depends(get_settings)):
    """
    Authenticate a user and send an OTP.
    """
    if settings.AUTH_MODE == "mock":
        # In mock mode, any phone is valid and we pretend OTP is sent
        return {"status": "otp_sent", "message": "Mock mode: any OTP will be accepted (e.g., 123456)"}
    else:
        # TODO: Implement real Azure AD B2C or OTP flow
        return {"status": "error", "message": "Real auth flow not implemented"}

@router.post("/verify")
async def verify(body: VerifyRequest, settings: Settings = Depends(get_settings)):
    """
    Verify OTP and return a JWT.
    """
    if settings.AUTH_MODE == "mock":
        if body.otp != settings.MOCK_OTP:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # Ensure mock user exists
        if body.phone not in MOCK_USERS:
            MOCK_USERS[body.phone] = {
                "id": f"mock_{body.phone}",
                "phone": body.phone,
                "tier": "free"
            }
        
        user = MOCK_USERS[body.phone]
        token = create_jwt(user["id"], user["phone"], user["tier"], settings)
        return {"access_token": token, "token_type": "bearer", "token": token}
    else:
        # TODO: Implement real OTP verification
        raise HTTPException(status_code=501, detail="Real auth flow not implemented")

@router.post("/register")
async def register(body: Dict[str, Any]):
    """
    Register a new student or teacher.
    """
    # TODO: Implement registration logic
    return {"status": "registered"}

@router.get("/profile")
async def get_profile():
    """
    Get the profile of the current authenticated user.
    """
    # TODO: Implement profile retrieval logic
    return {"user": "stub_user"}
