from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from database import get_db
from models.user import User
from models.api_key import APIKey

security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    return encoded_jwt


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Get the current authenticated user from JWT token or API key.

    Supports two authentication methods:
    1. JWT token (Bearer token from login)
    2. API key (Bearer tt_...)
    """
    token = credentials.credentials

    # Check if it's an API key (starts with 'tt_')
    if token.startswith("tt_"):
        return await authenticate_with_api_key(token, db)

    # Otherwise, treat as JWT token
    return await authenticate_with_jwt(token, db)


async def authenticate_with_jwt(token: str, db: AsyncSession) -> User:
    """Authenticate user with JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id: str = payload.get("sub")

        if user_id is None:
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    await db.commit()

    return user


async def authenticate_with_api_key(key: str, db: AsyncSession) -> User:
    """Authenticate user with API key."""
    key_hash = APIKey.hash_key(key)

    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not api_key.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is expired or revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Get the user
    result = await db.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive user",
        )

    # Increment API key usage
    api_key.increment_usage()
    await db.commit()

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security, auto_error=False),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """
    Get the current user if authenticated, otherwise None.
    Useful for endpoints that work with or without auth.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


def require_scopes(required_scopes: list[str]):
    """
    Dependency to check if the current user/API key has required scopes.

    Usage:
        @router.get("/tracks", dependencies=[Depends(require_scopes(["read:tracks"]))])
    """
    async def check_scopes(
        credentials: HTTPAuthorizationCredentials = Security(security),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        user = await get_current_user(credentials, db)
        token = credentials.credentials

        # If using API key, check scopes
        if token.startswith("tt_"):
            key_hash = APIKey.hash_key(token)
            result = await db.execute(
                select(APIKey).where(APIKey.key_hash == key_hash)
            )
            api_key = result.scalar_one_or_none()

            if not api_key.has_any_scope(required_scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scopes: {required_scopes}",
                )

        return user

    return check_scopes


def require_role(required_role: str):
    """
    Dependency to check if the current user has a specific role.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin"))])
    """
    async def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required role: {required_role}",
            )
        return user

    return check_role