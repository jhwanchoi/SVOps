import asyncio
import logging
from typing import Dict, Any, Optional
from celery import Task

from app.core.celery_app import celery_app
from app.application.services.notification_service import (
    NotificationService,
    NotificationType,
    get_notification_service,
)

logger = logging.getLogger(__name__)


class AsyncNotificationTask(Task):
    """Base class for async notification tasks"""

    def __call__(self, *args, **kwargs):
        return asyncio.get_event_loop().run_until_complete(
            self.run_async(*args, **kwargs)
        )

    async def run_async(self, *args, **kwargs):
        raise NotImplementedError


@celery_app.task(bind=True, base=AsyncNotificationTask)
async def send_workflow_started_notification(
    self,
    workflow_id: str,
    run_id: str,
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Send notification when workflow starts"""
    logger.info(f"Sending workflow started notification for {workflow_id}/{run_id}")

    try:
        notification_service = get_notification_service()
        await notification_service.send_workflow_notification(
            notification_type=NotificationType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            run_id=run_id,
            status="running",
            user_id=user_id,
            additional_data=additional_data,
        )
        logger.info(f"Workflow started notification sent for {workflow_id}/{run_id}")

    except Exception as e:
        logger.error(f"Failed to send workflow started notification: {e}")
        raise


@celery_app.task(bind=True, base=AsyncNotificationTask)
async def send_workflow_completed_notification(
    self,
    workflow_id: str,
    run_id: str,
    success: bool = True,
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Send notification when workflow completes"""
    status = "completed" if success else "failed"
    notification_type = (
        NotificationType.WORKFLOW_COMPLETED
        if success
        else NotificationType.WORKFLOW_FAILED
    )

    logger.info(f"Sending workflow {status} notification for {workflow_id}/{run_id}")

    try:
        notification_service = get_notification_service()
        await notification_service.send_workflow_notification(
            notification_type=notification_type,
            workflow_id=workflow_id,
            run_id=run_id,
            status=status,
            user_id=user_id,
            additional_data=additional_data,
        )
        logger.info(f"Workflow {status} notification sent for {workflow_id}/{run_id}")

    except Exception as e:
        logger.error(f"Failed to send workflow {status} notification: {e}")
        raise


@celery_app.task(bind=True, base=AsyncNotificationTask)
async def send_workflow_stopped_notification(
    self,
    workflow_id: str,
    run_id: str,
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Send notification when workflow is stopped"""
    logger.info(f"Sending workflow stopped notification for {workflow_id}/{run_id}")

    try:
        notification_service = get_notification_service()
        await notification_service.send_workflow_notification(
            notification_type=NotificationType.WORKFLOW_STOPPED,
            workflow_id=workflow_id,
            run_id=run_id,
            status="stopped",
            user_id=user_id,
            additional_data=additional_data,
        )
        logger.info(f"Workflow stopped notification sent for {workflow_id}/{run_id}")

    except Exception as e:
        logger.error(f"Failed to send workflow stopped notification: {e}")
        raise


@celery_app.task(bind=True, base=AsyncNotificationTask)
async def send_task_failed_notification(
    self,
    workflow_id: str,
    run_id: str,
    task_id: str,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Send notification when a task fails"""
    logger.info(
        f"Sending task failed notification for {workflow_id}/{run_id}/{task_id}"
    )

    try:
        notification_service = get_notification_service()

        # Add task_id to notification data
        notification_data = additional_data or {}
        notification_data["task_id"] = task_id

        await notification_service.send_workflow_notification(
            notification_type=NotificationType.TASK_FAILED,
            workflow_id=workflow_id,
            run_id=run_id,
            status="task_failed",
            additional_data=notification_data,
        )
        logger.info(
            f"Task failed notification sent for {workflow_id}/{run_id}/{task_id}"
        )

    except Exception as e:
        logger.error(f"Failed to send task failed notification: {e}")
        raise


@celery_app.task(bind=True, base=AsyncNotificationTask)
async def send_system_error_notification(
    self,
    message: str,
    severity: str = "error",
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Send system error notification"""
    logger.info(f"Sending system error notification: {message}")

    try:
        notification_service = get_notification_service()
        await notification_service.send_system_notification(
            notification_type=NotificationType.SYSTEM_ERROR,
            message=message,
            severity=severity,
            additional_data=additional_data,
        )
        logger.info(f"System error notification sent: {message}")

    except Exception as e:
        logger.error(f"Failed to send system error notification: {e}")
        raise


@celery_app.task(bind=True, base=AsyncNotificationTask)
async def send_bulk_notifications(self, notifications: list):
    """Send multiple notifications in bulk"""
    logger.info(f"Sending {len(notifications)} bulk notifications")

    try:
        notification_service = get_notification_service()

        for notification in notifications:
            notification_type = notification.get("type")

            if notification_type in [
                "workflow_started",
                "workflow_completed",
                "workflow_failed",
                "workflow_stopped",
                "task_failed",
            ]:
                await notification_service.send_workflow_notification(
                    notification_type=NotificationType(notification_type),
                    workflow_id=notification.get("workflow_id"),
                    run_id=notification.get("run_id"),
                    status=notification.get("status"),
                    user_id=notification.get("user_id"),
                    additional_data=notification.get("additional_data"),
                )
            elif notification_type == "system_error":
                await notification_service.send_system_notification(
                    notification_type=NotificationType.SYSTEM_ERROR,
                    message=notification.get("message"),
                    severity=notification.get("severity", "error"),
                    additional_data=notification.get("additional_data"),
                )

        logger.info(f"Bulk notifications sent successfully")

    except Exception as e:
        logger.error(f"Failed to send bulk notifications: {e}")
        raise


# Convenience functions for triggering notifications
def trigger_workflow_started_notification(
    workflow_id: str,
    run_id: str,
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Trigger workflow started notification"""
    send_workflow_started_notification.delay(
        workflow_id=workflow_id,
        run_id=run_id,
        user_id=user_id,
        additional_data=additional_data,
    )


def trigger_workflow_completed_notification(
    workflow_id: str,
    run_id: str,
    success: bool = True,
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Trigger workflow completed/failed notification"""
    send_workflow_completed_notification.delay(
        workflow_id=workflow_id,
        run_id=run_id,
        success=success,
        user_id=user_id,
        additional_data=additional_data,
    )


def trigger_workflow_stopped_notification(
    workflow_id: str,
    run_id: str,
    user_id: Optional[int] = None,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Trigger workflow stopped notification"""
    send_workflow_stopped_notification.delay(
        workflow_id=workflow_id,
        run_id=run_id,
        user_id=user_id,
        additional_data=additional_data,
    )


def trigger_task_failed_notification(
    workflow_id: str,
    run_id: str,
    task_id: str,
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Trigger task failed notification"""
    send_task_failed_notification.delay(
        workflow_id=workflow_id,
        run_id=run_id,
        task_id=task_id,
        additional_data=additional_data,
    )


def trigger_system_error_notification(
    message: str,
    severity: str = "error",
    additional_data: Optional[Dict[str, Any]] = None,
):
    """Trigger system error notification"""
    send_system_error_notification.delay(
        message=message, severity=severity, additional_data=additional_data
    )
