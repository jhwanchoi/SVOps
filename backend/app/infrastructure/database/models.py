from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(150), unique=True, index=True, nullable=False)
    email = Column(String(254), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(128), nullable=True)  # For future auth implementation
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    created_datasets = relationship("DatasetModel", back_populates="creator")
    created_tasks = relationship("TaskModel", back_populates="creator")


class DatasetModel(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    path = Column(String(255), nullable=False)
    data_type = Column(String(50), nullable=False)  # RecordingType enum values
    gt_path = Column(String(255), nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    # Relationships
    creator = relationship("UserModel", back_populates="created_datasets")
    tasks = relationship("TaskModel", back_populates="dataset")


class TaskModel(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String(64), index=True, nullable=False)  # TaskStatus enum values
    customer = Column(String(32), index=True, nullable=False)

    # SVent build configuration
    branch_name = Column(String(255), nullable=True)
    commit_id = Column(String(255), nullable=True)
    build_config = Column(String(256), nullable=True)
    build_config_customized = Column(Boolean, default=False, nullable=False)
    build_config_custom_conf = Column(JSON, default=dict, nullable=False)
    build_config_custom_ini = Column(JSON, default=dict, nullable=False)

    # SVnet inference
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    log_out_path = Column(String(255), nullable=False, default="")
    video_out_enabled = Column(Boolean, default=False, nullable=False)
    video_out_path = Column(String(255), nullable=False, default="")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    # Relationships
    creator = relationship("UserModel", back_populates="created_tasks")
    dataset = relationship("DatasetModel", back_populates="tasks")


class WorkflowModel(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    dag_id = Column(String(255), index=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_by_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)

    # Relationships
    creator = relationship("UserModel")
    workflow_runs = relationship("WorkflowRunModel", back_populates="workflow")


class WorkflowRunModel(Base):
    __tablename__ = "workflow_runs"

    id = Column(String(255), primary_key=True, index=True)  # Airflow run_id
    workflow_id = Column(
        Integer, ForeignKey("workflows.id"), index=True, nullable=False
    )
    status = Column(
        String(64), index=True, nullable=False
    )  # WorkflowStatus enum values
    trigger_type = Column(String(64), nullable=False)  # WorkflowTriggerType enum values
    configuration = Column(JSON, default=dict, nullable=False)  # WorkflowConfiguration
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)
    execution_date = Column(DateTime(timezone=True), nullable=True)
    triggered_by_id = Column(Integer, ForeignKey("users.id"), index=True, nullable=True)
    external_trigger_id = Column(String(255), nullable=True)
    note = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    workflow = relationship("WorkflowModel", back_populates="workflow_runs")
    triggered_by = relationship("UserModel")
