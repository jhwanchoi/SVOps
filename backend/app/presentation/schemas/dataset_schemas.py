from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

from app.shared.types import RecordingType


class DatasetBase(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = None
    path: str = Field(..., max_length=255)
    data_type: RecordingType
    gt_path: Optional[str] = Field(None, max_length=255)


class DatasetCreate(DatasetBase):
    created_by_id: Optional[int] = None


class DatasetUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    path: Optional[str] = Field(None, max_length=255)
    data_type: Optional[RecordingType] = None
    gt_path: Optional[str] = Field(None, max_length=255)


class DatasetResponse(DatasetBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None

    class Config:
        from_attributes = True
