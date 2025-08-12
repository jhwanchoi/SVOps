import asyncio
import json
import logging
from typing import Dict, List, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from app.application.services.event_service import EventService, get_event_service
from app.core.redis import get_redis

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(self):
        # Store active connections grouped by subscription type
        self.active_connections: Dict[str, Set[WebSocket]] = {
            "global": set(),
            "workflows": {},  # workflow_id -> set of websockets
            "users": {},  # user_id -> set of websockets
        }
        self.connection_info: Dict[WebSocket, Dict[str, any]] = {}
        self.event_service: Optional[EventService] = None
        self.redis_tasks: Dict[str, asyncio.Task] = {}

    async def connect(
        self,
        websocket: WebSocket,
        user_id: Optional[int] = None,
        workflow_id: Optional[str] = None,
    ):
        """Accept websocket connection and set up subscriptions"""
        await websocket.accept()

        # Store connection info
        connection_info = {
            "user_id": user_id,
            "workflow_id": workflow_id,
            "connected_at": datetime.now(),
            "subscriptions": [],
        }
        self.connection_info[websocket] = connection_info

        # Add to global connections
        self.active_connections["global"].add(websocket)
        connection_info["subscriptions"].append("global")

        # Add to user-specific connections
        if user_id:
            if user_id not in self.active_connections["users"]:
                self.active_connections["users"][user_id] = set()
            self.active_connections["users"][user_id].add(websocket)
            connection_info["subscriptions"].append(f"user:{user_id}")

        # Add to workflow-specific connections
        if workflow_id:
            if workflow_id not in self.active_connections["workflows"]:
                self.active_connections["workflows"][workflow_id] = set()
            self.active_connections["workflows"][workflow_id].add(websocket)
            connection_info["subscriptions"].append(f"workflow:{workflow_id}")

        # Start Redis subscription tasks
        await self._start_redis_subscriptions(websocket, user_id, workflow_id)

        logger.info(
            f"WebSocket connected: user_id={user_id}, workflow_id={workflow_id}"
        )

    async def disconnect(self, websocket: WebSocket):
        """Remove websocket connection and clean up subscriptions"""
        connection_info = self.connection_info.get(websocket, {})
        user_id = connection_info.get("user_id")
        workflow_id = connection_info.get("workflow_id")

        # Remove from global connections
        self.active_connections["global"].discard(websocket)

        # Remove from user-specific connections
        if user_id and user_id in self.active_connections["users"]:
            self.active_connections["users"][user_id].discard(websocket)
            if not self.active_connections["users"][user_id]:
                del self.active_connections["users"][user_id]

        # Remove from workflow-specific connections
        if workflow_id and workflow_id in self.active_connections["workflows"]:
            self.active_connections["workflows"][workflow_id].discard(websocket)
            if not self.active_connections["workflows"][workflow_id]:
                del self.active_connections["workflows"][workflow_id]

        # Stop Redis subscription tasks
        await self._stop_redis_subscriptions(websocket)

        # Clean up connection info
        if websocket in self.connection_info:
            del self.connection_info[websocket]

        logger.info(
            f"WebSocket disconnected: user_id={user_id}, workflow_id={workflow_id}"
        )

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific websocket"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
            await self.disconnect(websocket)

    async def broadcast_to_global(self, message: dict):
        """Broadcast message to all global subscribers"""
        await self._broadcast_to_connections(self.active_connections["global"], message)

    async def broadcast_to_user(self, user_id: int, message: dict):
        """Broadcast message to specific user's connections"""
        user_connections = self.active_connections["users"].get(user_id, set())
        await self._broadcast_to_connections(user_connections, message)

    async def broadcast_to_workflow(self, workflow_id: str, message: dict):
        """Broadcast message to workflow subscribers"""
        workflow_connections = self.active_connections["workflows"].get(
            workflow_id, set()
        )
        await self._broadcast_to_connections(workflow_connections, message)

    async def _broadcast_to_connections(
        self, connections: Set[WebSocket], message: dict
    ):
        """Helper method to broadcast to a set of connections"""
        if not connections:
            return

        disconnected = []
        for connection in connections.copy():
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.append(connection)

        # Clean up disconnected connections
        for connection in disconnected:
            await self.disconnect(connection)

    async def _start_redis_subscriptions(
        self, websocket: WebSocket, user_id: Optional[int], workflow_id: Optional[str]
    ):
        """Start Redis pub/sub subscriptions for this connection"""
        if not self.event_service:
            self.event_service = get_event_service()

        # Create unique task keys for this connection
        connection_id = id(websocket)

        # Subscribe to global events
        task_key = f"global_{connection_id}"
        self.redis_tasks[task_key] = asyncio.create_task(
            self._subscribe_to_redis_channel(
                self.event_service.get_global_channel_name(), websocket
            )
        )

        # Subscribe to user events
        if user_id:
            task_key = f"user_{user_id}_{connection_id}"
            self.redis_tasks[task_key] = asyncio.create_task(
                self._subscribe_to_redis_channel(
                    self.event_service.get_user_channel_name(user_id), websocket
                )
            )

        # Subscribe to workflow events
        if workflow_id:
            task_key = f"workflow_{workflow_id}_{connection_id}"
            self.redis_tasks[task_key] = asyncio.create_task(
                self._subscribe_to_redis_channel(
                    self.event_service.get_channel_name(workflow_id), websocket
                )
            )

    async def _stop_redis_subscriptions(self, websocket: WebSocket):
        """Stop Redis pub/sub subscriptions for this connection"""
        connection_id = id(websocket)

        # Find and cancel all tasks for this connection
        tasks_to_cancel = [
            task_key
            for task_key in self.redis_tasks.keys()
            if task_key.endswith(f"_{connection_id}")
        ]

        for task_key in tasks_to_cancel:
            task = self.redis_tasks[task_key]
            if not task.done():
                task.cancel()
            del self.redis_tasks[task_key]

    async def _subscribe_to_redis_channel(self, channel: str, websocket: WebSocket):
        """Subscribe to Redis channel and forward messages to websocket"""
        try:
            redis_client = await get_redis()
            pubsub = await redis_client.subscribe(channel)

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        # Forward Redis message to WebSocket
                        data = json.loads(message["data"])
                        await self.send_personal_message(data, websocket)
                    except json.JSONDecodeError:
                        logger.error(
                            f"Invalid JSON in Redis message: {message['data']}"
                        )
                    except Exception as e:
                        logger.error(f"Error forwarding Redis message: {e}")
                        break

        except asyncio.CancelledError:
            logger.info(f"Redis subscription cancelled for channel: {channel}")
        except Exception as e:
            logger.error(f"Error in Redis subscription for channel {channel}: {e}")
        finally:
            try:
                await pubsub.unsubscribe(channel)
            except Exception:
                pass

    def get_connection_stats(self) -> Dict[str, any]:
        """Get statistics about active connections"""
        return {
            "total_connections": len(self.connection_info),
            "global_subscribers": len(self.active_connections["global"]),
            "user_subscribers": {
                user_id: len(connections)
                for user_id, connections in self.active_connections["users"].items()
            },
            "workflow_subscribers": {
                workflow_id: len(connections)
                for workflow_id, connections in self.active_connections[
                    "workflows"
                ].items()
            },
            "active_redis_tasks": len(self.redis_tasks),
        }


# Global connection manager instance
manager = ConnectionManager()
