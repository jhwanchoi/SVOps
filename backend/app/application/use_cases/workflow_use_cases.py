from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.domain.entities import Workflow, WorkflowRun
from app.domain.value_objects import WorkflowId, WorkflowRunId, UserId, WorkflowConfiguration
from app.shared.types import WorkflowStatus, WorkflowTriggerType
from app.shared.exceptions import EntityNotFound, ExternalServiceError
from app.application.services.airflow_service import AirflowClient
from app.application.services.event_service import WorkflowEventPublisher
from app.infrastructure.repositories.unit_of_work import UnitOfWork


@dataclass
class TriggerWorkflowCommand:
    workflow_id: str
    triggered_by: Optional[int] = None
    task_id: Optional[int] = None
    dataset_id: Optional[int] = None
    parameters: Dict[str, Any] = None
    note: Optional[str] = None


@dataclass
class CreateWorkflowCommand:
    name: str
    description: Optional[str]
    dag_id: str
    created_by_id: Optional[int] = None


class WorkflowUseCases:
    def __init__(self, uow: UnitOfWork, event_publisher: Optional[WorkflowEventPublisher] = None):
        self.uow = uow
        self.airflow_client = AirflowClient()
        self.event_publisher = event_publisher

    async def create_workflow(self, command: CreateWorkflowCommand) -> Workflow:
        created_by = UserId(command.created_by_id) if command.created_by_id else None
        
        workflow = Workflow(
            id=None,
            name=command.name,
            description=command.description,
            dag_id=command.dag_id,
            created_by=created_by,
            created_at=datetime.now()
        )
        
        async with self.uow:
            workflow = await self.uow.workflows.create(workflow)
            await self.uow.commit()
            
        return workflow

    async def trigger_workflow(self, command: TriggerWorkflowCommand) -> WorkflowRun:
        workflow_id = WorkflowId(str(command.workflow_id))
        triggered_by = UserId(command.triggered_by) if command.triggered_by else None
        
        # Get workflow and task data
        async with self.uow:
            workflow = await self.uow.workflows.get_by_id(workflow_id)
            if not workflow:
                raise EntityNotFound("Workflow", command.workflow_id)
            
            # Get task with full configuration
            task = None
            if command.task_id:
                from app.domain.value_objects import TaskId
                task = await self.uow.tasks.get_by_id(TaskId(command.task_id))
                if not task:
                    raise EntityNotFound("Task", str(command.task_id))
            
            # Get dataset information
            dataset = None
            if command.dataset_id:
                from app.domain.value_objects import DatasetId
                dataset = await self.uow.datasets.get_by_id(DatasetId(command.dataset_id))
                if not dataset:
                    raise EntityNotFound("Dataset", str(command.dataset_id))
        
        # Generate DAG run ID
        run_id = f"api_trigger_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare comprehensive configuration for Airflow
        airflow_conf = {
            "task_id": command.task_id,
            "dataset_id": command.dataset_id,
            "parameters": command.parameters or {},
            "triggered_by": command.triggered_by,
            "note": command.note
        }
        
        # Add task configuration if task exists
        if task:
            airflow_conf["task_config"] = {
                "name": task.name,
                "description": task.description,
                "customer": task.customer,
                "status": task.status.value,
                "log_out_path": task.log_out_path,
                "build_config": {
                    "branch_name": task.configuration.branch_name,
                    "commit_id": task.configuration.commit_id,
                    "build_config": task.configuration.build_config,
                    "is_customized": task.configuration.is_customized,
                    "custom_conf": task.configuration.custom_conf,
                    "custom_ini": task.configuration.custom_ini
                },
                "video_output": {
                    "enabled": task.video_output.enabled,
                    "path": task.video_output.path if task.video_output.enabled else None
                }
            }
        
        # Add dataset configuration if dataset exists
        if dataset:
            airflow_conf["dataset_config"] = {
                "name": dataset.name,
                "description": dataset.description,
                "path": dataset.paths.path,
                "data_type": dataset.data_type.value,
                "gt_path": dataset.paths.gt_path,
                "created_at": dataset.created_at.isoformat() if dataset.created_at else None
            }
        
        try:
            # Trigger DAG in Airflow
            dag_run_response = await self.airflow_client.trigger_dag(
                dag_id=workflow.dag_id,
                dag_run_id=run_id,
                conf=airflow_conf
            )
            
            # Create WorkflowRun entity
            workflow_run = WorkflowRun(
                id=WorkflowRunId(dag_run_response["dag_run_id"]),
                workflow_id=workflow_id,
                status=WorkflowStatus.QUEUED,
                trigger_type=WorkflowTriggerType.API,
                configuration=WorkflowConfiguration(
                    task_id=command.task_id,
                    dataset_id=command.dataset_id,
                    parameters=command.parameters or {}
                ),
                triggered_by=triggered_by,
                external_trigger_id=dag_run_response["dag_run_id"],
                note=command.note,
                execution_date=datetime.fromisoformat(dag_run_response["execution_date"].replace('Z', '+00:00'))
            )
            
            async with self.uow:
                await self.uow.workflow_runs.create(workflow_run)
                await self.uow.commit()
            
            # Publish workflow triggered event
            if self.event_publisher:
                await self.event_publisher.workflow_triggered(
                    workflow_id=workflow.dag_id,
                    run_id=workflow_run.id.value,
                    user_id=command.triggered_by,
                    task_id=command.task_id,
                    dataset_id=command.dataset_id,
                    parameters=command.parameters
                )
                
            return workflow_run
            
        except Exception as e:
            raise ExternalServiceError(f"Failed to trigger workflow: {str(e)}", "airflow")

    async def get_workflow_run_status(self, workflow_id: str, run_id: str) -> WorkflowRun:
        workflow_run_id = WorkflowRunId(run_id)
        
        async with self.uow:
            workflow_run = await self.uow.workflow_runs.get_by_id(workflow_run_id)
            if not workflow_run:
                raise EntityNotFound("WorkflowRun", run_id)
            
            # Get the workflow to retrieve the DAG ID
            workflow = await self.uow.workflows.get_by_id(WorkflowId(workflow_id))
            if not workflow:
                raise EntityNotFound("Workflow", workflow_id)
        
        try:
            # Get status from Airflow using the actual DAG ID
            dag_run_response = await self.airflow_client.get_dag_run_status(
                dag_id=workflow.dag_id,
                dag_run_id=run_id
            )
            
            # Update local status if different
            airflow_status = self._map_airflow_status(dag_run_response["state"])
            if workflow_run.status != airflow_status:
                workflow_run.update_status(airflow_status)
                
                if dag_run_response.get("start_date"):
                    workflow_run.start_date = datetime.fromisoformat(
                        dag_run_response["start_date"].replace('Z', '+00:00')
                    )
                
                if dag_run_response.get("end_date"):
                    workflow_run.end_date = datetime.fromisoformat(
                        dag_run_response["end_date"].replace('Z', '+00:00')
                    )
                
                async with self.uow:
                    await self.uow.workflow_runs.update(workflow_run)
                    await self.uow.commit()
            
            return workflow_run
            
        except Exception as e:
            raise ExternalServiceError(f"Failed to get workflow status: {str(e)}", "airflow")

    async def list_workflow_runs(
        self, 
        workflow_id: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[WorkflowRun]:
        workflow_id_obj = WorkflowId(str(workflow_id))
        
        async with self.uow:
            return await self.uow.workflow_runs.get_by_workflow_id(
                workflow_id=workflow_id_obj,
                limit=limit,
                skip=skip
            )

    async def stop_workflow_run(self, workflow_id: str, run_id: str) -> WorkflowRun:
        try:
            # Stop in Airflow
            await self.airflow_client.patch_dag_run(
                dag_id=workflow_id,
                dag_run_id=run_id,
                state="failed"
            )
            
            # Update local status
            workflow_run_id = WorkflowRunId(run_id)
            async with self.uow:
                workflow_run = await self.uow.workflow_runs.get_by_id(workflow_run_id)
                if workflow_run:
                    workflow_run.update_status(WorkflowStatus.FAILED)
                    await self.uow.workflow_runs.update(workflow_run)
                    await self.uow.commit()
                    
                    # Publish workflow stopped event
                    if self.event_publisher:
                        await self.event_publisher.workflow_stopped(
                            workflow_id=workflow_id,
                            run_id=run_id
                        )
                    
                    return workflow_run
                else:
                    raise EntityNotFound("WorkflowRun", run_id)
                    
        except Exception as e:
            raise ExternalServiceError(f"Failed to stop workflow: {str(e)}", "airflow")

    async def retry_workflow_run(self, workflow_id: str, run_id: str) -> WorkflowRun:
        try:
            # Clear and restart in Airflow
            await self.airflow_client.clear_dag_run(
                dag_id=workflow_id,
                dag_run_id=run_id
            )
            
            # Update local status
            workflow_run_id = WorkflowRunId(run_id)
            async with self.uow:
                workflow_run = await self.uow.workflow_runs.get_by_id(workflow_run_id)
                if workflow_run:
                    workflow_run.update_status(WorkflowStatus.QUEUED)
                    workflow_run.start_date = None
                    workflow_run.end_date = None
                    await self.uow.workflow_runs.update(workflow_run)
                    await self.uow.commit()
                    
                    # Publish workflow retried event
                    if self.event_publisher:
                        await self.event_publisher.workflow_retried(
                            workflow_id=workflow_id,
                            run_id=run_id
                        )
                    
                    return workflow_run
                else:
                    raise EntityNotFound("WorkflowRun", run_id)
                    
        except Exception as e:
            raise ExternalServiceError(f"Failed to retry workflow: {str(e)}", "airflow")

    async def get_or_create_workflow(self, name: str, dag_id: str, description: str = None, created_by_id: int = None) -> Workflow:
        """Get existing workflow by DAG ID or create new one"""
        async with self.uow:
            # Try to find existing workflow by DAG ID
            existing_workflow = await self.uow.workflows.get_by_dag_id(dag_id)
            if existing_workflow:
                return existing_workflow
            
            # Create new workflow
            command = CreateWorkflowCommand(
                name=name,
                description=description,
                dag_id=dag_id,
                created_by_id=created_by_id
            )
            return await self.create_workflow(command)

    def _map_airflow_status(self, airflow_state: str) -> WorkflowStatus:
        mapping = {
            "queued": WorkflowStatus.QUEUED,
            "running": WorkflowStatus.RUNNING,
            "success": WorkflowStatus.SUCCESS,
            "failed": WorkflowStatus.FAILED,
            "up_for_retry": WorkflowStatus.UP_FOR_RETRY,
            "up_for_reschedule": WorkflowStatus.UP_FOR_RESCHEDULE,
            "upstream_failed": WorkflowStatus.UPSTREAM_FAILED,
            "skipped": WorkflowStatus.SKIPPED,
            "removed": WorkflowStatus.REMOVED,
            "scheduled": WorkflowStatus.SCHEDULED
        }
        return mapping.get(airflow_state, WorkflowStatus.QUEUED)