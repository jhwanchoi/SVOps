from typing import TypeVar
from enum import Enum

EntityId = TypeVar("EntityId")


class RecordingType(str, Enum):
    SURF = "Surf"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    UP_FOR_RETRY = "up_for_retry"
    UP_FOR_RESCHEDULE = "up_for_reschedule"
    UPSTREAM_FAILED = "upstream_failed"
    SKIPPED = "skipped"
    REMOVED = "removed"
    SCHEDULED = "scheduled"


class WorkflowTriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    API = "api"
    EXTERNAL = "external"