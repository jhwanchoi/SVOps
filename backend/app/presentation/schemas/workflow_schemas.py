from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from app.shared.types import WorkflowStatus, WorkflowTriggerType


class WorkflowBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    dag_id: str = Field(..., min_length=1, max_length=100)


class WorkflowCreate(WorkflowBase):
    created_by_id: Optional[int] = None


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    is_active: Optional[bool] = None


class WorkflowResponse(WorkflowBase):
    id: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    created_by_id: Optional[int]

    class Config:
        from_attributes = True


class WorkflowConfigurationSchema(BaseModel):
    task_id: Optional[int] = None
    dataset_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)


class WorkflowRunBase(BaseModel):
    workflow_id: str = Field(..., min_length=1)
    status: WorkflowStatus
    trigger_type: WorkflowTriggerType
    configuration: WorkflowConfigurationSchema


class WorkflowRunCreate(BaseModel):
    task_id: Optional[int] = None
    dataset_id: Optional[int] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    note: Optional[str] = Field(None, max_length=1000)


class WorkflowRunResponse(WorkflowRunBase):
    id: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    execution_date: Optional[datetime]
    triggered_by: Optional[int]
    external_trigger_id: Optional[str]
    note: Optional[str]

    class Config:
        from_attributes = True


class WorkflowRunListResponse(BaseModel):
    runs: List[WorkflowRunResponse]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool


class WorkflowControlRequest(BaseModel):
    action: str = Field(..., pattern="^(stop|retry|pause|resume)$")
    note: Optional[str] = Field(None, max_length=500)


class WorkflowStatusUpdate(BaseModel):
    status: WorkflowStatus
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    note: Optional[str] = None


class TaskInstanceResponse(BaseModel):
    task_id: str
    dag_id: str
    execution_date: datetime
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    duration: Optional[float]
    state: str
    try_number: int
    max_tries: int
    hostname: Optional[str]
    unixname: Optional[str]
    pool: str
    queue: str
    priority_weight: int
    operator: str
    log_url: Optional[str]


class WorkflowRunDetailResponse(WorkflowRunResponse):
    task_instances: List[TaskInstanceResponse] = Field(default_factory=list)
    log_url: Optional[str] = None
    graph_url: Optional[str] = None
