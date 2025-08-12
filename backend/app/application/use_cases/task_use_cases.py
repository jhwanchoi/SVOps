from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from app.domain.entities import Task, Dataset
from app.domain.repositories import UnitOfWork
from app.domain.value_objects import TaskId, UserId, DatasetId, TaskConfiguration, VideoOutput
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists
from app.shared.types import TaskStatus


@dataclass
class CreateTaskCommand:
    name: str
    description: Optional[str]
    status: TaskStatus
    customer: str
    log_out_path: str
    
    # Build configuration
    branch_name: Optional[str] = None
    commit_id: Optional[str] = None
    build_config: Optional[str] = None
    build_config_customized: bool = False
    build_config_custom_conf: Dict[str, Any] = None
    build_config_custom_ini: Dict[str, Any] = None
    
    # Dataset and output
    dataset_id: Optional[int] = None
    video_out_enabled: bool = False
    video_out_path: str = ""
    
    created_by_id: Optional[int] = None


@dataclass
class UpdateTaskCommand:
    task_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    customer: Optional[str] = None
    log_out_path: Optional[str] = None
    
    # Build configuration updates
    branch_name: Optional[str] = None
    commit_id: Optional[str] = None
    build_config: Optional[str] = None
    build_config_customized: Optional[bool] = None
    build_config_custom_conf: Optional[Dict[str, Any]] = None
    build_config_custom_ini: Optional[Dict[str, Any]] = None
    
    # Dataset and output updates
    dataset_id: Optional[int] = None
    video_out_enabled: Optional[bool] = None
    video_out_path: Optional[str] = None


