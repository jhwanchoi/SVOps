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