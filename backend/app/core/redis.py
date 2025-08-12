import redis.asyncio as redis
from typing import Optional
import json
import logging

from app.core.config import settings
from app.core.retry import with_retry, REDIS_RETRY, redis_circuit_breaker

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self):
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        try:
            self._redis = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
            )

            # Test connection
            await self._redis.ping()
            logger.info("Redis connected successfully")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            logger.info("Redis disconnected")

    @property
    def redis(self) -> redis.Redis:
        if not self._redis:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._redis

    @with_retry(REDIS_RETRY)
    @redis_circuit_breaker
    async def publish(self, channel: str, message: dict) -> None:
        """Publish message to Redis channel"""
        try:
            message_str = json.dumps(message)
            await self.redis.publish(channel, message_str)
            logger.debug(f"Published to {channel}: {message}")
        except Exception as e:
            logger.error(f"Failed to publish to {channel}: {e}")
            raise

    async def subscribe(self, channel: str):
        """Subscribe to Redis channel"""
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(channel)
            logger.info(f"Subscribed to channel: {channel}")
            return pubsub
        except Exception as e:
            logger.error(f"Failed to subscribe to {channel}: {e}")
            raise

    async def set_cache(self, key: str, value: dict, ttl: int = 3600) -> None:
        """Set cached value with TTL"""
        try:
            value_str = json.dumps(value)
            await self.redis.setex(key, ttl, value_str)
        except Exception as e:
            logger.error(f"Failed to set cache {key}: {e}")
            raise

    async def get_cache(self, key: str) -> Optional[dict]:
        """Get cached value"""
        try:
            value_str = await self.redis.get(key)
            if value_str:
                return json.loads(value_str)
            return None
        except Exception as e:
            logger.error(f"Failed to get cache {key}: {e}")
            return None

    async def delete_cache(self, key: str) -> None:
        """Delete cached value"""
        try:
            await self.redis.delete(key)
        except Exception as e:
            logger.error(f"Failed to delete cache {key}: {e}")
            raise


# Global Redis client instance
redis_client = RedisClient()


async def get_redis() -> RedisClient:
    """Dependency to get Redis client"""
    return redis_client
