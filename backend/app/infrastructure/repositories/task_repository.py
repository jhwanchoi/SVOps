from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.domain.entities import Task
from app.domain.repositories import TaskRepository
from app.domain.value_objects import (
    TaskId,
    UserId,
    DatasetId,
    TaskConfiguration,
    VideoOutput,
)
from app.infrastructure.database.models import TaskModel, DatasetModel
from app.shared.exceptions import EntityNotFound
from app.shared.types import TaskStatus


class SQLAlchemyTaskRepository(TaskRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: TaskModel) -> Task:
        configuration = TaskConfiguration(
            branch_name=model.branch_name,
            commit_id=model.commit_id,
            build_config=model.build_config,
            is_customized=model.build_config_customized,
            custom_conf=model.build_config_custom_conf,
            custom_ini=model.build_config_custom_ini,
        )

        video_output = VideoOutput(
            enabled=model.video_out_enabled, path=model.video_out_path
        )

        dataset = None
        if model.dataset:
            from app.infrastructure.repositories.dataset_repository import (
                SQLAlchemyDatasetRepository,
            )

            dataset_repo = SQLAlchemyDatasetRepository(self.session)
            dataset = dataset_repo._to_domain(model.dataset)

        return Task(
            id=TaskId(model.id) if model.id else None,
            name=model.name,
            description=model.description,
            status=TaskStatus(model.status),
            customer=model.customer,
            configuration=configuration,
            dataset=dataset,
            log_out_path=model.log_out_path,
            video_output=video_output,
            created_at=model.created_at,
            created_by=UserId(model.created_by_id) if model.created_by_id else None,
        )

    def _to_model(self, domain: Task) -> TaskModel:
        model = TaskModel(
            name=domain.name,
            description=domain.description,
            status=domain.status.value,
            customer=domain.customer,
            branch_name=domain.configuration.branch_name,
            commit_id=domain.configuration.commit_id,
            build_config=domain.configuration.build_config,
            build_config_customized=domain.configuration.is_customized,
            build_config_custom_conf=domain.configuration.custom_conf,
            build_config_custom_ini=domain.configuration.custom_ini,
            dataset_id=(
                domain.dataset.id.value
                if domain.dataset and domain.dataset.id
                else None
            ),
            log_out_path=domain.log_out_path,
            video_out_enabled=domain.video_output.enabled,
            video_out_path=domain.video_output.path,
            created_by_id=domain.created_by.value if domain.created_by else None,
        )
        if domain.id:
            model.id = domain.id.value
        return model

    async def create(self, task: Task) -> Task:
        model = self._to_model(task)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model, ["dataset"])
        return self._to_domain(model)

    async def get_by_id(self, task_id: TaskId) -> Optional[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.id == task_id.value)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Optional[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.name == name)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .offset(skip)
            .limit(limit)
            .order_by(TaskModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_status(
        self, status: TaskStatus, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.status == status.value)
            .offset(skip)
            .limit(limit)
            .order_by(TaskModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_customer(
        self, customer: str, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.customer == customer)
            .offset(skip)
            .limit(limit)
            .order_by(TaskModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_creator(
        self, creator_id: UserId, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.created_by_id == creator_id.value)
            .offset(skip)
            .limit(limit)
            .order_by(TaskModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_dataset(
        self, dataset_id: DatasetId, skip: int = 0, limit: int = 100
    ) -> List[Task]:
        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.dataset_id == dataset_id.value)
            .offset(skip)
            .limit(limit)
            .order_by(TaskModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def update(self, task: Task) -> Task:
        if not task.id:
            raise ValueError("Cannot update task without ID")

        result = await self.session.execute(
            select(TaskModel)
            .options(selectinload(TaskModel.dataset))
            .where(TaskModel.id == task.id.value)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise EntityNotFound("Task", str(task.id.value))

        model.name = task.name
        model.description = task.description
        model.status = task.status.value
        model.customer = task.customer
        model.branch_name = task.configuration.branch_name
        model.commit_id = task.configuration.commit_id
        model.build_config = task.configuration.build_config
        model.build_config_customized = task.configuration.is_customized
        model.build_config_custom_conf = task.configuration.custom_conf
        model.build_config_custom_ini = task.configuration.custom_ini
        model.dataset_id = (
            task.dataset.id.value if task.dataset and task.dataset.id else None
        )
        model.log_out_path = task.log_out_path
        model.video_out_enabled = task.video_output.enabled
        model.video_out_path = task.video_output.path

        await self.session.flush()
        await self.session.refresh(model, ["dataset"])
        return self._to_domain(model)

    async def delete(self, task_id: TaskId) -> bool:
        result = await self.session.execute(
            select(TaskModel).where(TaskModel.id == task_id.value)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False

        await self.session.delete(model)
        return True
