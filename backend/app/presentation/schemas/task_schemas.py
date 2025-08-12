from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

from app.shared.types import TaskStatus
from app.presentation.schemas.dataset_schemas import DatasetResponse


class TaskConfigurationSchema(BaseModel):
    branch_name: Optional[str] = None
    commit_id: Optional[str] = None
    build_config: Optional[str] = None
    build_config_customized: bool = False
    build_config_custom_conf: Dict[str, Any] = {}
    build_config_custom_ini: Dict[str, Any] = {}


class VideoOutputSchema(BaseModel):
    enabled: bool = False
    path: str = ""


class TaskBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    customer: str = Field(..., max_length=32)
    log_out_path: str = Field(..., max_length=255)


class TaskCreate(TaskBase):
    # Status with default value
    status: TaskStatus = TaskStatus.PENDING

    # Build configuration
    branch_name: Optional[str] = None
    commit_id: Optional[str] = None
    build_config: Optional[str] = None
    build_config_customized: bool = False
    build_config_custom_conf: Dict[str, Any] = {}
    build_config_custom_ini: Dict[str, Any] = {}

    # Dataset and output
    dataset_id: Optional[int] = None
    video_out_enabled: bool = False
    video_out_path: str = ""

    created_by_id: Optional[int] = None


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    customer: Optional[str] = Field(None, max_length=32)
    log_out_path: Optional[str] = Field(None, max_length=255)

    # Build configuration updates
    branch_name: Optional[str] = None
    commit_id: Optional[str] = None
    build_config: Optional[str] = None
    build_config_customized: Optional[bool] = None
    build_config_custom_conf: Optional[Dict[str, Any]] = None
    build_config_custom_ini: Optional[Dict[str, Any]] = None

    # Dataset and output updates
    dataset_id: Optional[int] = None
    video_out_enabled: Optional[bool] = None
    video_out_path: Optional[str] = None


class TaskResponse(TaskBase):
    id: int
    status: TaskStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    created_by_id: Optional[int] = None

    # Configuration
    configuration: TaskConfigurationSchema

    # Dataset and output
    dataset: Optional[DatasetResponse] = None
    video_output: VideoOutputSchema

    class Config:
        from_attributes = True
