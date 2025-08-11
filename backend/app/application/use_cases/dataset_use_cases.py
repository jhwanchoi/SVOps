from typing import List, Optional
from dataclasses import dataclass

from app.domain.entities import Dataset
from app.domain.repositories import UnitOfWork
from app.domain.value_objects import DatasetId, UserId, DatasetPath
from app.shared.exceptions import EntityNotFound, EntityAlreadyExists
from app.shared.types import RecordingType


@dataclass
class CreateDatasetCommand:
    name: str
    description: Optional[str]
    path: str
    data_type: RecordingType
    gt_path: Optional[str] = None
    created_by_id: Optional[int] = None


@dataclass
class UpdateDatasetCommand:
    dataset_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    path: Optional[str] = None
    data_type: Optional[RecordingType] = None
    gt_path: Optional[str] = None


class DatasetUseCases:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def create_dataset(self, command: CreateDatasetCommand) -> Dataset:
        async with self.uow:
            # Check if dataset name already exists
            existing_dataset = await self.uow.datasets.get_by_name(command.name)
            if existing_dataset:
                raise EntityAlreadyExists("Dataset", "name", command.name)
            
            # Validate creator exists if provided
            creator_id = None
            if command.created_by_id:
                creator = await self.uow.users.get_by_id(UserId(command.created_by_id))
                if not creator:
                    raise EntityNotFound("User", str(command.created_by_id))
                creator_id = UserId(command.created_by_id)
            
            dataset = Dataset(
                id=None,
                name=command.name,
                description=command.description,
                paths=DatasetPath(path=command.path, gt_path=command.gt_path),
                data_type=command.data_type,
                created_by=creator_id,
            )
            
            created_dataset = await self.uow.datasets.create(dataset)
            await self.uow.commit()
            return created_dataset
    
    async def get_dataset_by_id(self, dataset_id: int) -> Dataset:
        async with self.uow:
            dataset = await self.uow.datasets.get_by_id(DatasetId(dataset_id))
            if not dataset:
                raise EntityNotFound("Dataset", str(dataset_id))
            return dataset
    
    async def get_dataset_by_name(self, name: str) -> Optional[Dataset]:
        async with self.uow:
            return await self.uow.datasets.get_by_name(name)
    
    async def update_dataset(self, command: UpdateDatasetCommand) -> Dataset:
        async with self.uow:
            dataset = await self.uow.datasets.get_by_id(DatasetId(command.dataset_id))
            if not dataset:
                raise EntityNotFound("Dataset", str(command.dataset_id))
            
            # Check for name conflicts if name is being changed
            if command.name and command.name != dataset.name:
                existing_dataset = await self.uow.datasets.get_by_name(command.name)
                if existing_dataset:
                    raise EntityAlreadyExists("Dataset", "name", command.name)
                dataset.name = command.name
            
            if command.description is not None:
                dataset.description = command.description
            
            if command.path or command.gt_path is not None:
                new_path = command.path or dataset.paths.path
                new_gt_path = command.gt_path if command.gt_path is not None else dataset.paths.gt_path
                dataset.paths = DatasetPath(path=new_path, gt_path=new_gt_path)
            
            if command.data_type:
                dataset.data_type = command.data_type
            
            updated_dataset = await self.uow.datasets.update(dataset)
            await self.uow.commit()
            return updated_dataset
    
    async def delete_dataset(self, dataset_id: int) -> bool:
        async with self.uow:
            dataset = await self.uow.datasets.get_by_id(DatasetId(dataset_id))
            if not dataset:
                raise EntityNotFound("Dataset", str(dataset_id))
            
            result = await self.uow.datasets.delete(DatasetId(dataset_id))
            await self.uow.commit()
            return result
    
    async def list_datasets(self, skip: int = 0, limit: int = 100) -> List[Dataset]:
        async with self.uow:
            return await self.uow.datasets.list_all(skip=skip, limit=limit)
    
    async def list_datasets_by_type(self, data_type: RecordingType, skip: int = 0, limit: int = 100) -> List[Dataset]:
        async with self.uow:
            return await self.uow.datasets.list_by_type(data_type, skip=skip, limit=limit)
    
    async def list_datasets_by_creator(self, creator_id: int, skip: int = 0, limit: int = 100) -> List[Dataset]:
        async with self.uow:
            return await self.uow.datasets.list_by_creator(UserId(creator_id), skip=skip, limit=limit)