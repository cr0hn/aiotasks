"""Rate limiting and throttling for AioTasks.

Provides rate limiting functionality to control task execution rates,
protecting external APIs and system resources.
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

log = logging.getLogger("aiotasks.rate_limit")


@dataclass
class RateLimit:
    """Rate limit configuration.

    Attributes:
        limit: Maximum number of executions
        period: Time period in seconds
        burst: Allow burst up to this many tasks (default: same as limit)
    """

    limit: int
    period: float
    burst: int | None = None

    def __post_init__(self) -> None:
        """Initialize burst if not set."""
        if self.burst is None:
            self.burst = self.limit

    @classmethod
    def parse(cls, rate_string: str) -> RateLimit:
        """Parse rate limit string.

        Formats:
            - '10/s' - 10 per second
            - '100/m' - 100 per minute
            - '1000/h' - 1000 per hour
            - '10000/d' - 10000 per day

        Args:
            rate_string: Rate limit string

        Returns:
            RateLimit instance

        Raises:
            ValueError: If format is invalid

        Examples:
            >>> RateLimit.parse('10/s')
            RateLimit(limit=10, period=1.0)
            >>> RateLimit.parse('100/m')
            RateLimit(limit=100, period=60.0)
        """
        pattern = r"^(\d+)/([smhd])$"
        match = re.match(pattern, rate_string.lower())

        if not match:
            msg = f"Invalid rate limit format: {rate_string}. Expected format: '10/s', '100/m', '1000/h', or '10000/d'"
            raise ValueError(msg)

        limit = int(match.group(1))
        unit = match.group(2)

        # Convert to seconds
        periods = {
            "s": 1.0,  # second
            "m": 60.0,  # minute
            "h": 3600.0,  # hour
            "d": 86400.0,  # day
        }

        period = periods[unit]

        return cls(limit=limit, period=period)

    def __str__(self) -> str:
        """String representation."""
        if self.period == 1.0:
            return f"{self.limit}/s"
        if self.period == 60.0:
            return f"{self.limit}/m"
        if self.period == 3600.0:
            return f"{self.limit}/h"
        if self.period == 86400.0:
            return f"{self.limit}/d"
        return f"{self.limit}/{self.period}s"


class RateLimiter:
    """Base rate limiter interface."""

    async def acquire(self, key: str, rate_limit: RateLimit) -> bool:
        """Acquire permission to execute.

        Args:
            key: Unique key for this rate limit (e.g., task name)
            rate_limit: Rate limit configuration

        Returns:
            True if allowed, False if rate limited
        """
        raise NotImplementedError

    async def wait_for_slot(
        self, key: str, rate_limit: RateLimit, timeout: float | None = None
    ) -> bool:
        """Wait until a slot is available.

        Args:
            key: Unique key for this rate limit
            rate_limit: Rate limit configuration
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if acquired, False if timed out
        """
        raise NotImplementedError

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key to reset
        """
        raise NotImplementedError


