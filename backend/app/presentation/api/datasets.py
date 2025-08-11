from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.application.use_cases.dataset_use_cases import DatasetUseCases, CreateDatasetCommand, UpdateDatasetCommand
from app.infrastructure.repositories.unit_of_work import SQLAlchemyUnitOfWork
from app.presentation.schemas.dataset_schemas import DatasetCreate, DatasetUpdate, DatasetResponse
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists
from app.shared.types import RecordingType

router = APIRouter(prefix="/datasets", tags=["datasets"])


def get_dataset_use_cases(db: AsyncSession = Depends(get_db)) -> DatasetUseCases:
    uow = SQLAlchemyUnitOfWork(db)
    return DatasetUseCases(uow)


@router.post("/", response_model=DatasetResponse, status_code=status.HTTP_201_CREATED)
async def create_dataset(
    dataset_data: DatasetCreate,
    use_cases: DatasetUseCases = Depends(get_dataset_use_cases)
):
    try:
        command = CreateDatasetCommand(
            name=dataset_data.name,
            description=dataset_data.description,
            path=dataset_data.path,
            data_type=dataset_data.data_type,
            gt_path=dataset_data.gt_path,
            created_by_id=dataset_data.created_by_id
        )
        dataset = await use_cases.create_dataset(command)
        return DatasetResponse(
            id=dataset.id.value,
            name=dataset.name,
            description=dataset.description,
            path=dataset.paths.path,
            data_type=dataset.data_type,
            gt_path=dataset.paths.gt_path,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            created_by_id=dataset.created_by.value if dataset.created_by else None
        )
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset with {e.field}='{e.value}' already exists"
        )
    except EntityNotFound as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=e.args[0]
        )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(
    dataset_id: int,
    use_cases: DatasetUseCases = Depends(get_dataset_use_cases)
):
    try:
        dataset = await use_cases.get_dataset_by_id(dataset_id)
        return DatasetResponse(
            id=dataset.id.value,
            name=dataset.name,
            description=dataset.description,
            path=dataset.paths.path,
            data_type=dataset.data_type,
            gt_path=dataset.paths.gt_path,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            created_by_id=dataset.created_by.value if dataset.created_by else None
        )
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )


@router.put("/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: int,
    dataset_data: DatasetUpdate,
    use_cases: DatasetUseCases = Depends(get_dataset_use_cases)
):
    try:
        command = UpdateDatasetCommand(
            dataset_id=dataset_id,
            name=dataset_data.name,
            description=dataset_data.description,
            path=dataset_data.path,
            data_type=dataset_data.data_type,
            gt_path=dataset_data.gt_path
        )
        dataset = await use_cases.update_dataset(command)
        return DatasetResponse(
            id=dataset.id.value,
            name=dataset.name,
            description=dataset.description,
            path=dataset.paths.path,
            data_type=dataset.data_type,
            gt_path=dataset.paths.gt_path,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            created_by_id=dataset.created_by.value if dataset.created_by else None
        )
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )
    except EntityAlreadyExists as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dataset with {e.field}='{e.value}' already exists"
        )


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(
    dataset_id: int,
    use_cases: DatasetUseCases = Depends(get_dataset_use_cases)
):
    try:
        await use_cases.delete_dataset(dataset_id)
    except EntityNotFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found"
        )


@router.get("/", response_model=List[DatasetResponse])
async def list_datasets(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    data_type: Optional[RecordingType] = None,
    creator_id: Optional[int] = None,
    use_cases: DatasetUseCases = Depends(get_dataset_use_cases)
):
    if data_type:
        datasets = await use_cases.list_datasets_by_type(data_type, skip=skip, limit=limit)
    elif creator_id:
        datasets = await use_cases.list_datasets_by_creator(creator_id, skip=skip, limit=limit)
    else:
        datasets = await use_cases.list_datasets(skip=skip, limit=limit)
    
    return [
        DatasetResponse(
            id=dataset.id.value,
            name=dataset.name,
            description=dataset.description,
            path=dataset.paths.path,
            data_type=dataset.data_type,
            gt_path=dataset.paths.gt_path,
            created_at=dataset.created_at,
            updated_at=dataset.updated_at,
            created_by_id=dataset.created_by.value if dataset.created_by else None
        )
        for dataset in datasets
    ]