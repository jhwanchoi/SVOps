from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl

from app.application.services.notification_service import (
    NotificationService,
    NotificationConfig,
    NotificationType,
    NotificationChannel,
    get_notification_service,
)
from app.application.tasks.notification_tasks import (
    trigger_workflow_started_notification,
    trigger_workflow_completed_notification,
    trigger_system_error_notification,
)
from app.core.dependencies import get_current_active_user, get_current_superuser
from app.domain.entities import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationConfigCreate(BaseModel):
    name: str
    channel: NotificationChannel
    webhook_url: HttpUrl
    enabled: bool = True
    notification_types: List[NotificationType] = []
    filters: dict = {}


class NotificationConfigResponse(BaseModel):
    name: str
    channel: NotificationChannel
    webhook_url: str
    enabled: bool
    notification_types: List[NotificationType]
    filters: dict

    class Config:
        from_attributes = True




@router.post(
    "/configs",
    response_model=NotificationConfigResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_notification_config(
    config_data: NotificationConfigCreate,
    current_user: User = Depends(get_current_superuser),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Create a new notification configuration (admin only)"""
    try:
        config = NotificationConfig(
            name=config_data.name,
            channel=config_data.channel,
            webhook_url=config_data.webhook_url,
            enabled=config_data.enabled,
            notification_types=config_data.notification_types,
            filters=config_data.filters,
        )

        notification_service.add_config(config)

        return NotificationConfigResponse(
            name=config.name,
            channel=config.channel,
            webhook_url=str(config.webhook_url),
            enabled=config.enabled,
            notification_types=config.notification_types,
            filters=config.filters,
        )

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/configs", response_model=List[NotificationConfigResponse])
async def list_notification_configs(
    current_user: User = Depends(get_current_superuser),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """List all notification configurations (admin only)"""
    configs = []
    for config in notification_service.notification_configs:
        configs.append(
            NotificationConfigResponse(
                name=config.name,
                channel=config.channel,
                webhook_url=str(config.webhook_url),
                enabled=config.enabled,
                notification_types=config.notification_types,
                filters=config.filters,
            )
        )

    return configs


@router.delete("/configs/{config_name}")
async def delete_notification_config(
    config_name: str,
    current_user: User = Depends(get_current_superuser),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Delete notification configuration (admin only)"""
    initial_count = len(notification_service.notification_configs)
    notification_service.notification_configs = [
        config
        for config in notification_service.notification_configs
        if config.name != config_name
    ]

    if len(notification_service.notification_configs) == initial_count:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification config '{config_name}' not found",
        )

    return {"message": f"Notification config '{config_name}' deleted successfully"}




@router.get("/types")
async def get_notification_types(current_user: User = Depends(get_current_active_user)):
    """Get available notification types"""
    return {
        "notification_types": [nt.value for nt in NotificationType],
        "channels": [ch.value for ch in NotificationChannel],
    }


@router.post("/configs/{config_name}/enable")
async def enable_notification_config(
    config_name: str,
    current_user: User = Depends(get_current_superuser),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Enable notification configuration (admin only)"""
    for config in notification_service.notification_configs:
        if config.name == config_name:
            config.enabled = True
            return {"message": f"Notification config '{config_name}' enabled"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Notification config '{config_name}' not found",
    )


@router.post("/configs/{config_name}/disable")
async def disable_notification_config(
    config_name: str,
    current_user: User = Depends(get_current_superuser),
    notification_service: NotificationService = Depends(get_notification_service),
):
    """Disable notification configuration (admin only)"""
    for config in notification_service.notification_configs:
        if config.name == config_name:
            config.enabled = False
            return {"message": f"Notification config '{config_name}' disabled"}

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Notification config '{config_name}' not found",
    )


# Webhook endpoint for receiving external notifications
@router.post("/webhook/{config_name}")
async def receive_webhook(config_name: str, payload: dict):
    """Receive webhook from external services"""
    # This endpoint can be used to receive notifications from external services
    # and trigger internal notifications based on the payload

    # For security, you might want to add webhook signature verification here

    try:
        # Process the webhook payload
        # This is a basic example - customize based on your needs

        if payload.get("type") == "deployment":
            trigger_system_error_notification(
                message=f"External deployment notification: {payload.get('message', 'Unknown')}",
                severity="info",
                additional_data=payload,
            )

        return {"message": "Webhook received successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process webhook: {str(e)}",
        )
