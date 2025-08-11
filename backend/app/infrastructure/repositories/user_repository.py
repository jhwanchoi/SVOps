from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.entities import User
from app.domain.repositories import UserRepository
from app.domain.value_objects import UserId
from app.infrastructure.database.models import UserModel
from app.shared.exceptions import EntityNotFound


class SQLAlchemyUserRepository(UserRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_domain(self, model: UserModel) -> User:
        return User(
            id=UserId(model.id) if model.id else None,
            username=model.username,
            email=model.email,
            name=model.name,
            is_active=model.is_active,
            is_superuser=model.is_superuser,
            created_at=model.created_at
        )
    
    def _to_model(self, domain: User) -> UserModel:
        model = UserModel(
            username=domain.username,
            email=domain.email,
            name=domain.name,
            is_active=domain.is_active,
            is_superuser=domain.is_superuser
        )
        if domain.id:
            model.id = domain.id.value
        return model
    
    async def create(self, user: User) -> User:
        model = self._to_model(user)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id.value)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.username == username)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
    
    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(UserModel).where(UserModel.email == email)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None
    
    async def update(self, user: User) -> User:
        if not user.id:
            raise ValueError("Cannot update user without ID")
        
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user.id.value)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise EntityNotFound("User", str(user.id.value))
        
        model.username = user.username
        model.email = user.email
        model.name = user.name
        model.is_active = user.is_active
        model.is_superuser = user.is_superuser
        
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)
    
    async def delete(self, user_id: UserId) -> bool:
        result = await self.session.execute(
            select(UserModel).where(UserModel.id == user_id.value)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False
        
        await self.session.delete(model)
        return True
    
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        result = await self.session.execute(
            select(UserModel)
            .offset(skip)
            .limit(limit)
            .order_by(UserModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]