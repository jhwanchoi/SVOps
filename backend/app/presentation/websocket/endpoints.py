import json
import logging
from typing import Optional
from fastapi import (
    APIRouter,
    WebSocket,
    WebSocketDisconnect,
    Depends,
    Query,
    HTTPException,
    status,
)
from datetime import datetime

from app.presentation.websocket.connection_manager import manager
from app.application.services.event_service import get_event_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def websocket_global_endpoint(websocket: WebSocket):
    """Global WebSocket endpoint for all events"""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(websocket)


@router.websocket("/ws/user/{user_id}")
async def websocket_user_endpoint(websocket: WebSocket, user_id: int):
    """User-specific WebSocket endpoint"""
    await manager.connect(websocket, user_id=user_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(websocket, message, user_id=user_id)
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}: {e}")
        await manager.disconnect(websocket)


@router.websocket("/ws/workflow/{workflow_id}")
async def websocket_workflow_endpoint(websocket: WebSocket, workflow_id: str):
    """Workflow-specific WebSocket endpoint"""
    await manager.connect(websocket, workflow_id=workflow_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(
                    websocket, message, workflow_id=workflow_id
                )
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for workflow {workflow_id}: {e}")
        await manager.disconnect(websocket)


@router.websocket("/ws/user/{user_id}/workflow/{workflow_id}")
async def websocket_user_workflow_endpoint(
    websocket: WebSocket, user_id: int, workflow_id: str
):
    """User and workflow-specific WebSocket endpoint"""
    await manager.connect(websocket, user_id=user_id, workflow_id=workflow_id)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                await handle_websocket_message(
                    websocket, message, user_id=user_id, workflow_id=workflow_id
                )
            except json.JSONDecodeError:
                await manager.send_personal_message(
                    {"error": "Invalid JSON format"}, websocket
                )
    except WebSocketDisconnect:
        await manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for user {user_id}, workflow {workflow_id}: {e}")
        await manager.disconnect(websocket)


async def handle_websocket_message(
    websocket: WebSocket,
    message: dict,
    user_id: Optional[int] = None,
    workflow_id: Optional[str] = None,
):
    """Handle incoming WebSocket messages from clients"""
    try:
        message_type = message.get("type")

        if message_type == "ping":
            # Respond to ping with pong
            await manager.send_personal_message(
                {"type": "pong", "timestamp": datetime.now().isoformat()}, websocket
            )

        elif message_type == "subscribe":
            # Handle subscription requests
            await handle_subscription_request(websocket, message, user_id, workflow_id)

        elif message_type == "unsubscribe":
            # Handle unsubscription requests
            await handle_unsubscription_request(
                websocket, message, user_id, workflow_id
            )

        elif message_type == "get_status":
            # Handle status requests
            await handle_status_request(websocket, message, user_id, workflow_id)

        else:
            await manager.send_personal_message(
                {"error": f"Unknown message type: {message_type}"}, websocket
            )

    except Exception as e:
        logger.error(f"Error handling WebSocket message: {e}")
        await manager.send_personal_message(
            {"error": "Internal server error"}, websocket
        )


async def handle_subscription_request(
    websocket: WebSocket,
    message: dict,
    user_id: Optional[int],
    workflow_id: Optional[str],
):
    """Handle subscription requests from clients"""
    subscription_type = message.get("subscription_type")
    target = message.get("target")

    if subscription_type == "workflow" and target:
        # Add to workflow-specific subscriptions
        if target not in manager.active_connections["workflows"]:
            manager.active_connections["workflows"][target] = set()
        manager.active_connections["workflows"][target].add(websocket)

        await manager.send_personal_message(
            {
                "type": "subscription_confirmed",
                "subscription_type": "workflow",
                "target": target,
            },
            websocket,
        )

    elif subscription_type == "user" and target:
        # Add to user-specific subscriptions
        target_user_id = int(target)
        if target_user_id not in manager.active_connections["users"]:
            manager.active_connections["users"][target_user_id] = set()
        manager.active_connections["users"][target_user_id].add(websocket)

        await manager.send_personal_message(
            {
                "type": "subscription_confirmed",
                "subscription_type": "user",
                "target": target,
            },
            websocket,
        )
    else:
        await manager.send_personal_message(
            {"error": "Invalid subscription request"}, websocket
        )


async def handle_unsubscription_request(
    websocket: WebSocket,
    message: dict,
    user_id: Optional[int],
    workflow_id: Optional[str],
):
    """Handle unsubscription requests from clients"""
    subscription_type = message.get("subscription_type")
    target = message.get("target")

    if subscription_type == "workflow" and target:
        if target in manager.active_connections["workflows"]:
            manager.active_connections["workflows"][target].discard(websocket)
            if not manager.active_connections["workflows"][target]:
                del manager.active_connections["workflows"][target]

        await manager.send_personal_message(
            {
                "type": "unsubscription_confirmed",
                "subscription_type": "workflow",
                "target": target,
            },
            websocket,
        )

    elif subscription_type == "user" and target:
        target_user_id = int(target)
        if target_user_id in manager.active_connections["users"]:
            manager.active_connections["users"][target_user_id].discard(websocket)
            if not manager.active_connections["users"][target_user_id]:
                del manager.active_connections["users"][target_user_id]

        await manager.send_personal_message(
            {
                "type": "unsubscription_confirmed",
                "subscription_type": "user",
                "target": target,
            },
            websocket,
        )


async def handle_status_request(
    websocket: WebSocket,
    message: dict,
    user_id: Optional[int],
    workflow_id: Optional[str],
):
    """Handle status requests from clients"""
    request_type = message.get("request_type")

    if request_type == "workflow_status":
        target_workflow_id = message.get("workflow_id")
        target_run_id = message.get("run_id")

        if target_workflow_id and target_run_id:
            # Get cached status from Redis
            event_service = get_event_service()
            cached_status = await event_service.get_cached_workflow_status(
                target_workflow_id, target_run_id
            )

            await manager.send_personal_message(
                {
                    "type": "status_response",
                    "request_type": "workflow_status",
                    "workflow_id": target_workflow_id,
                    "run_id": target_run_id,
                    "status": cached_status,
                },
                websocket,
            )
        else:
            await manager.send_personal_message(
                {"error": "Missing workflow_id or run_id for status request"}, websocket
            )

    elif request_type == "connection_stats":
        stats = manager.get_connection_stats()
        await manager.send_personal_message(
            {
                "type": "status_response",
                "request_type": "connection_stats",
                "stats": stats,
            },
            websocket,
        )
    else:
        await manager.send_personal_message(
            {"error": f"Unknown status request type: {request_type}"}, websocket
        )


# HTTP endpoint to get WebSocket connection statistics
@router.get("/ws/stats")
async def get_websocket_stats():
    """Get WebSocket connection statistics"""
    return manager.get_connection_stats()


