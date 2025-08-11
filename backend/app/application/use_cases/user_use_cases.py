from typing import List, Optional
from dataclasses import dataclass

from app.domain.entities import User
from app.domain.repositories import UnitOfWork
from app.domain.value_objects import UserId
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists, ValidationError


@dataclass
class CreateUserCommand:
    username: str
    email: str
    name: str
    is_active: bool = True
    is_superuser: bool = False


@dataclass
class UpdateUserCommand:
    user_id: int
    username: Optional[str] = None
    email: Optional[str] = None
    name: Optional[str] = None
    is_active: Optional[bool] = None


class UserUseCases:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def create_user(self, command: CreateUserCommand) -> User:
        async with self.uow:
            # Check if username already exists
            existing_user = await self.uow.users.get_by_username(command.username)
            if existing_user:
                raise EntityAlreadyExists("User", "username", command.username)
            
            # Check if email already exists
            existing_email = await self.uow.users.get_by_email(command.email)
            if existing_email:
                raise EntityAlreadyExists("User", "email", command.email)
            
            user = User(
                id=None,
                username=command.username,
                email=command.email,
                name=command.name,
                is_active=command.is_active,
                is_superuser=command.is_superuser
            )
            
            created_user = await self.uow.users.create(user)
            await self.uow.commit()
            return created_user
    
    async def get_user_by_id(self, user_id: int) -> User:
        async with self.uow:
            user = await self.uow.users.get_by_id(UserId(user_id))
            if not user:
                raise EntityNotFound("User", str(user_id))
            return user
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        async with self.uow:
            return await self.uow.users.get_by_username(username)
    
    async def update_user(self, command: UpdateUserCommand) -> User:
        async with self.uow:
            user = await self.uow.users.get_by_id(UserId(command.user_id))
            if not user:
                raise EntityNotFound("User", str(command.user_id))
            
            # Check for username conflicts if username is being changed
            if command.username and command.username != user.username:
                existing_user = await self.uow.users.get_by_username(command.username)
                if existing_user:
                    raise EntityAlreadyExists("User", "username", command.username)
                user.username = command.username
            
            # Check for email conflicts if email is being changed
            if command.email and command.email != user.email:
                existing_email = await self.uow.users.get_by_email(command.email)
                if existing_email:
                    raise EntityAlreadyExists("User", "email", command.email)
                user.email = command.email
            
            if command.name is not None:
                user.name = command.name
            if command.is_active is not None:
                user.is_active = command.is_active
            
            updated_user = await self.uow.users.update(user)
            await self.uow.commit()
            return updated_user
    
    async def delete_user(self, user_id: int) -> bool:
        async with self.uow:
            user = await self.uow.users.get_by_id(UserId(user_id))
            if not user:
                raise EntityNotFound("User", str(user_id))
            
            result = await self.uow.users.delete(UserId(user_id))
            await self.uow.commit()
            return result
    
    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        async with self.uow:
            return await self.uow.users.list_all(skip=skip, limit=limit)