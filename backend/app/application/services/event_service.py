import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from enum import Enum

from app.core.redis import RedisClient, get_redis
from app.core.config import settings

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    WORKFLOW_TRIGGERED = "workflow.triggered"
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
    WORKFLOW_STOPPED = "workflow.stopped"
    WORKFLOW_RETRIED = "workflow.retried"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    SYSTEM_ERROR = "system.error"


@dataclass
class Event:
    type: EventType
    workflow_id: str
    run_id: Optional[str] = None
    task_id: Optional[str] = None
    user_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    data: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.data is None:
            self.data = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type.value,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


class EventService:
    def __init__(self, redis_client: RedisClient):
        self.redis = redis_client
        self.subscribers: Dict[str, List[Callable]] = {}

    def get_channel_name(self, workflow_id: str, run_id: Optional[str] = None) -> str:
        """Generate Redis channel name for workflow events"""
        if run_id:
            return f"{settings.WEBSOCKET_CHANNEL_PREFIX}:workflow:{workflow_id}:run:{run_id}"
        return f"{settings.WEBSOCKET_CHANNEL_PREFIX}:workflow:{workflow_id}"

    def get_global_channel_name(self) -> str:
        """Get global events channel name"""
        return f"{settings.WEBSOCKET_CHANNEL_PREFIX}:global"

    def get_user_channel_name(self, user_id: int) -> str:
        """Get user-specific events channel name"""
        return f"{settings.WEBSOCKET_CHANNEL_PREFIX}:user:{user_id}"

    async def publish_event(self, event: Event) -> None:
        """Publish event to relevant channels"""
        try:
            event_data = event.to_dict()

            # Publish to workflow-specific channel
            workflow_channel = self.get_channel_name(event.workflow_id, event.run_id)
            await self.redis.publish(workflow_channel, event_data)

            # Publish to global events channel
            global_channel = self.get_global_channel_name()
            await self.redis.publish(global_channel, event_data)

            # Publish to user-specific channel if user_id is provided
            if event.user_id:
                user_channel = self.get_user_channel_name(event.user_id)
                await self.redis.publish(user_channel, event_data)

            logger.info(
                f"Published event {event.type} for workflow {event.workflow_id}"
            )

        except Exception as e:
            logger.error(f"Failed to publish event {event.type}: {e}")
            raise

    async def subscribe_to_workflow(
        self, workflow_id: str, run_id: Optional[str] = None
    ):
        """Subscribe to workflow events"""
        channel = self.get_channel_name(workflow_id, run_id)
        return await self.redis.subscribe(channel)

    async def subscribe_to_global_events(self):
        """Subscribe to global events"""
        channel = self.get_global_channel_name()
        return await self.redis.subscribe(channel)

    async def subscribe_to_user_events(self, user_id: int):
        """Subscribe to user-specific events"""
        channel = self.get_user_channel_name(user_id)
        return await self.redis.subscribe(channel)

    async def cache_workflow_status(
        self,
        workflow_id: str,
        run_id: str,
        status_data: Dict[str, Any],
        ttl: int = 3600,
    ):
        """Cache workflow status for quick retrieval"""
        cache_key = f"workflow_status:{workflow_id}:{run_id}"
        await self.redis.set_cache(cache_key, status_data, ttl)

    async def get_cached_workflow_status(
        self, workflow_id: str, run_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached workflow status"""
        cache_key = f"workflow_status:{workflow_id}:{run_id}"
        return await self.redis.get_cache(cache_key)

    async def clear_workflow_cache(self, workflow_id: str, run_id: str):
        """Clear cached workflow status"""
        cache_key = f"workflow_status:{workflow_id}:{run_id}"
        await self.redis.delete_cache(cache_key)


class WorkflowEventPublisher:
    """Helper class for publishing workflow-specific events"""

    def __init__(self, event_service: EventService):
        self.event_service = event_service

    async def workflow_triggered(
        self, workflow_id: str, run_id: str, user_id: Optional[int] = None, **data
    ):
        event = Event(
            type=EventType.WORKFLOW_TRIGGERED,
            workflow_id=workflow_id,
            run_id=run_id,
            user_id=user_id,
            data=data,
        )
        await self.event_service.publish_event(event)

    async def workflow_started(self, workflow_id: str, run_id: str, **data):
        event = Event(
            type=EventType.WORKFLOW_STARTED,
            workflow_id=workflow_id,
            run_id=run_id,
            data=data,
        )
        await self.event_service.publish_event(event)

    async def workflow_completed(
        self, workflow_id: str, run_id: str, success: bool = True, **data
    ):
        event_type = (
            EventType.WORKFLOW_COMPLETED if success else EventType.WORKFLOW_FAILED
        )
        event = Event(
            type=event_type, workflow_id=workflow_id, run_id=run_id, data=data
        )
        await self.event_service.publish_event(event)

    async def workflow_stopped(
        self, workflow_id: str, run_id: str, user_id: Optional[int] = None, **data
    ):
        event = Event(
            type=EventType.WORKFLOW_STOPPED,
            workflow_id=workflow_id,
            run_id=run_id,
            user_id=user_id,
            data=data,
        )
        await self.event_service.publish_event(event)

    async def workflow_retried(
        self, workflow_id: str, run_id: str, user_id: Optional[int] = None, **data
    ):
        event = Event(
            type=EventType.WORKFLOW_RETRIED,
            workflow_id=workflow_id,
            run_id=run_id,
            user_id=user_id,
            data=data,
        )
        await self.event_service.publish_event(event)

    async def task_started(self, workflow_id: str, run_id: str, task_id: str, **data):
        event = Event(
            type=EventType.TASK_STARTED,
            workflow_id=workflow_id,
            run_id=run_id,
            task_id=task_id,
            data=data,
        )
        await self.event_service.publish_event(event)

    async def task_completed(
        self, workflow_id: str, run_id: str, task_id: str, success: bool = True, **data
    ):
        event_type = EventType.TASK_COMPLETED if success else EventType.TASK_FAILED
        event = Event(
            type=event_type,
            workflow_id=workflow_id,
            run_id=run_id,
            task_id=task_id,
            data=data,
        )
        await self.event_service.publish_event(event)


# Global instances
def get_event_service() -> EventService:
    """Dependency to get event service"""
    from app.core.redis import redis_client

    return EventService(redis_client)


def get_workflow_event_publisher() -> WorkflowEventPublisher:
    """Dependency to get workflow event publisher"""
    event_service = get_event_service()
    return WorkflowEventPublisher(event_service)
