from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app.repositories.cosmos_repo import CosmosRepo

router = APIRouter()
cosmos_repo = CosmosRepo()


@router.post("/profile")
async def update_profile(request: Request, body: Dict[str, Any]):
    """Persist the student's full profile to Cosmos DB."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    existing = await cosmos_repo.get_user(user_id)
    body.pop("id", None)
    existing.update(body)
    saved = await cosmos_repo.upsert_user(existing)
    return {"status": "updated", "profile": saved}
