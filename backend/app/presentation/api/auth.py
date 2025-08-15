from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr, Field

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_current_active_user
from app.core.rate_limit import auth_rate_limit, api_rate_limit
from app.application.services.auth_service import AuthService, Token, get_auth_service
from app.application.use_cases.user_use_cases import UserUseCases, CreateUserCommand
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.presentation.schemas.user_schemas import UserResponse
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists, ValidationError
from app.domain.entities import User

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    name: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


def get_user_use_cases(db: AsyncSession = Depends(get_db)) -> UserUseCases:
    uow = SQLAlchemyUnitOfWork(db)
    return UserUseCases(uow)


def _user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=user.id.value if user.id else 0,
        username=user.username,
        email=user.email,
        name=user.name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        created_at=user.created_at,
    )


@router.post("/login", response_model=TokenResponse)
@auth_rate_limit()
async def login(
    request: Request,
    login_data: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """Authenticate user and return JWT token"""
    try:
        # Get user by username
        user = await use_cases.get_user_by_username(login_data.username)

        # Verify password
        if not auth_service.verify_password(login_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate scopes based on user permissions
        scopes = ["user:read"]
        if user.is_superuser:
            scopes.extend(
                ["user:admin", "workflow:admin", "workflow:read", "workflow:write"]
            )
        else:
            scopes.extend(["workflow:read", "workflow:write"])

        # Create token
        token = auth_service.create_user_token(
            user_id=user.id.value, username=user.username, scopes=scopes
        )

        return TokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=_user_to_response(user),
        )

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/login/oauth2", response_model=Token)
@auth_rate_limit()
async def login_oauth2(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """OAuth2 compatible login endpoint"""
    try:
        # Get user by username
        user = await use_cases.get_user_by_username(form_data.username)

        # Verify password
        if not auth_service.verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Generate scopes
        scopes = form_data.scopes or ["user:read"]
        if user.is_superuser:
            scopes.extend(
                ["user:admin", "workflow:admin", "workflow:read", "workflow:write"]
            )

        # Create token
        token = auth_service.create_user_token(
            user_id=user.id.value, username=user.username, scopes=scopes
        )

        # Create user response
        user_response = UserResponse(
            id=user.id.value,
            username=user.username,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )

        return TokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=user_response,
        )

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post(
    "/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED
)
@auth_rate_limit()
async def register(
    request: Request,
    register_data: RegisterRequest,
    auth_service: AuthService = Depends(get_auth_service),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """Register new user"""
    try:
        # Validate password strength
        auth_service.validate_password_strength(register_data.password)

        # Hash password
        hashed_password = auth_service.get_password_hash(register_data.password)

        # Create user
        command = CreateUserCommand(
            username=register_data.username,
            email=register_data.email,
            name=register_data.name,
            hashed_password=hashed_password,
        )

        user = await use_cases.create_user(command)

        # Create token for new user
        scopes = ["user:read", "workflow:read", "workflow:write"]
        token = auth_service.create_user_token(
            user_id=user.id.value, username=user.username, scopes=scopes
        )

        return TokenResponse(
            access_token=token.access_token,
            token_type=token.token_type,
            expires_in=token.expires_in,
            user=_user_to_response(user),
        )

    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with {e.field}='{e.value}' already exists",
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return _user_to_response(current_user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    """Change user password"""
    try:
        # Verify current password
        if not auth_service.verify_password(
            password_data.current_password, current_user.hashed_password
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        # Validate new password strength
        auth_service.validate_password_strength(password_data.new_password)

        # Hash new password
        new_hashed_password = auth_service.get_password_hash(password_data.new_password)

        # Update password
        await use_cases.update_user_password(current_user.id.value, new_hashed_password)

        return {"message": "Password changed successfully"}

    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=e.message)


@router.post("/refresh")
async def refresh_token(
    current_user: User = Depends(get_current_active_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Refresh JWT token"""
    # Generate scopes based on user permissions
    scopes = ["user:read"]
    if current_user.is_superuser:
        scopes.extend(
            ["user:admin", "workflow:admin", "workflow:read", "workflow:write"]
        )
    else:
        scopes.extend(["workflow:read", "workflow:write"])

    # Create new token
    token = auth_service.create_user_token(
        user_id=current_user.id.value, username=current_user.username, scopes=scopes
    )

    return TokenResponse(
        access_token=token.access_token,
        token_type=token.token_type,
        expires_in=token.expires_in,
        user=_user_to_response(current_user),
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """Logout user (client should discard token)"""
    return {"message": "Successfully logged out"}


@router.get("/verify-token")
async def verify_token(current_user: User = Depends(get_current_active_user)):
    """Verify token validity"""
    return {"valid": True, "user": _user_to_response(current_user)}
