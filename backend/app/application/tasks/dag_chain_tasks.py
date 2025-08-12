"""
Celery tasks for DAG chain execution monitoring and management
"""

import asyncio
from typing import List, Optional
from datetime import datetime
import logging

from app.core.celery_app import celery_app
from app.application.services.airflow_service import AirflowClient
from app.application.use_cases.workflow_use_cases import (
    WorkflowUseCases,
    TriggerWorkflowCommand,
)
from app.application.use_cases.task_use_cases import TaskUseCases
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.shared.types import WorkflowStatus, TaskStatus
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# DAG execution chain order
DAG_EXECUTION_CHAIN = [
    "data_processing_pipeline",
    "ml_training_pipeline",
    "simple_workflow_example",
]


@celery_app.task(bind=True, max_retries=3)
def monitor_dag_chain_completion(
    self, task_id: int, workflow_run_id: str, dag_index: int
):
    """
    Monitor a DAG completion and trigger the next DAG in chain if successful
    """
    try:
        logger.info(
            f"Starting DAG chain monitoring for task_id={task_id}, workflow_run_id={workflow_run_id}, dag_index={dag_index}"
        )

        # Run async monitoring in sync context
        asyncio.run(_monitor_dag_completion_async(task_id, workflow_run_id, dag_index))

    except Exception as exc:
        logger.error(f"DAG chain monitoring failed: {str(exc)}")
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


async def _monitor_dag_completion_async(
    task_id: int, workflow_run_id: str, dag_index: int
):
    """Async implementation of DAG completion monitoring"""

    airflow_client = AirflowClient()

    async with AsyncSessionLocal() as db:
        uow = SQLAlchemyUnitOfWork(db)
        workflow_use_cases = WorkflowUseCases(uow)
        task_use_cases = TaskUseCases(uow)

        max_wait_minutes = 60  # Maximum wait time
        check_interval = 30  # Check every 30 seconds
        total_checks = (max_wait_minutes * 60) // check_interval

        for check_count in range(total_checks):
            try:
                # Get current WorkflowRun from database
                async with uow:
                    from app.domain.value_objects import WorkflowRunId

                    workflow_run = await uow.workflow_runs.get_by_id(
                        WorkflowRunId(workflow_run_id)
                    )

                    if not workflow_run:
                        logger.error(f"WorkflowRun {workflow_run_id} not found")
                        return

                    # Get workflow to get DAG ID
                    workflow = await uow.workflows.get_by_id(workflow_run.workflow_id)
                    if not workflow:
                        logger.error(
                            f"Workflow {workflow_run.workflow_id.value} not found"
                        )
                        return

                # Check DAG status in Airflow
                try:
                    dag_run_response = await airflow_client.get_dag_run_status(
                        dag_id=workflow.dag_id, dag_run_id=workflow_run_id
                    )

                    airflow_state = dag_run_response.get("state")
                    logger.info(
                        f"DAG {workflow.dag_id} run {workflow_run_id} state: {airflow_state}"
                    )

                    if airflow_state == "success":
                        logger.info(f"DAG {workflow.dag_id} completed successfully!")

                        # Update WorkflowRun status
                        async with uow:
                            workflow_run.update_status(WorkflowStatus.SUCCESS)
                            if dag_run_response.get("end_date"):
                                workflow_run.end_date = datetime.fromisoformat(
                                    dag_run_response["end_date"].replace("Z", "+00:00")
                                )
                            await uow.workflow_runs.update(workflow_run)
                            await uow.commit()

                        # Trigger next DAG if exists
                        next_dag_index = dag_index + 1
                        if next_dag_index < len(DAG_EXECUTION_CHAIN):
                            await _trigger_next_dag(
                                task_id,
                                next_dag_index,
                                workflow_run.configuration.parameters,
                            )
                        else:
                            # All DAGs completed - update task status
                            logger.info(f"All DAGs completed for task {task_id}")
                            await task_use_cases.update_task_status(
                                task_id, TaskStatus.COMPLETED
                            )

                        return  # Exit monitoring

                    elif airflow_state == "failed":
                        logger.error(f"DAG {workflow.dag_id} failed!")

                        # Update WorkflowRun and Task status to failed
                        async with uow:
                            workflow_run.update_status(WorkflowStatus.FAILED)
                            await uow.workflow_runs.update(workflow_run)
                            await uow.commit()

                        await task_use_cases.update_task_status(
                            task_id, TaskStatus.FAILED
                        )
                        return  # Exit monitoring

                    elif airflow_state in ["running", "queued"]:
                        # Still running, continue monitoring
                        logger.info(
                            f"DAG {workflow.dag_id} still {airflow_state}, continuing to monitor..."
                        )

                        # Update WorkflowRun status if needed
                        current_status = (
                            WorkflowStatus.RUNNING
                            if airflow_state == "running"
                            else WorkflowStatus.QUEUED
                        )
                        if workflow_run.status != current_status:
                            async with uow:
                                workflow_run.update_status(current_status)
                                if airflow_state == "running" and dag_run_response.get(
                                    "start_date"
                                ):
                                    workflow_run.start_date = datetime.fromisoformat(
                                        dag_run_response["start_date"].replace(
                                            "Z", "+00:00"
                                        )
                                    )
                                await uow.workflow_runs.update(workflow_run)
                                await uow.commit()

                except Exception as e:
                    logger.warning(f"Failed to get DAG status from Airflow: {str(e)}")

                # Wait before next check
                await asyncio.sleep(check_interval)

            except Exception as e:
                logger.error(f"Error in DAG monitoring loop: {str(e)}")
                await asyncio.sleep(check_interval)

        # Timeout reached
        logger.warning(
            f"DAG chain monitoring timeout for task {task_id}, workflow_run {workflow_run_id}"
        )


