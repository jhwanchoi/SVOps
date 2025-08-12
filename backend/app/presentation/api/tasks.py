import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.application.use_cases.task_use_cases import (
    TaskUseCases,
    CreateTaskCommand,
    UpdateTaskCommand,
)
from app.application.use_cases.workflow_use_cases import (
    WorkflowUseCases,
    TriggerWorkflowCommand,
)
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.presentation.schemas.task_schemas import (
    TaskCreate,
    TaskUpdate,
    TaskResponse,
    TaskConfigurationSchema,
    VideoOutputSchema,
)
from app.presentation.schemas.dataset_schemas import DatasetResponse
from app.presentation.schemas.workflow_schemas import WorkflowRunResponse
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists
from app.shared.types import TaskStatus, WorkflowStatus
from app.core.dependencies import get_current_active_user
from app.domain.entities import User

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Import DAG chain from central location
from app.application.tasks.dag_chain_tasks import DAG_EXECUTION_CHAIN


class TaskExecutionRequest(BaseModel):
    parameters: dict = {}
    note: Optional[str] = None


class TaskExecutionResponse(BaseModel):
    task_id: int
    total_dags: int
    workflow_runs: List[WorkflowRunResponse]
    message: str


def get_task_use_cases(db: AsyncSession = Depends(get_db)) -> TaskUseCases:
    uow = SQLAlchemyUnitOfWork(db)
    return TaskUseCases(uow)


def get_workflow_use_cases(db: AsyncSession = Depends(get_db)) -> WorkflowUseCases:
    from app.application.services.event_service import get_workflow_event_publisher

    uow = SQLAlchemyUnitOfWork(db)
    event_publisher = get_workflow_event_publisher()
    return WorkflowUseCases(uow, event_publisher)


def _task_to_response(task) -> TaskResponse:
    # Dataset 응답 생성
    dataset_response = None
    if task.dataset:
        dataset_response = DatasetResponse(
            id=task.dataset.id.value,
            name=task.dataset.name,
            description=task.dataset.description,
            path=task.dataset.paths.path,
            data_type=task.dataset.data_type,
            gt_path=task.dataset.paths.gt_path,
            created_at=task.dataset.created_at,
            updated_at=task.dataset.updated_at,
            created_by_id=(
                task.dataset.created_by.value if task.dataset.created_by else None
            ),
        )

    return TaskResponse(
        id=task.id.value,
        name=task.name,
        description=task.description,
        status=task.status,
        customer=task.customer,
        log_out_path=task.log_out_path,
        created_at=task.created_at,
        updated_at=task.updated_at if hasattr(task, "updated_at") else None,
        created_by_id=task.created_by.value if task.created_by else None,
        configuration=TaskConfigurationSchema(
            branch_name=task.configuration.branch_name,
            commit_id=task.configuration.commit_id,
            build_config=task.configuration.build_config,
            build_config_customized=task.configuration.is_customized,
            build_config_custom_conf=task.configuration.custom_conf,
            build_config_custom_ini=task.configuration.custom_ini,
        ),
        dataset=dataset_response,
        video_output=VideoOutputSchema(
            enabled=task.video_output.enabled, path=task.video_output.path
        ),
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate, use_cases: TaskUseCases = Depends(get_task_use_cases)
):
    try:
        command = CreateTaskCommand(
            name=task_data.name,
            description=task_data.description,
            status=task_data.status,
            customer=task_data.customer,
            log_out_path=task_data.log_out_path,
            branch_name=task_data.branch_name,
            commit_id=task_data.commit_id,
            build_config=task_data.build_config,
            build_config_customized=task_data.build_config_customized,
            build_config_custom_conf=task_data.build_config_custom_conf,
            build_config_custom_ini=task_data.build_config_custom_ini,
            dataset_id=task_data.dataset_id,
            video_out_enabled=task_data.video_out_enabled,
            video_out_path=task_data.video_out_path,
            created_by_id=task_data.created_by_id,
        )
        task = await use_cases.create_task(command)
        return _task_to_response(task)
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with {e.field}='{e.value}' already exists",
        )
    except EntityNotFound as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.args[0])


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, use_cases: TaskUseCases = Depends(get_task_use_cases)):
    try:
        task = await use_cases.get_task_by_id(task_id)
        return _task_to_response(task)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    try:
        command = UpdateTaskCommand(
            task_id=task_id,
            name=task_data.name,
            description=task_data.description,
            status=task_data.status,
            customer=task_data.customer,
            log_out_path=task_data.log_out_path,
            branch_name=task_data.branch_name,
            commit_id=task_data.commit_id,
            build_config=task_data.build_config,
            build_config_customized=task_data.build_config_customized,
            build_config_custom_conf=task_data.build_config_custom_conf,
            build_config_custom_ini=task_data.build_config_custom_ini,
            dataset_id=task_data.dataset_id,
            video_out_enabled=task_data.video_out_enabled,
            video_out_path=task_data.video_out_path,
        )
        task = await use_cases.update_task(command)
        return _task_to_response(task)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with {e.field}='{e.value}' already exists",
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int, use_cases: TaskUseCases = Depends(get_task_use_cases)
):
    try:
        await use_cases.delete_task(task_id)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    customer: Optional[str] = None,
    creator_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    use_cases: TaskUseCases = Depends(get_task_use_cases),
):
    if status_filter:
        tasks = await use_cases.list_tasks_by_status(
            status_filter, skip=skip, limit=limit
        )
    elif customer:
        tasks = await use_cases.list_tasks_by_customer(customer, skip=skip, limit=limit)
    elif creator_id:
        tasks = await use_cases.list_tasks_by_creator(
            creator_id, skip=skip, limit=limit
        )
    elif dataset_id:
        tasks = await use_cases.list_tasks_by_dataset(
            dataset_id, skip=skip, limit=limit
        )
    else:
        tasks = await use_cases.list_tasks(skip=skip, limit=limit)

    return [_task_to_response(task) for task in tasks]