class TaskUseCases:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def create_task(self, command: CreateTaskCommand) -> Task:
        async with self.uow:
            # Check if task name already exists
            existing_task = await self.uow.tasks.get_by_name(command.name)
            if existing_task:
                raise EntityAlreadyExists("Task", "name", command.name)
            
            # Validate creator exists if provided
            creator_id = None
            if command.created_by_id:
                creator = await self.uow.users.get_by_id(UserId(command.created_by_id))
                if not creator:
                    raise EntityNotFound("User", str(command.created_by_id))
                creator_id = UserId(command.created_by_id)
            
            # Validate dataset exists if provided
            dataset = None
            if command.dataset_id:
                dataset = await self.uow.datasets.get_by_id(DatasetId(command.dataset_id))
                if not dataset:
                    raise EntityNotFound("Dataset", str(command.dataset_id))
            
            # Create configuration
            configuration = TaskConfiguration(
                branch_name=command.branch_name,
                commit_id=command.commit_id,
                build_config=command.build_config,
                is_customized=command.build_config_customized,
                custom_conf=command.build_config_custom_conf or {},
                custom_ini=command.build_config_custom_ini or {}
            )
            
            # Create video output configuration
            video_output = VideoOutput(
                enabled=command.video_out_enabled,
                path=command.video_out_path
            )
            
            task = Task(
                id=None,
                name=command.name,
                description=command.description,
                status=command.status,
                customer=command.customer,
                configuration=configuration,
                dataset=dataset,
                log_out_path=command.log_out_path,
                video_output=video_output,
                created_by=creator_id
            )
            
            created_task = await self.uow.tasks.create(task)
            await self.uow.commit()
            return created_task
    
    async def get_task_by_id(self, task_id: int) -> Task:
        async with self.uow:
            task = await self.uow.tasks.get_by_id(TaskId(task_id))
            if not task:
                raise EntityNotFound("Task", str(task_id))
            return task
    
    async def get_task_by_name(self, name: str) -> Optional[Task]:
        async with self.uow:
            return await self.uow.tasks.get_by_name(name)
    
    async def update_task(self, command: UpdateTaskCommand) -> Task:
        async with self.uow:
            task = await self.uow.tasks.get_by_id(TaskId(command.task_id))
            if not task:
                raise EntityNotFound("Task", str(command.task_id))
            
            # Check for name conflicts if name is being changed
            if command.name and command.name != task.name:
                existing_task = await self.uow.tasks.get_by_name(command.name)
                if existing_task:
                    raise EntityAlreadyExists("Task", "name", command.name)
                task.name = command.name
            
            # Update basic fields
            if command.description is not None:
                task.description = command.description
            if command.status:
                task.update_status(command.status)
            if command.customer:
                task.customer = command.customer
            if command.log_out_path:
                task.log_out_path = command.log_out_path
            
            # Update build configuration
            if any([command.branch_name is not None, command.commit_id is not None, 
                   command.build_config is not None, command.build_config_customized is not None,
                   command.build_config_custom_conf is not None, command.build_config_custom_ini is not None]):
                
                new_config = TaskConfiguration(
                    branch_name=command.branch_name if command.branch_name is not None else task.configuration.branch_name,
                    commit_id=command.commit_id if command.commit_id is not None else task.configuration.commit_id,
                    build_config=command.build_config if command.build_config is not None else task.configuration.build_config,
                    is_customized=command.build_config_customized if command.build_config_customized is not None else task.configuration.is_customized,
                    custom_conf=command.build_config_custom_conf if command.build_config_custom_conf is not None else task.configuration.custom_conf,
                    custom_ini=command.build_config_custom_ini if command.build_config_custom_ini is not None else task.configuration.custom_ini
                )
                task.configuration = new_config
            
            # Update dataset if provided
            if command.dataset_id is not None:
                if command.dataset_id == 0:  # Remove dataset
                    task.dataset = None
                else:
                    dataset = await self.uow.datasets.get_by_id(DatasetId(command.dataset_id))
                    if not dataset:
                        raise EntityNotFound("Dataset", str(command.dataset_id))
                    task.assign_dataset(dataset)
            
            # Update video output
            if command.video_out_enabled is not None or command.video_out_path is not None:
                enabled = command.video_out_enabled if command.video_out_enabled is not None else task.video_output.enabled
                path = command.video_out_path if command.video_out_path is not None else task.video_output.path
                
                if enabled:
                    task.enable_video_output(path)
                else:
                    task.disable_video_output()
            
            updated_task = await self.uow.tasks.update(task)
            await self.uow.commit()
            return updated_task
    
    async def delete_task(self, task_id: int) -> bool:
        async with self.uow:
            task = await self.uow.tasks.get_by_id(TaskId(task_id))
            if not task:
                raise EntityNotFound("Task", str(task_id))
            
            result = await self.uow.tasks.delete(TaskId(task_id))
            await self.uow.commit()
            return result
    
    async def list_tasks(self, skip: int = 0, limit: int = 100) -> List[Task]:
        async with self.uow:
            return await self.uow.tasks.list_all(skip=skip, limit=limit)
    
    async def update_task_status(self, task_id: int, new_status: TaskStatus) -> Task:
        """Update task status"""
        async with self.uow:
            task = await self.uow.tasks.get_by_id(TaskId(task_id))
            if not task:
                raise EntityNotFound("Task", str(task_id))
            
            task.update_status(new_status)
            updated_task = await self.uow.tasks.update(task)
            await self.uow.commit()
            return updated_task
    
    async def list_tasks_by_status(self, status: TaskStatus, skip: int = 0, limit: int = 100) -> List[Task]:
        async with self.uow:
            return await self.uow.tasks.list_by_status(status, skip=skip, limit=limit)
    
    async def list_tasks_by_customer(self, customer: str, skip: int = 0, limit: int = 100) -> List[Task]:
        async with self.uow:
            return await self.uow.tasks.list_by_customer(customer, skip=skip, limit=limit)
    
    async def list_tasks_by_creator(self, creator_id: int, skip: int = 0, limit: int = 100) -> List[Task]:
        async with self.uow:
            return await self.uow.tasks.list_by_creator(UserId(creator_id), skip=skip, limit=limit)
    
    async def list_tasks_by_dataset(self, dataset_id: int, skip: int = 0, limit: int = 100) -> List[Task]:
        async with self.uow:
            return await self.uow.tasks.list_by_dataset(DatasetId(dataset_id), skip=skip, limit=limit)