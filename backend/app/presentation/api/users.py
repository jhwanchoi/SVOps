from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.use_cases.user_use_cases import (
    UserUseCases,
    CreateUserCommand,
    UpdateUserCommand,
)
from app.application.services.auth_service import get_auth_service, AuthService
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.presentation.schemas.user_schemas import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserList,
)
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists

router = APIRouter(prefix="/users", tags=["users"])


def get_user_use_cases(db: AsyncSession = Depends(get_db)) -> UserUseCases:
    uow = SQLAlchemyUnitOfWork(db)
    return UserUseCases(uow)


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    use_cases: UserUseCases = Depends(get_user_use_cases),
    auth_service: AuthService = Depends(get_auth_service),
):
    try:
        # Hash the password using auth service
        hashed_password = auth_service.get_password_hash(user_data.password)

        command = CreateUserCommand(
            username=user_data.username,
            email=user_data.email,
            name=user_data.name,
            hashed_password=hashed_password,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser,
        )
        user = await use_cases.create_user(command)
        return UserResponse(
            id=user.id.value,
            username=user.username,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with {e.field}='{e.value}' already exists",
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, use_cases: UserUseCases = Depends(get_user_use_cases)):
    try:
        user = await use_cases.get_user_by_id(user_id)
        return UserResponse(
            id=user.id.value,
            username=user.username,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    try:
        command = UpdateUserCommand(
            user_id=user_id,
            username=user_data.username,
            email=user_data.email,
            name=user_data.name,
            is_active=user_data.is_active,
        )
        user = await use_cases.update_user(command)
        return UserResponse(
            id=user.id.value,
            username=user.username,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with {e.field}='{e.value}' already exists",
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, use_cases: UserUseCases = Depends(get_user_use_cases)
):
    try:
        await use_cases.delete_user(user_id)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )


@router.get("/", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    use_cases: UserUseCases = Depends(get_user_use_cases),
):
    users = await use_cases.list_users(skip=skip, limit=limit)
    return [
        UserResponse(
            id=user.id.value,
            username=user.username,
            email=user.email,
            name=user.name,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            created_at=user.created_at,
        )
        for user in users
    ]
