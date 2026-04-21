from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()


@router.post("/profile")
async def update_profile(body: Dict[str, Any]):
    """
    Update the current student's profile.

    Phase 1 keeps auth/profile state client-side, so this endpoint mirrors the
    frontend contract and returns the submitted profile for callers to confirm.
    """
    return {"status": "updated", "profile": body}
