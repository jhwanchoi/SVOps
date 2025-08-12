from abc import ABC, abstractmethod
from typing import Optional, List, Protocol

from app.domain.entities import User, Dataset, Task, Workflow, WorkflowRun
from app.domain.value_objects import (
    UserId,
    DatasetId,
    TaskId,
    WorkflowId,
    WorkflowRunId,
)
from app.shared.types import TaskStatus, RecordingType, WorkflowStatus


class UserRepository(ABC):
    @abstractmethod
    async def create(self, user: User) -> User:
        pass

    @abstractmethod
    async def get_by_id(self, user_id: UserId) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        pass

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    async def update(self, user: User) -> User:
        pass

    @abstractmethod
    async def delete(self, user_id: UserId) -> bool:
        pass

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        pass


class DatasetRepository(ABC):
    @abstractmethod
    async def create(self, dataset: Dataset) -> Dataset:
        pass

    @abstractmethod
    async def get_by_id(self, dataset_id: DatasetId) -> Optional[Dataset]:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Dataset]:
        pass

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Dataset]:
        pass

    @abstractmethod
    async def list_by_type(
        self, data_type: RecordingType, skip: int = 0, limit: int = 100
    ) -> List[Dataset]:
        pass

    @abstractmethod
    async def list_by_creator(
        self, creator_id: UserId, skip: int = 0, limit: int = 100
    ) -> List[Dataset]:
        pass

    @abstractmethod
    async def update(self, dataset: Dataset) -> Dataset:
        pass

    @abstractmethod
    async def delete(self, dataset_id: DatasetId) -> bool:
        pass


class TaskRepository(ABC):
    @abstractmethod
    async def create(self, task: Task) -> Task:
        pass

    @abstractmethod
    async def get_by_id(self, task_id: TaskId) -> Optional[Task]:
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Task]:
        pass

    @abstractmethod
    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Task]:
        pass

    @abstractmethod
    async def list_by_status(
        self, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        pass

    @abstractmethod
    async def list_by_customer(
        self, customer: str, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        pass

    @abstractmethod
    async def list_by_creator(
        self, creator_id: UserId, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        pass

    @abstractmethod
    async def list_by_dataset(
        self, dataset_id: DatasetId, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        pass

    @abstractmethod
    async def update(self, task: Task) -> Task:
        pass

    @abstractmethod
    async def delete(self, task_id: TaskId) -> bool:
        pass


class WorkflowRepository(ABC):
    @abstractmethod
    async def create(self, workflow: Workflow) -> Workflow:
        pass

    @abstractmethod
    async def get_by_id(self, workflow_id: WorkflowId) -> Optional[Workflow]:
        pass

    @abstractmethod
    async def get_by_dag_id(self, dag_id: str) -> Optional[Workflow]:
        pass

    @abstractmethod
    async def list_active(self) -> List[Workflow]:
        pass

    @abstractmethod
    async def update(self, workflow: Workflow) -> Workflow:
        pass

    @abstractmethod
    async def delete(self, workflow_id: WorkflowId) -> None:
        pass


class WorkflowRunRepository(ABC):
    @abstractmethod
    async def create(self, workflow_run: WorkflowRun) -> WorkflowRun:
        pass

    @abstractmethod
    async def get_by_id(self, run_id: WorkflowRunId) -> Optional[WorkflowRun]:
        pass

    @abstractmethod
    async def get_by_workflow_id(
        self, workflow_id: WorkflowId, limit: int = 100, skip: int = 0
    ) -> List[WorkflowRun]:
        pass

    @abstractmethod
    async def list_by_status(self, statuses: List[WorkflowStatus]) -> List[WorkflowRun]:
        pass

    @abstractmethod
    async def get_by_task_id(
        self, task_id: int, limit: int = 100, skip: int = 0
    ) -> List[WorkflowRun]:
        pass

    @abstractmethod
    async def update(self, workflow_run: WorkflowRun) -> WorkflowRun:
        pass

    @abstractmethod
    async def delete(self, run_id: WorkflowRunId) -> None:
        pass


class UnitOfWork(Protocol):
    users: UserRepository
    datasets: DatasetRepository
    tasks: TaskRepository
    workflows: WorkflowRepository
    workflow_runs: WorkflowRunRepository

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def commit(self):
        pass

    async def rollback(self):
        pass