@router.post(
    "/{task_id}/execute",
    response_model=TaskExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def execute_task(
    task_id: int,
    execution_request: TaskExecutionRequest = TaskExecutionRequest(),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_active_user),
    task_use_cases: TaskUseCases = Depends(get_task_use_cases),
    workflow_use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    """Execute a task through DAG chain execution"""
    try:
        
        # 1. Get and validate task
        task = await task_use_cases.get_task_by_id(task_id)
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found"
            )

        # 2. Update task status to running
        await task_use_cases.update_task_status(task_id, TaskStatus.RUNNING)

        # 3. Create workflows for each DAG if they don't exist
        workflow_runs = []

        # Start with the first DAG
        dag_id = DAG_EXECUTION_CHAIN[0]
        workflow = await workflow_use_cases.get_or_create_workflow(
            name=f"{dag_id.replace('_', ' ').title()}",
            dag_id=dag_id,
            description=f"Auto-created workflow for {dag_id}",
            created_by_id=current_user.id.value,
        )

        # Trigger first DAG
        command = TriggerWorkflowCommand(
            workflow_id=workflow.id.value,
            triggered_by=current_user.id.value,
            task_id=task_id,
            dataset_id=task.dataset.id.value if task and task.dataset else None,
            parameters={
                **execution_request.parameters,
                "dag_index": 0,
                "dag_total": len(DAG_EXECUTION_CHAIN)
            },
            note=f"DAG 1/{len(DAG_EXECUTION_CHAIN)}: {dag_id} - {execution_request.note or 'Task execution'}",
        )

        workflow_run = await workflow_use_cases.trigger_workflow(command)
        workflow_runs.append(workflow_run)

        # Schedule monitoring for DAG chain (if more than 1 DAG)
        if len(DAG_EXECUTION_CHAIN) > 1:
            from app.application.tasks.workflow_tasks import trigger_next_dag_after_completion
            try:
                result = trigger_next_dag_after_completion.delay(
                    current_dag_id=workflow.dag_id,
                    current_run_id=workflow_run.id.value,
                    next_dag_id=DAG_EXECUTION_CHAIN[1],
                    task_id=task_id,
                    triggered_by=current_user.id.value,
                    parameters={
                        **execution_request.parameters,
                        "dag_index": 1,
                        "dag_total": len(DAG_EXECUTION_CHAIN)
                    },
                    note=f"DAG 2/{len(DAG_EXECUTION_CHAIN)}: {DAG_EXECUTION_CHAIN[1]} - {execution_request.note or 'Task execution'}"
                )
                logger.info(f"DAG chaining task scheduled: {result.id}")
            except Exception as e:
                logger.error(f"Failed to schedule next DAG monitoring: {e}")

        # Add placeholders for remaining DAGs
        for i in range(1, len(DAG_EXECUTION_CHAIN)):
            dag_id = DAG_EXECUTION_CHAIN[i]
            workflow = await workflow_use_cases.get_or_create_workflow(
                name=f"{dag_id.replace('_', ' ').title()}",
                dag_id=dag_id,
                description=f"Auto-created workflow for {dag_id}",
                created_by_id=current_user.id.value,
            )
            
            from app.domain.entities import WorkflowRun
            from app.domain.value_objects import WorkflowRunId
            from app.shared.types import WorkflowTriggerType
            
            placeholder_run = WorkflowRun(
                id=WorkflowRunId(f"pending_{dag_id}_{task_id}_{i}"),
                workflow_id=workflow.id,
                status=WorkflowStatus.QUEUED,
                trigger_type=WorkflowTriggerType.API,
                configuration=None,
                triggered_by=None,
                external_trigger_id=None,
                note=f"Pending DAG {i+1}/{len(DAG_EXECUTION_CHAIN)}: {dag_id}",
            )
            workflow_runs.append(placeholder_run)

        return TaskExecutionResponse(
            task_id=task_id,
            total_dags=len(DAG_EXECUTION_CHAIN),
            workflow_runs=[_workflow_run_to_response(run) for run in workflow_runs],
            message=f"Task {task_id} execution started with {len(DAG_EXECUTION_CHAIN)} DAG chain",
        )

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except Exception as e:
        # Revert task status on error
        try:
            await task_use_cases.update_task_status(task_id, TaskStatus.FAILED)
        except:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute task: {str(e)}",
        )