async def _trigger_next_dag(task_id: int, dag_index: int, original_parameters: dict):
    """Trigger the next DAG in the chain"""

    if dag_index >= len(DAG_EXECUTION_CHAIN):
        logger.warning(
            f"Invalid DAG index {dag_index}, chain has {len(DAG_EXECUTION_CHAIN)} DAGs"
        )
        return

    next_dag_id = DAG_EXECUTION_CHAIN[dag_index]
    logger.info(
        f"Triggering next DAG: {next_dag_id} (index {dag_index}) for task {task_id}"
    )

    async with AsyncSessionLocal() as db:
        uow = SQLAlchemyUnitOfWork(db)
        workflow_use_cases = WorkflowUseCases(uow)

        try:
            # Get or create workflow for next DAG
            workflow = await workflow_use_cases.get_or_create_workflow(
                name=f"{next_dag_id.replace('_', ' ').title()}",
                dag_id=next_dag_id,
                description=f"Auto-created workflow for {next_dag_id}",
                created_by_id=original_parameters.get("triggered_by", 1),
            )

            # Prepare parameters for next DAG
            next_parameters = original_parameters.copy()
            next_parameters.update(
                {
                    "dag_chain_index": dag_index,
                    "dag_chain_total": len(DAG_EXECUTION_CHAIN),
                    "next_dag": (
                        DAG_EXECUTION_CHAIN[dag_index + 1]
                        if dag_index + 1 < len(DAG_EXECUTION_CHAIN)
                        else None
                    ),
                }
            )

            # Trigger next DAG
            command = TriggerWorkflowCommand(
                workflow_id=workflow.id.value,
                triggered_by=original_parameters.get("triggered_by"),
                task_id=task_id,
                dataset_id=original_parameters.get("dataset_id"),
                parameters=next_parameters,
                note=f"DAG Chain {dag_index+1}/{len(DAG_EXECUTION_CHAIN)}: {next_dag_id} - Auto-triggered from previous DAG completion",
            )

            workflow_run = await workflow_use_cases.trigger_workflow(command)

            logger.info(
                f"Successfully triggered DAG {next_dag_id}, WorkflowRun ID: {workflow_run.id.value}"
            )

            # Schedule monitoring for the new DAG
            monitor_dag_chain_completion.apply_async(
                args=[task_id, workflow_run.id.value, dag_index],
                countdown=30,  # Start monitoring after 30 seconds
            )

        except Exception as e:
            logger.error(f"Failed to trigger next DAG {next_dag_id}: {str(e)}")
            # Update task status to failed
            task_use_cases = TaskUseCases(uow)
            await task_use_cases.update_task_status(task_id, TaskStatus.FAILED)


@celery_app.task
def start_dag_chain_monitoring(task_id: int, workflow_run_id: str, dag_index: int = 0):
    """
    Start monitoring for DAG chain completion
    This is called after the first DAG is triggered
    """
    logger.info(f"Starting DAG chain monitoring for task {task_id}")

    # Schedule the monitoring task to run after a delay
    monitor_dag_chain_completion.apply_async(
        args=[task_id, workflow_run_id, dag_index],
        countdown=60,  # Start monitoring after 1 minute
    )

    return f"DAG chain monitoring scheduled for task {task_id}"
