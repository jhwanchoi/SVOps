import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Conditional import of Celery
try:
    from celery import Task
    from app.core.celery_app import celery_app, CELERY_AVAILABLE

    if not CELERY_AVAILABLE or not celery_app:
        raise ImportError("Celery not available")
except ImportError:
    # Mock objects if Celery is not available
    Task = object
    celery_app = None
    CELERY_AVAILABLE = False
from app.core.config import settings
from app.application.services.airflow_service import AirflowClient
from app.application.services.event_service import EventService, WorkflowEventPublisher
from app.application.use_cases.workflow_use_cases import WorkflowUseCases
from app.application.tasks.notification_tasks import (
    trigger_workflow_started_notification,
    trigger_workflow_completed_notification,
    trigger_task_failed_notification,
)
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.core.redis import RedisClient
from app.shared.types import WorkflowStatus, TaskStatus
from app.domain.value_objects import WorkflowId, WorkflowRunId

logger = logging.getLogger(__name__)

# Create async database engine for background tasks
async_engine = create_async_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_recycle=300,
)

AsyncSessionLocal = sessionmaker(
    async_engine, class_=AsyncSession, expire_on_commit=False
)


# Only define tasks if Celery is available
if CELERY_AVAILABLE and celery_app:

    class AsyncTask(Task):
        """Base class for async Celery tasks"""

        def __call__(self, *args, **kwargs):
            return asyncio.get_event_loop().run_until_complete(
                self.run_async(*args, **kwargs)
            )

        async def run_async(self, *args, **kwargs):
            raise NotImplementedError

    @celery_app.task(bind=True, base=AsyncTask)
    async def monitor_workflow_run(self, workflow_id: str, run_id: str):
        """Monitor a specific workflow run until completion"""
        return await _monitor_workflow_run_impl(workflow_id, run_id)

    @celery_app.task(bind=True, base=AsyncTask)
    async def monitor_active_workflows(self):
        """Periodic task to monitor all active workflow runs"""
        return await _monitor_active_workflows_impl()

    @celery_app.task(bind=True, base=AsyncTask)
    async def cleanup_completed_workflows(self):
        """Clean up old completed workflow data"""
        return await _cleanup_completed_workflows_impl()

    @celery_app.task(bind=True, base=AsyncTask)
    async def sync_workflow_tasks(self, workflow_id: str, run_id: str):
        """Sync task instances for a workflow run"""
        return await _sync_workflow_tasks_impl(workflow_id, run_id)

else:
    # Mock functions if Celery is not available
    def monitor_workflow_run(*args, **kwargs):
        logger.warning("Celery not available - monitor_workflow_run task skipped")
        return None

    def monitor_active_workflows(*args, **kwargs):
        logger.warning("Celery not available - monitor_active_workflows task skipped")
        return None

    def cleanup_completed_workflows(*args, **kwargs):
        logger.warning(
            "Celery not available - cleanup_completed_workflows task skipped"
        )
        return None

    def sync_workflow_tasks(*args, **kwargs):
        logger.warning("Celery not available - sync_workflow_tasks task skipped")
        return None

    # Add delay method to mock functions
    monitor_workflow_run.delay = monitor_workflow_run
    sync_workflow_tasks.delay = sync_workflow_tasks
    cleanup_completed_workflows.delay = cleanup_completed_workflows


