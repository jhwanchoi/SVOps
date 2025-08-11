from fastapi import APIRouter

from app.presentation.api import users, datasets, tasks

api_router = APIRouter()

api_router.include_router(users.router)
api_router.include_router(datasets.router)
api_router.include_router(tasks.router)

@api_router.get("/")
async def root():
    return {"message": "SVOps API", "version": "1.0.0"}

@api_router.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}