@router.get("/{task_id}/status")
async def get_task_execution_status(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    task_use_cases: TaskUseCases = Depends(get_task_use_cases),
    workflow_use_cases: WorkflowUseCases = Depends(get_workflow_use_cases),
):
    """Get Task execution status including all related WorkflowRuns"""
    try:
        # 1. Get task basic info
        task = await task_use_cases.get_task_by_id(task_id)

        # 2. Get all workflow runs for this task
        from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork

        uow = SQLAlchemyUnitOfWork(db)
        async with uow:
            workflow_runs = await uow.workflow_runs.get_by_task_id(task_id)

            # Convert to response format
            workflow_run_responses = [
                _workflow_run_to_response(run) for run in workflow_runs
            ]

            # Determine overall status - prioritize task status
            if task.status.value in ["completed", "failed"]:
                # If task is completed or failed, use task status as overall status
                overall_status = task.status.value
            elif not workflow_runs:
                overall_status = task.status.value
            else:
                # Check workflow run statuses
                statuses = [run.status.value for run in workflow_runs]
                if "running" in statuses or "queued" in statuses:
                    overall_status = "running"
                elif "failed" in statuses:
                    overall_status = "failed"
                elif all(s == "success" for s in statuses):
                    overall_status = "success"
                else:
                    overall_status = "running"

            return {
                "task_id": task_id,
                "task_status": task.status.value,
                "task_name": task.name,
                "dag_chain": DAG_EXECUTION_CHAIN,
                "workflow_runs": workflow_run_responses,
                "total_workflow_runs": len(workflow_runs),
                "overall_status": overall_status,
            }

    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Task not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task execution status: {str(e)}",
        )


def _workflow_run_to_response(workflow_run) -> WorkflowRunResponse:
    """Convert WorkflowRun to WorkflowRunResponse"""
    # Handle case where configuration might be None
    if workflow_run.configuration:
        config = {
            "task_id": workflow_run.configuration.task_id,
            "dataset_id": workflow_run.configuration.dataset_id,
            "parameters": workflow_run.configuration.parameters,
        }
    else:
        config = {
            "task_id": None,
            "dataset_id": None,
            "parameters": {},
        }
    
    return WorkflowRunResponse(
        id=workflow_run.id.value,
        workflow_id=workflow_run.workflow_id.value,
        status=workflow_run.status,
        trigger_type=workflow_run.trigger_type,
        configuration=config,
        start_date=workflow_run.start_date,
        end_date=workflow_run.end_date,
        execution_date=workflow_run.execution_date,
        triggered_by=(
            workflow_run.triggered_by.value if workflow_run.triggered_by else None
        ),
        external_trigger_id=workflow_run.external_trigger_id,
        note=workflow_run.note,
    )
