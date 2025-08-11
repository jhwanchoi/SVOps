from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.use_cases.task_use_cases import TaskUseCases, CreateTaskCommand, UpdateTaskCommand
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.presentation.schemas.task_schemas import TaskCreate, TaskUpdate, TaskResponse, TaskConfigurationSchema, VideoOutputSchema
from app.presentation.schemas.dataset_schemas import DatasetResponse
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists
from app.shared.types import TaskStatus

router = APIRouter(prefix="/tasks", tags=["tasks"])


def get_task_use_cases(db: AsyncSession = Depends(get_db)) -> TaskUseCases:
    uow = SQLAlchemyUnitOfWork(db)
    return TaskUseCases(uow)


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
            created_by_id=task.dataset.created_by.value if task.dataset.created_by else None
        )
    
    return TaskResponse(
        id=task.id.value,
        name=task.name,
        description=task.description,
        status=task.status,
        customer=task.customer,
        log_out_path=task.log_out_path,
        created_at=task.created_at,
        updated_at=task.updated_at if hasattr(task, 'updated_at') else None,
        created_by_id=task.created_by.value if task.created_by else None,
        configuration=TaskConfigurationSchema(
            branch_name=task.configuration.branch_name,
            commit_id=task.configuration.commit_id,
            build_config=task.configuration.build_config,
            build_config_customized=task.configuration.is_customized,
            build_config_custom_conf=task.configuration.custom_conf,
            build_config_custom_ini=task.configuration.custom_ini
        ),
        dataset=dataset_response,
        video_output=VideoOutputSchema(
            enabled=task.video_output.enabled,
            path=task.video_output.path
        )
    )


@router.post("/", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    use_cases: TaskUseCases = Depends(get_task_use_cases)
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
            created_by_id=task_data.created_by_id
        )
        task = await use_cases.create_task(command)
        return _task_to_response(task)
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with {e.field}='{e.value}' already exists"
        )
    except EntityNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.args[0]
        )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    use_cases: TaskUseCases = Depends(get_task_use_cases)
):
    try:
        task = await use_cases.get_task_by_id(task_id)
        return _task_to_response(task)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    use_cases: TaskUseCases = Depends(get_task_use_cases)
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
            video_out_path=task_data.video_out_path
        )
        task = await use_cases.update_task(command)
        return _task_to_response(task)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Task with {e.field}='{e.value}' already exists"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: int,
    use_cases: TaskUseCases = Depends(get_task_use_cases)
):
    try:
        await use_cases.delete_task(task_id)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found"
        )


@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status_filter: Optional[TaskStatus] = Query(None, alias="status"),
    customer: Optional[str] = None,
    creator_id: Optional[int] = None,
    dataset_id: Optional[int] = None,
    use_cases: TaskUseCases = Depends(get_task_use_cases)
):
    if status_filter:
        tasks = await use_cases.list_tasks_by_status(status_filter, skip=skip, limit=limit)
    elif customer:
        tasks = await use_cases.list_tasks_by_customer(customer, skip=skip, limit=limit)
    elif creator_id:
        tasks = await use_cases.list_tasks_by_creator(creator_id, skip=skip, limit=limit)
    elif dataset_id:
        tasks = await use_cases.list_tasks_by_dataset(dataset_id, skip=skip, limit=limit)
    else:
        tasks = await use_cases.list_tasks(skip=skip, limit=limit)
    
    return [_task_to_response(task) for task in tasks]