import asyncio
import logging
import functools
from typing import Callable, Type, Union, Tuple, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RetryConfig:
    """Configuration for retry logic"""

    def __init__(
        self,
        max_attempts: int = 3,
        delay: float = 1.0,
        backoff_factor: float = 2.0,
        max_delay: float = 60.0,
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,),
    ):
        self.max_attempts = max_attempts
        self.delay = delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter
        self.exceptions = exceptions


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for retry attempt"""
    delay = config.delay * (config.backoff_factor ** (attempt - 1))
    delay = min(delay, config.max_delay)

    if config.jitter:
        import random

        delay *= 0.5 + random.random() * 0.5  # Add 0-50% jitter

    return delay


async def retry_async(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
    """Retry an async function with exponential backoff"""
    last_exception = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.debug(f"Attempt {attempt}/{config.max_attempts} for {func.__name__}")
            result = await func(*args, **kwargs)

            if attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")

            return result

        except config.exceptions as e:
            last_exception = e

            if attempt == config.max_attempts:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_attempts} attempts"
                )
                break

            delay = calculate_delay(attempt, config)
            logger.warning(
                f"Function {func.__name__} failed on attempt {attempt}, "
                f"retrying in {delay:.2f}s: {str(e)}"
            )

            await asyncio.sleep(delay)

        except Exception as e:
            # Non-retryable exception
            logger.error(
                f"Function {func.__name__} failed with non-retryable error: {str(e)}"
            )
            raise

    raise last_exception


def retry_sync(func: Callable, config: RetryConfig, *args, **kwargs) -> Any:
    """Retry a sync function with exponential backoff"""
    import time

    last_exception = None

    for attempt in range(1, config.max_attempts + 1):
        try:
            logger.debug(f"Attempt {attempt}/{config.max_attempts} for {func.__name__}")
            result = func(*args, **kwargs)

            if attempt > 1:
                logger.info(f"Function {func.__name__} succeeded on attempt {attempt}")

            return result

        except config.exceptions as e:
            last_exception = e

            if attempt == config.max_attempts:
                logger.error(
                    f"Function {func.__name__} failed after {config.max_attempts} attempts"
                )
                break

            delay = calculate_delay(attempt, config)
            logger.warning(
                f"Function {func.__name__} failed on attempt {attempt}, "
                f"retrying in {delay:.2f}s: {str(e)}"
            )

            time.sleep(delay)

        except Exception as e:
            # Non-retryable exception
            logger.error(
                f"Function {func.__name__} failed with non-retryable error: {str(e)}"
            )
            raise

    raise last_exception


def with_retry(config: RetryConfig = None):
    """Decorator for adding retry logic to functions"""
    if config is None:
        config = RetryConfig()

    def decorator(func: Callable):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                return await retry_async(func, config, *args, **kwargs)

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_sync(func, config, *args, **kwargs)

            return sync_wrapper

    return decorator


# Common retry configurations
EXTERNAL_SERVICE_RETRY = RetryConfig(
    max_attempts=3,
    delay=2.0,
    backoff_factor=2.0,
    max_delay=30.0,
    exceptions=(ConnectionError, TimeoutError, Exception),
)

DATABASE_RETRY = RetryConfig(
    max_attempts=3,
    delay=0.5,
    backoff_factor=1.5,
    max_delay=5.0,
    exceptions=(Exception,),
)

REDIS_RETRY = RetryConfig(
    max_attempts=2,
    delay=1.0,
    backoff_factor=2.0,
    max_delay=10.0,
    exceptions=(Exception,),
)


# Circuit breaker pattern
class CircuitBreaker:
    """Simple circuit breaker implementation"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: Type[Exception] = Exception,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN

    def __call__(self, func: Callable):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")

            try:
                result = await func(*args, **kwargs)
                self._on_success()
                return result
            except self.expected_exception as e:
                self._on_failure()
                raise

        return wrapper

    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time
            and datetime.now() - self.last_failure_time
            > timedelta(seconds=self.recovery_timeout)
        )

    def _on_success(self):
        self.failure_count = 0
        self.state = "CLOSED"

    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


# Usage examples and presets
airflow_circuit_breaker = CircuitBreaker(
    failure_threshold=3, recovery_timeout=30, expected_exception=Exception
)

redis_circuit_breaker = CircuitBreaker(
    failure_threshold=2, recovery_timeout=15, expected_exception=Exception
)
