from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from abc import ABC

from app.shared.types import (
    RecordingType,
    TaskStatus,
    WorkflowStatus,
    WorkflowTriggerType,
)
from app.domain.value_objects import (
    UserId,
    DatasetId,
    TaskId,
    DatasetPath,
    TaskConfiguration,
    VideoOutput,
    WorkflowId,
    WorkflowRunId,
    WorkflowConfiguration,
)


class Entity(ABC):
    pass


@dataclass
class User(Entity):
    id: Optional[UserId]
    username: str
    email: str
    name: str
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.username or len(self.username.strip()) < 3:
            raise ValueError("Username must be at least 3 characters")
        if not self.email or "@" not in self.email:
            raise ValueError("Valid email is required")


@dataclass
class Dataset(Entity):
    id: Optional[DatasetId]
    name: str
    description: Optional[str]
    paths: DatasetPath
    data_type: RecordingType
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[UserId] = None

    def __post_init__(self):
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("Dataset name is required")


@dataclass
class Task(Entity):
    id: Optional[TaskId]
    name: str
    description: Optional[str]
    status: TaskStatus
    customer: str

    # Build configuration
    configuration: TaskConfiguration

    # Dataset and output
    dataset: Optional[Dataset] = None
    log_out_path: str = ""
    video_output: VideoOutput = field(default_factory=lambda: VideoOutput(False))

    created_at: Optional[datetime] = None
    created_by: Optional[UserId] = None

    def __post_init__(self):
        if not self.name or len(self.name.strip()) < 1:
            raise ValueError("Task name is required")
        if not self.customer or len(self.customer.strip()) < 1:
            raise ValueError("Customer is required")
        if not self.log_out_path:
            raise ValueError("Log output path is required")

    def update_status(self, new_status: TaskStatus) -> None:
        self.status = new_status

    def assign_dataset(self, dataset: Dataset) -> None:
        self.dataset = dataset

    def enable_video_output(self, output_path: str) -> None:
        self.video_output = VideoOutput(True, output_path)

    def disable_video_output(self) -> None:
        self.video_output = VideoOutput(False)


@dataclass
class Workflow(Entity):
    id: Optional[WorkflowId]
    name: str
    description: Optional[str]
    dag_id: str
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: Optional[UserId] = None

    def __post_init__(self):
        if not self.name or (isinstance(self.name, str) and len(self.name.strip()) < 1):
            raise ValueError("Workflow name is required")
        if not self.dag_id or (
            isinstance(self.dag_id, str) and len(self.dag_id.strip()) < 1
        ):
            raise ValueError("DAG ID is required")


@dataclass
class WorkflowRun(Entity):
    id: WorkflowRunId
    workflow_id: WorkflowId
    status: WorkflowStatus
    trigger_type: WorkflowTriggerType
    configuration: WorkflowConfiguration
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    execution_date: Optional[datetime] = None
    triggered_by: Optional[UserId] = None
    external_trigger_id: Optional[str] = None
    note: Optional[str] = None

    def update_status(self, new_status: WorkflowStatus) -> None:
        self.status = new_status
        if new_status in [WorkflowStatus.SUCCESS, WorkflowStatus.FAILED]:
            self.end_date = datetime.now()

    def mark_started(self) -> None:
        self.status = WorkflowStatus.RUNNING
        self.start_date = datetime.now()

    def mark_completed(self, success: bool = True) -> None:
        self.status = WorkflowStatus.SUCCESS if success else WorkflowStatus.FAILED
        self.end_date = datetime.now()
