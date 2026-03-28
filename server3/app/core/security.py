from http.cookies import SimpleCookie

from fastapi import HTTPException, Request, WebSocket, status
from jose import JWTError, jwt

from app.core.config import get_settings

settings = get_settings()


def _extract_bearer_token(auth_header: str | None) -> str | None:
    if not auth_header:
        return None

    parts = auth_header.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1].strip() or None


def get_request_token(request: Request) -> str | None:
    header_token = _extract_bearer_token(request.headers.get("Authorization"))
    if header_token:
        return header_token

    cookie_token = request.cookies.get(settings.AUTH_COOKIE_NAME, "").strip()
    return cookie_token or None


def get_websocket_token(websocket: WebSocket, query_token: str | None = None) -> str | None:
    if query_token and query_token.strip():
        return query_token.strip()

    cookie_header = websocket.headers.get("cookie")
    if not cookie_header:
        return None

    cookie = SimpleCookie()
    cookie.load(cookie_header)
    morsel = cookie.get(settings.AUTH_COOKIE_NAME)
    if not morsel:
        return None
    return morsel.value.strip() or None


def get_current_user_id_from_token(token: str) -> str:
    """
    Decodes the JWT token to get the user ID.
    Supports both 'sub' and 'user_id' claims depending on how Server 2 issues tokens.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str = payload.get("sub") or payload.get("user_id")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token claims")
        return str(user_id)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials")


async def get_authenticated_user_id_from_token(token: str) -> str:
    user_id = get_current_user_id_from_token(token)

    from app.db.mongo import get_community_db

    community_db = await get_community_db()
    if community_db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="User database unavailable",
        )

    user = await community_db.users.find_one({"user_id": user_id}, {"jwt_token": 1})
    if not user or user.get("jwt_token") != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is no longer active",
        )

    return str(user_id)


async def get_current_user(request: Request) -> str:
    """
    FastAPI dependency to get current user ID from Authorization header or auth cookie.
    """
    token = get_request_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
        )
    return await get_authenticated_user_id_from_token(token)
