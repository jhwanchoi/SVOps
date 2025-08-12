from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.domain.entities import Workflow, WorkflowRun
from app.domain.value_objects import WorkflowId, WorkflowRunId, UserId
from app.domain.repositories import WorkflowRepository, WorkflowRunRepository
from app.infrastructure.database.models import WorkflowModel, WorkflowRunModel
from app.shared.types import WorkflowStatus


class SQLAlchemyWorkflowRepository(WorkflowRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: WorkflowModel) -> Workflow:
        return Workflow(
            id=WorkflowId(str(model.id)) if model.id else None,
            name=model.name,
            description=model.description,
            dag_id=model.dag_id,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=UserId(model.created_by_id) if model.created_by_id else None,
        )

    def _to_model(self, domain: Workflow) -> WorkflowModel:
        model = WorkflowModel(
            name=domain.name,
            description=domain.description,
            dag_id=domain.dag_id,
            is_active=domain.is_active,
            created_by_id=domain.created_by.value if domain.created_by else None,
        )
        if domain.id:
            model.id = int(domain.id.value)
        return model

    async def create(self, workflow: Workflow) -> Workflow:
        model = self._to_model(workflow)
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def get_by_id(self, workflow_id: WorkflowId) -> Optional[Workflow]:
        stmt = select(WorkflowModel).where(WorkflowModel.id == int(workflow_id.value))
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_dag_id(self, dag_id: str) -> Optional[Workflow]:
        stmt = select(WorkflowModel).where(WorkflowModel.dag_id == dag_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_active(self) -> List[Workflow]:
        stmt = select(WorkflowModel).where(WorkflowModel.is_active == True)
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def update(self, workflow: Workflow) -> Workflow:
        model = self._to_model(workflow)
        stmt = (
            update(WorkflowModel)
            .where(WorkflowModel.id == workflow.id.value)
            .values(
                name=model.name,
                description=model.description,
                is_active=model.is_active,
            )
        )
        await self.session.execute(stmt)
        return workflow

    async def delete(self, workflow_id: WorkflowId) -> None:
        stmt = select(WorkflowModel).where(WorkflowModel.id == workflow_id.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)


class SQLAlchemyWorkflowRunRepository(WorkflowRunRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: WorkflowRunModel) -> WorkflowRun:
        from app.domain.value_objects import WorkflowConfiguration
        from app.shared.types import WorkflowTriggerType

        return WorkflowRun(
            id=WorkflowRunId(model.id),
            workflow_id=WorkflowId(str(model.workflow_id)),
            status=WorkflowStatus(model.status),
            trigger_type=WorkflowTriggerType(model.trigger_type),
            configuration=WorkflowConfiguration(
                task_id=model.configuration.get("task_id"),
                dataset_id=model.configuration.get("dataset_id"),
                parameters=model.configuration.get("parameters", {}),
            ),
            start_date=model.start_date,
            end_date=model.end_date,
            execution_date=model.execution_date,
            triggered_by=(
                UserId(model.triggered_by_id) if model.triggered_by_id else None
            ),
            external_trigger_id=model.external_trigger_id,
            note=model.note,
        )

    def _to_model(self, domain: WorkflowRun) -> WorkflowRunModel:
        model = WorkflowRunModel(
            id=domain.id.value,
            workflow_id=int(domain.workflow_id.value),
            status=domain.status.value,
            trigger_type=domain.trigger_type.value,
            configuration={
                "task_id": domain.configuration.task_id,
                "dataset_id": domain.configuration.dataset_id,
                "parameters": domain.configuration.parameters,
            },
            start_date=domain.start_date,
            end_date=domain.end_date,
            execution_date=domain.execution_date,
            triggered_by_id=domain.triggered_by.value if domain.triggered_by else None,
            external_trigger_id=domain.external_trigger_id,
            note=domain.note,
        )
        return model

    async def create(self, workflow_run: WorkflowRun) -> WorkflowRun:
        model = self._to_model(workflow_run)
        self.session.add(model)
        await self.session.flush()
        return self._to_domain(model)

    async def get_by_id(self, run_id: WorkflowRunId) -> Optional[WorkflowRun]:
        stmt = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_workflow_id(
        self, workflow_id: WorkflowId, limit: int = 100, skip: int = 0
    ) -> List[WorkflowRun]:
        stmt = (
            select(WorkflowRunModel)
            .where(WorkflowRunModel.workflow_id == int(workflow_id.value))
            .offset(skip)
            .limit(limit)
            .order_by(WorkflowRunModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_status(self, statuses: List[WorkflowStatus]) -> List[WorkflowRun]:
        status_values = [status.value for status in statuses]
        stmt = select(WorkflowRunModel).where(
            WorkflowRunModel.status.in_(status_values)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def get_by_task_id(
        self, task_id: int, limit: int = 100, skip: int = 0
    ) -> List[WorkflowRun]:
        """Get workflow runs by task_id from configuration JSON"""
        from sqlalchemy import cast, String

        # Using PostgreSQL JSON query to find workflow runs with specific task_id
        stmt = (
            select(WorkflowRunModel)
            .where(
                cast(WorkflowRunModel.configuration.op("->")("task_id"), String)
                == str(task_id)
            )
            .offset(skip)
            .limit(limit)
            .order_by(WorkflowRunModel.created_at.desc())
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def update(self, workflow_run: WorkflowRun) -> WorkflowRun:
        model = self._to_model(workflow_run)
        stmt = (
            update(WorkflowRunModel)
            .where(WorkflowRunModel.id == workflow_run.id.value)
            .values(
                status=model.status,
                start_date=model.start_date,
                end_date=model.end_date,
                execution_date=model.execution_date,
                note=model.note,
            )
        )
        await self.session.execute(stmt)
        return workflow_run

    async def delete(self, run_id: WorkflowRunId) -> None:
        stmt = select(WorkflowRunModel).where(WorkflowRunModel.id == run_id.value)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.session.delete(model)
