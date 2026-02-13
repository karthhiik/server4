from jose import jwt, JWTError
from fastapi import HTTPException, WebSocket, status, Depends
from fastapi.security import OAuth2PasswordBearer
from app.core.config import get_settings

settings = get_settings()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

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

async def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    FastAPI Dependency to get current user ID from Authorization header.
    """
    return get_current_user_id_from_token(token)
