from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.services.auth_service import (
    AuthService,
    TokenData,
    get_auth_service,
)
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.domain.entities import User
from app.domain.value_objects import UserId
from app.shared.exceptions import UnauthorizedError, EntityNotFound

# HTTP Bearer token security scheme
security = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenData:
    """Extract and verify JWT token from Authorization header"""
    try:
        token_data = auth_service.verify_token(credentials.credentials)
        return token_data
    except UnauthorizedError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_data: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current user from token"""
    try:
        uow = SQLAlchemyUnitOfWork(db)
        async with uow:
            user = await uow.users.get_by_id(UserId(token_data.user_id))
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Inactive user",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            return user
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user (alias for clarity)"""
    return current_user


async def get_current_superuser(current_user: User = Depends(get_current_user)) -> User:
    """Get current user and verify superuser status"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


class RequireScopes:
    """Dependency class to require specific scopes"""

    def __init__(self, *required_scopes: str):
        self.required_scopes = set(required_scopes)

    def __call__(
        self, token_data: TokenData = Depends(get_current_user_token)
    ) -> TokenData:
        user_scopes = set(token_data.scopes)

        if not self.required_scopes.issubset(user_scopes):
            missing_scopes = self.required_scopes - user_scopes
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scopes: {', '.join(missing_scopes)}",
            )

        return token_data


# Common scope requirements
require_workflow_read = RequireScopes("workflow:read")
require_workflow_write = RequireScopes("workflow:write")
require_workflow_admin = RequireScopes("workflow:admin")
require_user_admin = RequireScopes("user:admin")


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Get current user if token is provided (optional authentication)"""
    if not credentials:
        return None

    try:
        token_data = auth_service.verify_token(credentials.credentials)
        uow = SQLAlchemyUnitOfWork(db)
        async with uow:
            user = await uow.users.get_by_id(UserId(token_data.user_id))
            return user if user and user.is_active else None
    except (UnauthorizedError, EntityNotFound):
        return None


def create_websocket_auth_dependency():
    """Create WebSocket authentication dependency"""

    async def websocket_auth(
        token: Optional[str] = None,
        auth_service: AuthService = Depends(get_auth_service),
        db: AsyncSession = Depends(get_db),
    ) -> Optional[User]:
        """Authenticate WebSocket connection using token parameter"""
        if not token:
            return None

        try:
            token_data = auth_service.verify_token(token)
            uow = SQLAlchemyUnitOfWork(db)
            async with uow:
                user = await uow.users.get_by_id(UserId(token_data.user_id))
                return user if user and user.is_active else None
        except (UnauthorizedError, EntityNotFound):
            return None

    return websocket_auth


websocket_auth = create_websocket_auth_dependency()
