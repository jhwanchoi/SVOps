from fastapi import APIRouter

from app.presentation.api import users, datasets, tasks, workflows, auth, notifications
from app.presentation.websocket import endpoints as websocket_endpoints

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(datasets.router)
api_router.include_router(tasks.router)
api_router.include_router(workflows.router)
api_router.include_router(notifications.router)
api_router.include_router(websocket_endpoints.router)


@api_router.get("/")
async def root():
    return {"message": "SVOps API", "version": "1.0.0"}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}