# Implementation functions (work regardless of Celery availability)
async def _monitor_workflow_run_impl(workflow_id: str, run_id: str):
    """Monitor a specific workflow run until completion"""
    logger.info(f"Starting monitoring for workflow run {workflow_id}/{run_id}")

    try:
        airflow_client = AirflowClient()
        redis_client = RedisClient()
        await redis_client.connect()

        event_service = EventService(redis_client)
        event_publisher = WorkflowEventPublisher(event_service)

        max_attempts = 1440  # 12 hours with 30-second intervals
        attempt = 0

        while attempt < max_attempts:
            try:
                # Get status from Airflow
                dag_run_response = await airflow_client.get_dag_run_status(
                    workflow_id, run_id
                )
                airflow_state = dag_run_response.get("state", "unknown")

                # Map Airflow state to our WorkflowStatus
                status = _map_airflow_status(airflow_state)

                # Update database
                await _update_workflow_run_status(workflow_id, run_id, dag_run_response)

                # Cache status in Redis
                status_data = {
                    "status": status.value,
                    "state": airflow_state,
                    "start_date": dag_run_response.get("start_date"),
                    "end_date": dag_run_response.get("end_date"),
                    "execution_date": dag_run_response.get("execution_date"),
                    "last_updated": datetime.now().isoformat(),
                }
                await event_service.cache_workflow_status(
                    workflow_id, run_id, status_data
                )

                # Publish status update events and trigger notifications
                if airflow_state == "running":
                    await event_publisher.workflow_started(
                        workflow_id, run_id, **status_data
                    )
                    # Trigger notification
                    trigger_workflow_started_notification(workflow_id, run_id)

                elif airflow_state == "success":
                    await event_publisher.workflow_completed(
                        workflow_id, run_id, success=True, **status_data
                    )
                    # Trigger notification
                    trigger_workflow_completed_notification(
                        workflow_id, run_id, success=True
                    )
                    break

                elif airflow_state == "failed":
                    await event_publisher.workflow_completed(
                        workflow_id, run_id, success=False, **status_data
                    )
                    # Trigger notification
                    trigger_workflow_completed_notification(
                        workflow_id, run_id, success=False
                    )
                    break

                # Check if workflow is in terminal state
                if status in [
                    WorkflowStatus.SUCCESS,
                    WorkflowStatus.FAILED,
                    WorkflowStatus.REMOVED,
                ]:
                    logger.info(
                        f"Workflow run {workflow_id}/{run_id} reached terminal state: {status}"
                    )
                    break

                # Wait before next check
                await asyncio.sleep(30)
                attempt += 1

            except Exception as e:
                logger.error(
                    f"Error monitoring workflow run {workflow_id}/{run_id}: {e}"
                )
                await asyncio.sleep(60)  # Wait longer on error
                attempt += 1

        await redis_client.disconnect()
        logger.info(f"Finished monitoring workflow run {workflow_id}/{run_id}")

    except Exception as e:
        logger.error(f"Failed to monitor workflow run {workflow_id}/{run_id}: {e}")
        raise


async def _monitor_active_workflows_impl():
    """Periodic task to monitor all active workflow runs"""
    logger.info("Starting periodic monitoring of active workflows")

    try:
        async with AsyncSessionLocal() as db:
            uow = SQLAlchemyUnitOfWork(db)
            async with uow:
                # Get all active workflow runs
                active_runs = await uow.workflow_runs.list_by_status(
                    [
                        WorkflowStatus.QUEUED,
                        WorkflowStatus.RUNNING,
                        WorkflowStatus.UP_FOR_RETRY,
                        WorkflowStatus.UP_FOR_RESCHEDULE,
                        WorkflowStatus.SCHEDULED,
                    ]
                )

                logger.info(f"Found {len(active_runs)} active workflow runs")

                # Trigger individual monitoring tasks
                for workflow_run in active_runs:
                    monitor_workflow_run.delay(
                        workflow_run.workflow_id.value, workflow_run.id.value
                    )

    except Exception as e:
        logger.error(f"Error in periodic workflow monitoring: {e}")
        raise


async def _cleanup_completed_workflows_impl():
    """Clean up old completed workflow data"""
    logger.info("Starting cleanup of completed workflows")

    try:
        redis_client = RedisClient()
        await redis_client.connect()

        # Clean up workflow status cache for completed runs older than 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)

        async with AsyncSessionLocal() as db:
            uow = SQLAlchemyUnitOfWork(db)
            async with uow:
                # Get completed workflow runs older than cutoff
                old_completed_runs = await uow.workflow_runs.list_completed_before(
                    cutoff_time
                )

                logger.info(
                    f"Found {len(old_completed_runs)} old completed workflow runs to clean up"
                )

                for workflow_run in old_completed_runs:
                    try:
                        # Clear Redis cache
                        await redis_client.delete_cache(
                            f"workflow_status:{workflow_run.workflow_id.value}:{workflow_run.id.value}"
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to clean cache for {workflow_run.id.value}: {e}"
                        )

        await redis_client.disconnect()
        logger.info("Finished cleanup of completed workflows")

    except Exception as e:
        logger.error(f"Error in workflow cleanup: {e}")
        raise


