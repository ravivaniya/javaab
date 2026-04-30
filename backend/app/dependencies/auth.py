from fastapi import HTTPException, Request


def require_teacher(request: Request) -> None:
    """FastAPI dependency — 403 if caller is not a teacher."""
    role = getattr(request.state, "user_role", "student")
    if role != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
