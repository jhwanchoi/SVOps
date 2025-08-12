from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.domain.repositories import UnitOfWork
from app.infrastructure.repositories.user_repository import SQLAlchemyUserRepository
from app.infrastructure.repositories.dataset_repository import (
    SQLAlchemyDatasetRepository,
)
from app.infrastructure.repositories.task_repository import SQLAlchemyTaskRepository
from app.infrastructure.repositories.workflow_repository import (
    SQLAlchemyWorkflowRepository,
    SQLAlchemyWorkflowRunRepository,
)


class SQLAlchemyUnitOfWork:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._users: Optional[SQLAlchemyUserRepository] = None
        self._datasets: Optional[SQLAlchemyDatasetRepository] = None
        self._tasks: Optional[SQLAlchemyTaskRepository] = None
        self._workflows: Optional[SQLAlchemyWorkflowRepository] = None
        self._workflow_runs: Optional[SQLAlchemyWorkflowRunRepository] = None

    @property
    def users(self) -> SQLAlchemyUserRepository:
        if self._users is None:
            self._users = SQLAlchemyUserRepository(self.session)
        return self._users

    @property
    def datasets(self) -> SQLAlchemyDatasetRepository:
        if self._datasets is None:
            self._datasets = SQLAlchemyDatasetRepository(self.session)
        return self._datasets

    @property
    def tasks(self) -> SQLAlchemyTaskRepository:
        if self._tasks is None:
            self._tasks = SQLAlchemyTaskRepository(self.session)
        return self._tasks

    @property
    def workflows(self) -> SQLAlchemyWorkflowRepository:
        if self._workflows is None:
            self._workflows = SQLAlchemyWorkflowRepository(self.session)
        return self._workflows

    @property
    def workflow_runs(self) -> SQLAlchemyWorkflowRunRepository:
        if self._workflow_runs is None:
            self._workflow_runs = SQLAlchemyWorkflowRunRepository(self.session)
        return self._workflow_runs

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

    async def commit(self):
        await self.session.commit()

    async def rollback(self):
        await self.session.rollback()