async def _sync_workflow_tasks_impl(workflow_id: str, run_id: str):
    """Sync task instances for a workflow run"""
    logger.info(f"Syncing task instances for workflow run {workflow_id}/{run_id}")

    try:
        airflow_client = AirflowClient()
        redis_client = RedisClient()
        await redis_client.connect()

        event_service = EventService(redis_client)
        event_publisher = WorkflowEventPublisher(event_service)

        # Get task instances from Airflow
        task_instances_response = await airflow_client.get_task_instances(
            workflow_id, run_id
        )
        task_instances = task_instances_response.get("task_instances", [])

        # Process each task instance
        for task_instance in task_instances:
            task_id = task_instance.get("task_id")
            state = task_instance.get("state")

            # Publish task events
            if state == "running":
                await event_publisher.task_started(
                    workflow_id=workflow_id,
                    run_id=run_id,
                    task_id=task_id,
                    start_date=task_instance.get("start_date"),
                    hostname=task_instance.get("hostname"),
                )
            elif state == "success":
                await event_publisher.task_completed(
                    workflow_id=workflow_id,
                    run_id=run_id,
                    task_id=task_id,
                    success=True,
                    end_date=task_instance.get("end_date"),
                    duration=task_instance.get("duration"),
                )
            elif state == "failed":
                await event_publisher.task_completed(
                    workflow_id=workflow_id,
                    run_id=run_id,
                    task_id=task_id,
                    success=False,
                    end_date=task_instance.get("end_date"),
                    duration=task_instance.get("duration"),
                )
                # Trigger task failed notification
                trigger_task_failed_notification(
                    workflow_id=workflow_id,
                    run_id=run_id,
                    task_id=task_id,
                    additional_data={
                        "end_date": task_instance.get("end_date"),
                        "duration": task_instance.get("duration"),
                        "hostname": task_instance.get("hostname"),
                    },
                )

        await redis_client.disconnect()
        logger.info(
            f"Finished syncing task instances for workflow run {workflow_id}/{run_id}"
        )

    except Exception as e:
        logger.error(f"Error syncing task instances for {workflow_id}/{run_id}: {e}")
        raise


async def _update_workflow_run_status(
    workflow_id: str, run_id: str, dag_run_data: Dict[str, Any]
):
    """Update workflow run status in database"""
    try:
        async with AsyncSessionLocal() as db:
            uow = SQLAlchemyUnitOfWork(db)
            async with uow:
                workflow_run = await uow.workflow_runs.get_by_id(WorkflowRunId(run_id))
                if workflow_run:
                    # Update status
                    airflow_state = dag_run_data.get("state", "unknown")
                    status = _map_airflow_status(airflow_state)
                    workflow_run.update_status(status)

                    # Update timestamps
                    if dag_run_data.get("start_date"):
                        workflow_run.start_date = datetime.fromisoformat(
                            dag_run_data["start_date"].replace("Z", "+00:00")
                        )

                    if dag_run_data.get("end_date"):
                        workflow_run.end_date = datetime.fromisoformat(
                            dag_run_data["end_date"].replace("Z", "+00:00")
                        )

                    await uow.workflow_runs.update(workflow_run)
                    await uow.commit()

    except Exception as e:
        logger.error(f"Error updating workflow run status: {e}")


def _map_airflow_status(airflow_state: str) -> WorkflowStatus:
    """Map Airflow state to WorkflowStatus"""
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
        "scheduled": WorkflowStatus.SCHEDULED,
    }
    return mapping.get(airflow_state, WorkflowStatus.QUEUED)


# Simple DAG chaining task
if CELERY_AVAILABLE and celery_app:
    @celery_app.task(bind=True)
    def trigger_next_dag_after_completion(
        self, 
        current_dag_id: str, 
        current_run_id: str, 
        next_dag_id: str, 
        task_id: int,
        triggered_by: int,
        parameters: dict,
        note: str
    ):
        """Monitor current DAG and trigger next DAG when it completes successfully"""
        # Use asyncio to run the async implementation
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_trigger_next_dag_impl(
                current_dag_id, current_run_id, next_dag_id, task_id, triggered_by, parameters, note
            ))
            return result
        finally:
            loop.close()
else:
    def trigger_next_dag_after_completion(*args, **kwargs):
        logger.warning("Celery not available - DAG chaining disabled")
        return None
    
    trigger_next_dag_after_completion.delay = trigger_next_dag_after_completion


