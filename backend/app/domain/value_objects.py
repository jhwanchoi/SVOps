from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime

from app.shared.exceptions import ValidationError
from app.shared.types import (
    RecordingType,
    TaskStatus,
    WorkflowStatus,
    WorkflowTriggerType,
)


@dataclass(frozen=True)
class UserId:
    value: int

    def __post_init__(self):
        if self.value <= 0:
            raise ValidationError("user_id", "User ID must be positive")


@dataclass(frozen=True)
class DatasetId:
    value: int

    def __post_init__(self):
        if self.value <= 0:
            raise ValidationError("dataset_id", "Dataset ID must be positive")


@dataclass(frozen=True)
class TaskId:
    value: int

    def __post_init__(self):
        if self.value <= 0:
            raise ValidationError("task_id", "Task ID must be positive")


@dataclass(frozen=True)
class DatasetPath:
    path: str
    gt_path: Optional[str] = None

    def __post_init__(self):
        if not self.path or not self.path.strip():
            raise ValidationError("path", "Dataset path cannot be empty")


@dataclass(frozen=True)
class TaskConfiguration:
    branch_name: Optional[str]
    commit_id: Optional[str]
    build_config: Optional[str]
    is_customized: bool = False
    custom_conf: Dict[str, Any] = None
    custom_ini: Dict[str, Any] = None

    def __post_init__(self):
        if self.custom_conf is None:
            object.__setattr__(self, "custom_conf", {})
        if self.custom_ini is None:
            object.__setattr__(self, "custom_ini", {})


@dataclass(frozen=True)
class VideoOutput:
    enabled: bool
    path: str = ""

    def __post_init__(self):
        if self.enabled and not self.path.strip():
            raise ValidationError(
                "video_path", "Video output path required when enabled"
            )


@dataclass(frozen=True)
class WorkflowId:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValidationError("workflow_id", "Workflow ID cannot be empty")


@dataclass(frozen=True)
class WorkflowRunId:
    value: str

    def __post_init__(self):
        if not self.value or not self.value.strip():
            raise ValidationError("workflow_run_id", "Workflow Run ID cannot be empty")


@dataclass(frozen=True)
class WorkflowConfiguration:
    task_id: Optional[int] = None
    dataset_id: Optional[int] = None
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            object.__setattr__(self, "parameters", {})