@dataclass
class TokenBucket:
    """Token bucket for rate limiting.

    Implements the token bucket algorithm for smooth rate limiting.
    """

    capacity: int
    refill_rate: float  # tokens per second
    tokens: float = field(init=False)
    last_update: float = field(init=False)

    def __post_init__(self) -> None:
        """Initialize tokens and timestamp."""
        self.tokens = float(self.capacity)
        self.last_update = time.time()

    def refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update

        # Calculate new tokens
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + new_tokens)
        self.last_update = now

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were consumed, False if insufficient tokens
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def time_until_available(self, tokens: int = 1) -> float:
        """Calculate time until tokens will be available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Time in seconds until tokens available (0 if already available)
        """
        self.refill()

        if self.tokens >= tokens:
            return 0.0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter using token bucket algorithm.

    Fast and simple, but not shared across processes.
    """

    def __init__(self) -> None:
        """Initialize memory rate limiter."""
        self._buckets: dict[str, TokenBucket] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def _get_bucket(self, key: str, rate_limit: RateLimit) -> TokenBucket:
        """Get or create token bucket for key.

        Args:
            key: Rate limit key
            rate_limit: Rate limit configuration

        Returns:
            TokenBucket instance
        """
        if key not in self._buckets:
            # Calculate refill rate (tokens per second)
            refill_rate = rate_limit.limit / rate_limit.period
            capacity = rate_limit.burst or rate_limit.limit

            self._buckets[key] = TokenBucket(
                capacity=capacity,
                refill_rate=refill_rate,
            )

        return self._buckets[key]

    async def acquire(self, key: str, rate_limit: RateLimit) -> bool:
        """Acquire permission to execute.

        Args:
            key: Unique key for this rate limit
            rate_limit: Rate limit configuration

        Returns:
            True if allowed, False if rate limited
        """
        async with self._locks[key]:
            bucket = self._get_bucket(key, rate_limit)
            return bucket.consume()

    async def wait_for_slot(
        self, key: str, rate_limit: RateLimit, timeout: float | None = None
    ) -> bool:
        """Wait until a slot is available.

        Args:
            key: Unique key for this rate limit
            rate_limit: Rate limit configuration
            timeout: Maximum time to wait

        Returns:
            True if acquired, False if timed out
        """
        start_time = time.time()

        while True:
            # Try to acquire
            if await self.acquire(key, rate_limit):
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # Calculate wait time
            async with self._locks[key]:
                bucket = self._get_bucket(key, rate_limit)
                wait_time = bucket.time_until_available()

            # Apply timeout if set
            if timeout is not None:
                remaining = timeout - (time.time() - start_time)
                wait_time = min(wait_time, remaining)

            # Wait and retry
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            else:
                # Small delay to prevent tight loop
                await asyncio.sleep(0.01)

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key to reset
        """
        async with self._locks[key]:
            if key in self._buckets:
                del self._buckets[key]


