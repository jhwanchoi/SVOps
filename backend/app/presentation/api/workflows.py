import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.application.use_cases.workflow_use_cases import (
    WorkflowUseCases,
    TriggerWorkflowCommand,
    CreateWorkflowCommand,
)
from app.application.services.event_service import get_workflow_event_publisher

# Import Celery tasks conditionally to avoid import issues during startup
try:
    from app.application.tasks.workflow_tasks import (
        monitor_workflow_run,
        sync_workflow_tasks,
    )

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    monitor_workflow_run = None
    sync_workflow_tasks = None
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.presentation.schemas.workflow_schemas import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowRunCreate,
    WorkflowRunResponse,
    WorkflowControlRequest,
    WorkflowRunListResponse,
    WorkflowRunDetailResponse,
)
from app.core.dependencies import (
    get_current_active_user,
    require_workflow_read,
    require_workflow_write,
)
from app.domain.entities import User
from app.shared.exceptions import EntityNotFound, ExternalServiceError
from app.shared.types import WorkflowStatus

router = APIRouter(prefix="/workflows", tags=["workflows"])


def get_workflow_use_cases(db: AsyncSession = Depends(get_db)) -> WorkflowUseCases:
    uow = SQLAlchemyUnitOfWork(db)
    event_publisher = get_workflow_event_publisher()
    return WorkflowUseCases(uow, event_publisher)


def _workflow_to_response(workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=workflow.id.value,
        name=workflow.name,
        description=workflow.description,
        dag_id=workflow.dag_id,
        is_active=workflow.is_active,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        created_by_id=workflow.created_by.value if workflow.created_by else None,
    )


def _workflow_run_to_response(workflow_run) -> WorkflowRunResponse:
    return WorkflowRunResponse(
        id=workflow_run.id.value,
        workflow_id=workflow_run.workflow_id.value,
        status=workflow_run.status,
        trigger_type=workflow_run.trigger_type,
        configuration={
            "task_id": workflow_run.configuration.task_id,
            "dataset_id": workflow_run.configuration.dataset_id,
            "parameters": workflow_run.configuration.parameters,
        },
        start_date=workflow_run.start_date,
        end_date=workflow_run.end_date,
        execution_date=workflow_run.execution_date,
        triggered_by=(
            workflow_run.triggered_by.value if workflow_run.triggered_by else None
        ),
        external_trigger_id=workflow_run.external_trigger_id,
        note=workflow_run.note,
    )


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    workflow_data: WorkflowCreate,
    current_user: User = Depends(get_current_active_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
    _: None = Depends(require_workflow_write),
):
    try:
        command = CreateWorkflowCommand(
            name=workflow_data.name,
            description=workflow_data.description,
            dag_id=workflow_data.dag_id,
            created_by_id=current_user.id.value,
        )
        workflow = await use_cases.create_workflow(command)
        return _workflow_to_response(workflow)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/{workflow_id}/runs",
    response_model=WorkflowRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_workflow(
    workflow_id: str,
    trigger_data: WorkflowRunCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
    _: None = Depends(require_workflow_write),
):
    try:
        command = TriggerWorkflowCommand(
            workflow_id=workflow_id,
            triggered_by=current_user.id.value,
            task_id=trigger_data.task_id,
            dataset_id=trigger_data.dataset_id,
            parameters=trigger_data.parameters,
            note=trigger_data.note,
        )

        workflow_run = await use_cases.trigger_workflow(command)

        # Start background tasks for monitoring if Celery is available
        if CELERY_AVAILABLE and monitor_workflow_run and sync_workflow_tasks:
            monitor_workflow_run.delay(workflow_id, workflow_run.id.value)
            sync_workflow_tasks.delay(workflow_id, workflow_run.id.value)
        else:
            logger.warning(
                "Celery tasks not available - background monitoring disabled"
            )

        return _workflow_run_to_response(workflow_run)

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow not found"
        )
    except ExternalServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.get("/{workflow_id}/runs", response_model=WorkflowRunListResponse)
async def list_workflow_runs(
    workflow_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_active_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
    _: None = Depends(require_workflow_read),
):
    try:
        workflow_runs = await use_cases.list_workflow_runs(
            workflow_id=workflow_id, limit=limit, skip=skip
        )

        return WorkflowRunListResponse(
            runs=[_workflow_run_to_response(run) for run in workflow_runs],
            total=len(workflow_runs),  # TODO: implement proper pagination
            page=skip // limit + 1,
            per_page=limit,
            has_next=len(workflow_runs) == limit,
            has_prev=skip > 0,
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{workflow_id}/runs/{run_id}", response_model=WorkflowRunResponse)
async def get_workflow_run(
    workflow_id: str,
    run_id: str,
    current_user: User = Depends(get_current_active_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
    _: None = Depends(require_workflow_read),
):
    try:
        workflow_run = await use_cases.get_workflow_run_status(workflow_id, run_id)
        return _workflow_run_to_response(workflow_run)

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found"
        )
    except ExternalServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


@router.post("/{workflow_id}/runs/{run_id}/control", response_model=WorkflowRunResponse)
async def control_workflow_run(
    workflow_id: str,
    run_id: str,
    control_request: WorkflowControlRequest,
    current_user: User = Depends(get_current_active_user),
    use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
    _: None = Depends(require_workflow_write),
):
    try:
        if control_request.action == "stop":
            workflow_run = await use_cases.stop_workflow_run(workflow_id, run_id)
        elif control_request.action == "retry":
            workflow_run = await use_cases.retry_workflow_run(workflow_id, run_id)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action: {control_request.action}",
            )

        return _workflow_run_to_response(workflow_run)

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Workflow run not found"
        )
    except ExternalServiceError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))


