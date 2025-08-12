from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domain.entities import Dataset
from app.domain.repositories import DatasetRepository
from app.domain.value_objects import DatasetId, UserId, DatasetPath
from app.infrastructure.database.models import DatasetModel
from app.shared.exceptions import EntityNotFound
from app.shared.types import RecordingType


class SQLAlchemyDatasetRepository(DatasetRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, model: DatasetModel) -> Dataset:
        return Dataset(
            id=DatasetId(model.id) if model.id else None,
            name=model.name,
            description=model.description,
            paths=DatasetPath(path=model.path, gt_path=model.gt_path),
            data_type=RecordingType(model.data_type),
            created_at=model.created_at,
            updated_at=model.updated_at,
            created_by=UserId(model.created_by_id) if model.created_by_id else None,
        )

    def _to_model(self, domain: Dataset) -> DatasetModel:
        model = DatasetModel(
            name=domain.name,
            description=domain.description,
            path=domain.paths.path,
            gt_path=domain.paths.gt_path,
            data_type=domain.data_type.value,
            created_by_id=domain.created_by.value if domain.created_by else None,
        )
        if domain.id:
            model.id = domain.id.value
        return model

    async def create(self, dataset: Dataset) -> Dataset:
        model = self._to_model(dataset)
        self.session.add(model)
        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def get_by_id(self, dataset_id: DatasetId) -> Optional[Dataset]:
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_id.value)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_name(self, name: str) -> Optional[Dataset]:
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.name == name)
        )
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def list_all(self, skip: int = 0, limit: int = 100) -> List[Dataset]:
        result = await self.session.execute(
            select(DatasetModel)
            .offset(skip)
            .limit(limit)
            .order_by(DatasetModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_type(
        self, data_type: RecordingType, skip: int = 0, limit: int = 100
    ) -> List[Dataset]:
        result = await self.session.execute(
            select(DatasetModel)
            .where(DatasetModel.data_type == data_type.value)
            .offset(skip)
            .limit(limit)
            .order_by(DatasetModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def list_by_creator(
        self, creator_id: UserId, skip: int = 0, limit: int = 100
    ) -> List[Dataset]:
        result = await self.session.execute(
            select(DatasetModel)
            .where(DatasetModel.created_by_id == creator_id.value)
            .offset(skip)
            .limit(limit)
            .order_by(DatasetModel.created_at.desc())
        )
        models = result.scalars().all()
        return [self._to_domain(model) for model in models]

    async def update(self, dataset: Dataset) -> Dataset:
        if not dataset.id:
            raise ValueError("Cannot update dataset without ID")

        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset.id.value)
        )
        model = result.scalar_one_or_none()
        if not model:
            raise EntityNotFound("Dataset", str(dataset.id.value))

        model.name = dataset.name
        model.description = dataset.description
        model.path = dataset.paths.path
        model.gt_path = dataset.paths.gt_path
        model.data_type = dataset.data_type.value

        await self.session.flush()
        await self.session.refresh(model)
        return self._to_domain(model)

    async def delete(self, dataset_id: DatasetId) -> bool:
        result = await self.session.execute(
            select(DatasetModel).where(DatasetModel.id == dataset_id.value)
        )
        model = result.scalar_one_or_none()
        if not model:
            return False

        await self.session.delete(model)
        return True