class RedisRateLimiter(RateLimiter):
    """Redis-based rate limiter using sliding window.

    Distributed rate limiting across multiple processes/machines.
    """

    def __init__(self, redis_url: str = "redis://localhost:6379/0") -> None:
        """Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self._redis: Any = None

    async def _get_redis(self) -> Any:
        """Get Redis connection.

        Returns:
            Redis connection
        """
        if self._redis is None:
            try:
                import redis.asyncio as redis

                self._redis = await redis.from_url(self.redis_url)
            except ImportError:
                msg = "redis package not installed. Install with: pip install aiotasks[redis]"
                raise ImportError(msg) from None

        return self._redis

    async def acquire(self, key: str, rate_limit: RateLimit) -> bool:
        """Acquire permission using sliding window algorithm.

        Args:
            key: Unique key for this rate limit
            rate_limit: Rate limit configuration

        Returns:
            True if allowed, False if rate limited
        """
        redis = await self._get_redis()
        now = time.time()
        window_start = now - rate_limit.period

        # Build Redis key
        redis_key = f"ratelimit:{key}"

        # Use Redis pipeline for atomic operations
        pipe = redis.pipeline()

        # Remove old entries outside the window
        pipe.zremrangebyscore(redis_key, "-inf", window_start)

        # Count current entries in window
        pipe.zcard(redis_key)

        # Execute pipeline
        results = await pipe.execute()
        current_count = results[1]

        # Check if under limit
        if current_count < rate_limit.limit:
            # Add new entry with current timestamp
            await redis.zadd(redis_key, {str(now): now})
            await redis.expire(redis_key, int(rate_limit.period) + 1)
            return True

        return False

    async def wait_for_slot(
        self, key: str, rate_limit: RateLimit, timeout: float | None = None
    ) -> bool:
        """Wait until a slot is available.

        Args:
            key: Unique key for this rate limit
            rate_limit: Rate limit configuration
            timeout: Maximum time to wait

        Returns:
            True if acquired, False if timed out
        """
        start_time = time.time()

        while True:
            # Try to acquire
            if await self.acquire(key, rate_limit):
                return True

            # Check timeout
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    return False

            # Calculate wait time (estimate)
            wait_time = rate_limit.period / rate_limit.limit

            # Apply timeout if set
            if timeout is not None:
                remaining = timeout - (time.time() - start_time)
                wait_time = min(wait_time, remaining)

            # Wait and retry
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            else:
                await asyncio.sleep(0.01)

    async def reset(self, key: str) -> None:
        """Reset rate limit for a key.

        Args:
            key: Rate limit key to reset
        """
        redis = await self._get_redis()
        redis_key = f"ratelimit:{key}"
        await redis.delete(redis_key)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


def build_rate_limiter(backend: str = "memory", **kwargs: Any) -> RateLimiter:
    """Build rate limiter from backend type.

    Args:
        backend: Backend type ('memory' or 'redis')
        **kwargs: Additional backend-specific arguments

    Returns:
        RateLimiter instance

    Examples:
        >>> limiter = build_rate_limiter('memory')
        >>> limiter = build_rate_limiter('redis', redis_url='redis://localhost:6379/1')
    """
    if backend == "memory":
        return MemoryRateLimiter()
    if backend == "redis":
        redis_url = kwargs.get("redis_url", "redis://localhost:6379/0")
        return RedisRateLimiter(redis_url=redis_url)
    msg = f"Unknown rate limiter backend: {backend}"
    raise ValueError(msg)


class RateLimitedTask:
    """Wrapper for rate-limited task execution."""

    def __init__(
        self,
        task_func: Callable,
        rate_limit: str | RateLimit,
        limiter: RateLimiter | None = None,
        wait: bool = True,
        timeout: float | None = None,
    ) -> None:
        """Initialize rate-limited task.

        Args:
            task_func: Task function to wrap
            rate_limit: Rate limit (string or RateLimit object)
            limiter: Rate limiter instance (default: memory limiter)
            wait: Wait for slot if rate limited (default: True)
            timeout: Maximum wait time (default: None = wait forever)
        """
        self.task_func = task_func
        self.rate_limit = RateLimit.parse(rate_limit) if isinstance(rate_limit, str) else rate_limit
        self.limiter = limiter or MemoryRateLimiter()
        self.wait = wait
        self.timeout = timeout

        # Use function name as rate limit key
        self.key = getattr(task_func, "__name__", "unknown")

    async def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Execute task with rate limiting.

        Args:
            *args: Positional arguments for task
            **kwargs: Keyword arguments for task

        Returns:
            Task result

        Raises:
            RuntimeError: If rate limited and wait=False
        """
        if self.wait:
            # Wait for slot
            acquired = await self.limiter.wait_for_slot(self.key, self.rate_limit, self.timeout)
            if not acquired:
                msg = f"Rate limit timeout for task '{self.key}'"
                raise RuntimeError(msg)
        # Try to acquire without waiting
        elif not await self.limiter.acquire(self.key, self.rate_limit):
            msg = f"Rate limited: {self.key} (max {self.rate_limit})"
            raise RuntimeError(msg)

        # Execute task
        return await self.task_func(*args, **kwargs)


def rate_limit(
    limit: str | RateLimit,
    backend: str = "memory",
    wait: bool = True,
    timeout: float | None = None,
    **backend_kwargs: Any,
) -> Callable:
    """Decorator to add rate limiting to tasks.

    Args:
        limit: Rate limit ('10/s', '100/m', etc.)
        backend: Rate limiter backend ('memory' or 'redis')
        wait: Wait for slot if rate limited
        timeout: Maximum wait time
        **backend_kwargs: Additional backend arguments

    Returns:
        Decorated function with rate limiting

    Examples:
        >>> @rate_limit('10/s')
        >>> async def send_email(to: str):
        ...     pass
        >>>
        >>> @rate_limit('100/m', backend='redis')
        >>> async def api_call():
        ...     pass
    """
    limiter = build_rate_limiter(backend, **backend_kwargs)

    def decorator(func: Callable) -> RateLimitedTask:
        return RateLimitedTask(
            task_func=func,
            rate_limit=limit,
            limiter=limiter,
            wait=wait,
            timeout=timeout,
        )

    return decorator
