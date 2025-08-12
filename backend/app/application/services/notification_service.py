import httpx
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, HttpUrl

from app.core.config import settings
from app.core.retry import with_retry, EXTERNAL_SERVICE_RETRY
from app.shared.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_STOPPED = "workflow_stopped"
    TASK_FAILED = "task_failed"
    SYSTEM_ERROR = "system_error"


class NotificationChannel(str, Enum):
    SLACK = "slack"
    WEBHOOK = "webhook"
    EMAIL = "email"


class NotificationConfig(BaseModel):
    name: str
    channel: NotificationChannel
    webhook_url: HttpUrl
    enabled: bool = True
    notification_types: List[NotificationType] = []
    filters: Dict[str, Any] = {}


class SlackMessage(BaseModel):
    text: str
    username: str = "SVOps Bot"
    icon_emoji: str = ":robot_face:"
    channel: Optional[str] = None
    attachments: List[Dict[str, Any]] = []
    blocks: List[Dict[str, Any]] = []


class WebhookMessage(BaseModel):
    event_type: str
    timestamp: str
    data: Dict[str, Any]
    metadata: Dict[str, Any] = {}


class NotificationService:
    def __init__(self):
        self.notification_configs: List[NotificationConfig] = []
        self._load_configs()

    def _load_configs(self):
        """Load notification configurations from settings"""
        # TODO: Load from database or configuration file
        # For now, use basic configuration
        pass

    def add_config(self, config: NotificationConfig):
        """Add notification configuration"""
        self.notification_configs.append(config)

    async def send_workflow_notification(
        self,
        notification_type: NotificationType,
        workflow_id: str,
        run_id: str,
        status: str,
        user_id: Optional[int] = None,
        additional_data: Dict[str, Any] = None,
    ):
        """Send workflow-related notification"""
        try:
            # Prepare notification data
            notification_data = {
                "workflow_id": workflow_id,
                "run_id": run_id,
                "status": status,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "additional_data": additional_data or {},
            }

            # Send to all configured channels
            for config in self.notification_configs:
                if not config.enabled:
                    continue

                if notification_type not in config.notification_types:
                    continue

                if not self._should_send_notification(config, notification_data):
                    continue

                await self._send_notification(
                    config, notification_type, notification_data
                )

        except Exception as e:
            logger.error(f"Error sending workflow notification: {e}")

    async def send_system_notification(
        self,
        notification_type: NotificationType,
        message: str,
        severity: str = "info",
        additional_data: Dict[str, Any] = None,
    ):
        """Send system-related notification"""
        try:
            notification_data = {
                "message": message,
                "severity": severity,
                "timestamp": datetime.now().isoformat(),
                "additional_data": additional_data or {},
            }

            for config in self.notification_configs:
                if not config.enabled:
                    continue

                if notification_type not in config.notification_types:
                    continue

                await self._send_notification(
                    config, notification_type, notification_data
                )

        except Exception as e:
            logger.error(f"Error sending system notification: {e}")

    def _should_send_notification(
        self, config: NotificationConfig, data: Dict[str, Any]
    ) -> bool:
        """Check if notification should be sent based on filters"""
        if not config.filters:
            return True

        # Apply filters
        for filter_key, filter_value in config.filters.items():
            if filter_key in data:
                if isinstance(filter_value, list):
                    if data[filter_key] not in filter_value:
                        return False
                else:
                    if data[filter_key] != filter_value:
                        return False

        return True

    async def _send_notification(
        self,
        config: NotificationConfig,
        notification_type: NotificationType,
        data: Dict[str, Any],
    ):
        """Send notification to specific channel"""
        try:
            if config.channel == NotificationChannel.SLACK:
                await self._send_slack_notification(config, notification_type, data)
            elif config.channel == NotificationChannel.WEBHOOK:
                await self._send_webhook_notification(config, notification_type, data)
            else:
                logger.warning(f"Unsupported notification channel: {config.channel}")

        except Exception as e:
            logger.error(f"Error sending notification to {config.name}: {e}")

    @with_retry(EXTERNAL_SERVICE_RETRY)
    async def _send_slack_notification(
        self,
        config: NotificationConfig,
        notification_type: NotificationType,
        data: Dict[str, Any],
    ):
        """Send Slack notification"""
        slack_message = self._build_slack_message(notification_type, data)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                str(config.webhook_url),
                json=slack_message.dict(),
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )

            if response.status_code != 200:
                raise ExternalServiceError(
                    f"Slack API error: {response.status_code} - {response.text}"
                )

            logger.info(f"Slack notification sent successfully to {config.name}")

    @with_retry(EXTERNAL_SERVICE_RETRY)
    async def _send_webhook_notification(
        self,
        config: NotificationConfig,
        notification_type: NotificationType,
        data: Dict[str, Any],
    ):
        """Send webhook notification"""
        webhook_message = WebhookMessage(
            event_type=notification_type.value,
            timestamp=datetime.now().isoformat(),
            data=data,
            metadata={
                "source": "svops",
                "version": "1.0.0",
                "config_name": config.name,
            },
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                str(config.webhook_url),
                json=webhook_message.dict(),
                headers={"Content-Type": "application/json"},
                timeout=30.0,
            )

            if response.status_code not in [200, 201, 202]:
                raise ExternalServiceError(
                    f"Webhook error: {response.status_code} - {response.text}"
                )

            logger.info(f"Webhook notification sent successfully to {config.name}")

    def _build_slack_message(
        self, notification_type: NotificationType, data: Dict[str, Any]
    ) -> SlackMessage:
        """Build Slack message based on notification type"""

        if notification_type == NotificationType.WORKFLOW_STARTED:
            return self._build_workflow_started_slack_message(data)
        elif notification_type == NotificationType.WORKFLOW_COMPLETED:
            return self._build_workflow_completed_slack_message(data)
        elif notification_type == NotificationType.WORKFLOW_FAILED:
            return self._build_workflow_failed_slack_message(data)
        elif notification_type == NotificationType.WORKFLOW_STOPPED:
            return self._build_workflow_stopped_slack_message(data)
        elif notification_type == NotificationType.TASK_FAILED:
            return self._build_task_failed_slack_message(data)
        elif notification_type == NotificationType.SYSTEM_ERROR:
            return self._build_system_error_slack_message(data)
        else:
            return SlackMessage(text=f"Unknown notification type: {notification_type}")

    def _build_workflow_started_slack_message(
        self, data: Dict[str, Any]
    ) -> SlackMessage:
        workflow_id = data.get("workflow_id", "Unknown")
        run_id = data.get("run_id", "Unknown")

        return SlackMessage(
            text=f"🚀 Workflow Started",
            attachments=[
                {
                    "color": "good",
                    "fields": [
                        {"title": "Workflow ID", "value": workflow_id, "short": True},
                        {"title": "Run ID", "value": run_id, "short": True},
                        {"title": "Status", "value": "Running", "short": True},
                        {
                            "title": "Timestamp",
                            "value": data.get("timestamp", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        )

    def _build_workflow_completed_slack_message(
        self, data: Dict[str, Any]
    ) -> SlackMessage:
        workflow_id = data.get("workflow_id", "Unknown")
        run_id = data.get("run_id", "Unknown")

        return SlackMessage(
            text=f"✅ Workflow Completed Successfully",
            attachments=[
                {
                    "color": "good",
                    "fields": [
                        {"title": "Workflow ID", "value": workflow_id, "short": True},
                        {"title": "Run ID", "value": run_id, "short": True},
                        {"title": "Status", "value": "Completed", "short": True},
                        {
                            "title": "Timestamp",
                            "value": data.get("timestamp", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        )

    def _build_workflow_failed_slack_message(
        self, data: Dict[str, Any]
    ) -> SlackMessage:
        workflow_id = data.get("workflow_id", "Unknown")
        run_id = data.get("run_id", "Unknown")

        return SlackMessage(
            text=f"❌ Workflow Failed",
            attachments=[
                {
                    "color": "danger",
                    "fields": [
                        {"title": "Workflow ID", "value": workflow_id, "short": True},
                        {"title": "Run ID", "value": run_id, "short": True},
                        {"title": "Status", "value": "Failed", "short": True},
                        {
                            "title": "Timestamp",
                            "value": data.get("timestamp", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        )

    def _build_workflow_stopped_slack_message(
        self, data: Dict[str, Any]
    ) -> SlackMessage:
        workflow_id = data.get("workflow_id", "Unknown")
        run_id = data.get("run_id", "Unknown")

        return SlackMessage(
            text=f"⏹️ Workflow Stopped",
            attachments=[
                {
                    "color": "warning",
                    "fields": [
                        {"title": "Workflow ID", "value": workflow_id, "short": True},
                        {"title": "Run ID", "value": run_id, "short": True},
                        {"title": "Status", "value": "Stopped", "short": True},
                        {
                            "title": "Timestamp",
                            "value": data.get("timestamp", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        )

    def _build_task_failed_slack_message(self, data: Dict[str, Any]) -> SlackMessage:
        workflow_id = data.get("workflow_id", "Unknown")
        run_id = data.get("run_id", "Unknown")
        task_id = data.get("task_id", "Unknown")

        return SlackMessage(
            text=f"⚠️ Task Failed",
            attachments=[
                {
                    "color": "warning",
                    "fields": [
                        {"title": "Workflow ID", "value": workflow_id, "short": True},
                        {"title": "Run ID", "value": run_id, "short": True},
                        {"title": "Task ID", "value": task_id, "short": True},
                        {
                            "title": "Timestamp",
                            "value": data.get("timestamp", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        )

    def _build_system_error_slack_message(self, data: Dict[str, Any]) -> SlackMessage:
        message = data.get("message", "Unknown error")
        severity = data.get("severity", "info")

        color = {"error": "danger", "warning": "warning", "info": "good"}.get(
            severity, "good"
        )

        return SlackMessage(
            text=f"🔥 System {severity.title()}",
            attachments=[
                {
                    "color": color,
                    "fields": [
                        {"title": "Message", "value": message, "short": False},
                        {"title": "Severity", "value": severity.title(), "short": True},
                        {
                            "title": "Timestamp",
                            "value": data.get("timestamp", ""),
                            "short": True,
                        },
                    ],
                }
            ],
        )


# Global notification service instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Dependency to get notification service"""
    return notification_service
