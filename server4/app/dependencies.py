"""FastAPI dependency injection."""

from fastapi import Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.database import get_db
from app.utils.auth import get_current_user, get_current_user_optional
from app.utils.rate_limiter import check_rate_limit


async def get_database() -> AsyncIOMotorDatabase:
    return get_db()


async def require_auth(user: dict = Depends(get_current_user)) -> dict:
    return user


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require authenticated user with admin role."""
    role = user.get("role", "")
    set_role = user.get("setuserrole", "")
    if role != "admin" and set_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def optional_auth(
    user: dict | None = Depends(get_current_user_optional),
) -> dict | None:
    return user


async def check_generation_rate_limit(user: dict = Depends(get_current_user)) -> dict:
    is_premium = user.get("role") == "premium" or user.get("setuserrole") == "premium"
    allowed = await check_rate_limit(user["user_id"], is_premium)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
        )
    return user