async def _trigger_next_dag_impl(
    current_dag_id: str, 
    current_run_id: str, 
    next_dag_id: str, 
    task_id: int,
    triggered_by: int,
    parameters: dict,
    note: str
):
    """Implementation of next DAG triggering"""
    logger.info(f"=== CELERY TASK STARTED ===")
    logger.info(f"_trigger_next_dag_impl called with:")
    logger.info(f"  current_dag_id: {current_dag_id}")
    logger.info(f"  current_run_id: {current_run_id}")
    logger.info(f"  next_dag_id: {next_dag_id}")
    logger.info(f"  task_id: {task_id}")
    logger.info(f"  triggered_by: {triggered_by}")
    logger.info(f"  parameters: {parameters}")
    logger.info(f"  note: {note}")
    logger.info(f"Starting monitoring DAG {current_dag_id}/{current_run_id} to trigger {next_dag_id}")
    
    try:
        airflow_client = AirflowClient()
        max_wait_minutes = 30  # Wait up to 30 minutes
        check_interval = 10  # Check every 10 seconds
        
        for _ in range((max_wait_minutes * 60) // check_interval):
            try:
                # Check current DAG status
                dag_run_response = await airflow_client.get_dag_run_status(
                    current_dag_id, current_run_id
                )
                
                state = dag_run_response.get("state")
                logger.info(f"Current DAG {current_dag_id} state: {state}")
                
                if state == "success":
                    logger.info(f"DAG {current_dag_id} completed successfully, triggering {next_dag_id}")
                    
                    # Import here to avoid circular imports
                    from app.application.use_cases.workflow_use_cases import (
                        WorkflowUseCases, 
                        TriggerWorkflowCommand
                    )
                    
                    async with AsyncSessionLocal() as db:
                        uow = SQLAlchemyUnitOfWork(db)
                        workflow_use_cases = WorkflowUseCases(uow)
                        
                        # Get or create workflow for next DAG
                        workflow = await workflow_use_cases.get_or_create_workflow(
                            name=f"{next_dag_id.replace('_', ' ').title()}",
                            dag_id=next_dag_id,
                            description=f"Auto-created workflow for {next_dag_id}",
                            created_by_id=triggered_by
                        )
                        
                        # Trigger next DAG
                        command = TriggerWorkflowCommand(
                            workflow_id=workflow.id.value,
                            triggered_by=triggered_by,
                            task_id=task_id,
                            dataset_id=None,
                            parameters=parameters,
                            note=note
                        )
                        
                        workflow_run = await workflow_use_cases.trigger_workflow(command)
                        logger.info(f"Successfully triggered {next_dag_id}, run_id: {workflow_run.id.value}")
                        
                        # Check if there are more DAGs in the chain
                        from app.application.tasks.dag_chain_tasks import DAG_EXECUTION_CHAIN
                        current_dag_index = None
                        for i, dag_id in enumerate(DAG_EXECUTION_CHAIN):
                            if dag_id == next_dag_id:
                                current_dag_index = i
                                break
                        
                        if current_dag_index is not None and current_dag_index + 1 < len(DAG_EXECUTION_CHAIN):
                            # There's another DAG after the one we just triggered
                            next_next_dag_id = DAG_EXECUTION_CHAIN[current_dag_index + 1]
                            logger.info(f"Scheduling monitoring for {next_dag_id} to trigger {next_next_dag_id}")
                            
                            # Schedule next monitoring task
                            trigger_next_dag_after_completion.delay(
                                current_dag_id=next_dag_id,
                                current_run_id=workflow_run.id.value,
                                next_dag_id=next_next_dag_id,
                                task_id=task_id,
                                triggered_by=triggered_by,
                                parameters=parameters,
                                note=f"DAG {current_dag_index + 2}/{len(DAG_EXECUTION_CHAIN)}: {next_next_dag_id} - Auto-triggered from previous DAG completion"
                            )
                        else:
                            logger.info(f"No more DAGs in chain after {next_dag_id}")
                            logger.info(f"All DAGs completed successfully! Updating task {task_id} status to COMPLETED")
                            
                            # Update task status to completed - all DAGs in chain are done
                            from app.application.use_cases.task_use_cases import TaskUseCases
                            async with AsyncSessionLocal() as db:
                                uow = SQLAlchemyUnitOfWork(db)
                                task_use_cases = TaskUseCases(uow)
                                await task_use_cases.update_task_status(task_id, TaskStatus.COMPLETED)
                                logger.info(f"Task {task_id} status updated to COMPLETED")
                        
                    return f"Successfully triggered {next_dag_id}"
                    
                elif state in ["failed", "up_for_retry", "upstream_failed"]:
                    logger.error(f"DAG {current_dag_id} failed with state: {state}")
                    
                    # Update task status to failed
                    from app.application.use_cases.task_use_cases import TaskUseCases
                    async with AsyncSessionLocal() as db:
                        uow = SQLAlchemyUnitOfWork(db)
                        task_use_cases = TaskUseCases(uow)
                        await task_use_cases.update_task_status(task_id, TaskStatus.FAILED)
                    
                    return f"DAG chain stopped - {current_dag_id} failed"
                    
                # Still running, continue monitoring
                await asyncio.sleep(check_interval)
                
            except Exception as e:
                logger.warning(f"Error checking DAG status: {e}")
                await asyncio.sleep(check_interval)
        
        logger.warning(f"Timeout waiting for DAG {current_dag_id} to complete")
        return f"Timeout monitoring {current_dag_id}"
        
    except Exception as e:
        logger.error(f"Error in DAG chaining: {e}")
        raise
