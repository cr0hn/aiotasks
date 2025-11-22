"""Unit tests for rate limiting functionality.

Tests cover:
- RateLimit parsing and configuration
- Token bucket algorithm
- Memory-based rate limiter
- Redis-based rate limiter (if available)
- Rate limit decorator
- Edge cases and error handling
"""

import asyncio
import time

import pytest


@pytest.mark.asyncio
class TestRateLimitParsing:
    """Test RateLimit parsing and configuration."""

    def test_parse_per_second(self):
        """Test parsing rate limit per second."""
        from aiotasks.rate_limit import RateLimit

        rate = RateLimit.parse("10/s")

        assert rate.limit == 10
        assert rate.period == 1.0
        assert rate.burst == 10

    def test_parse_per_minute(self):
        """Test parsing rate limit per minute."""
        from aiotasks.rate_limit import RateLimit

        rate = RateLimit.parse("100/m")

        assert rate.limit == 100
        assert rate.period == 60.0

    def test_parse_per_hour(self):
        """Test parsing rate limit per hour."""
        from aiotasks.rate_limit import RateLimit

        rate = RateLimit.parse("1000/h")

        assert rate.limit == 1000
        assert rate.period == 3600.0

    def test_parse_per_day(self):
        """Test parsing rate limit per day."""
        from aiotasks.rate_limit import RateLimit

        rate = RateLimit.parse("10000/d")

        assert rate.limit == 10000
        assert rate.period == 86400.0

    def test_parse_invalid_format(self):
        """Test parsing invalid format raises error."""
        from aiotasks.rate_limit import RateLimit

        with pytest.raises(ValueError, match="Invalid rate limit format"):
            RateLimit.parse("invalid")

        with pytest.raises(ValueError):
            RateLimit.parse("10/x")

        with pytest.raises(ValueError):
            RateLimit.parse("abc/s")

    def test_rate_limit_string_representation(self):
        """Test string representation of rate limits."""
        from aiotasks.rate_limit import RateLimit

        assert str(RateLimit.parse("10/s")) == "10/s"
        assert str(RateLimit.parse("100/m")) == "100/m"
        assert str(RateLimit.parse("1000/h")) == "1000/h"
        assert str(RateLimit.parse("10000/d")) == "10000/d"

    def test_rate_limit_custom_burst(self):
        """Test rate limit with custom burst."""
        from aiotasks.rate_limit import RateLimit

        rate = RateLimit(limit=10, period=1.0, burst=20)

        assert rate.limit == 10
        assert rate.period == 1.0
        assert rate.burst == 20


@pytest.mark.asyncio
class TestTokenBucket:
    """Test token bucket algorithm."""

    def test_token_bucket_initialization(self):
        """Test token bucket initialization."""
        from aiotasks.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        assert bucket.capacity == 10
        assert bucket.refill_rate == 1.0
        assert bucket.tokens == 10.0  # Starts full

    def test_token_bucket_consume_success(self):
        """Test successful token consumption."""
        from aiotasks.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        assert bucket.consume(1) is True
        assert bucket.consume(5) is True
        # Should have ~4 tokens left
        assert bucket.consume(4) is True

    def test_token_bucket_consume_failure(self):
        """Test failed token consumption when insufficient."""
        from aiotasks.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=1.0)

        # Consume all tokens
        assert bucket.consume(10) is True

        # No tokens left
        assert bucket.consume(1) is False

    def test_token_bucket_refill(self):
        """Test token refill over time."""
        import time

        from aiotasks.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 per second

        # Consume all
        bucket.consume(10)
        assert bucket.consume(1) is False

        # Wait for refill
        time.sleep(0.5)  # Should refill ~5 tokens

        assert bucket.consume(4) is True  # Should succeed

    def test_token_bucket_time_until_available(self):
        """Test calculating time until tokens available."""
        from aiotasks.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=10.0)

        # Consume all
        bucket.consume(10)

        # Calculate time for 5 tokens
        wait_time = bucket.time_until_available(5)

        assert 0.4 <= wait_time <= 0.6  # ~0.5 seconds

    def test_token_bucket_max_capacity(self):
        """Test token bucket doesn't exceed capacity."""
        import time

        from aiotasks.rate_limit import TokenBucket

        bucket = TokenBucket(capacity=10, refill_rate=100.0)

        # Wait longer than needed to fill
        time.sleep(1.0)

        # Refill shouldn't exceed capacity
        bucket.refill()
        assert bucket.tokens <= 10.0


@pytest.mark.asyncio
class TestMemoryRateLimiter:
    """Test memory-based rate limiter."""

    async def test_memory_limiter_acquire_success(self):
        """Test successful acquire."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=10, period=1.0)

        # Should succeed
        assert await limiter.acquire("test_key", rate) is True

    async def test_memory_limiter_rate_limit_exceeded(self):
        """Test rate limit exceeded."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=5, period=10.0)  # 5 per 10 seconds

        # Use all 5
        for _ in range(5):
            assert await limiter.acquire("test_key", rate) is True

        # 6th should fail
        assert await limiter.acquire("test_key", rate) is False

    async def test_memory_limiter_wait_for_slot(self):
        """Test waiting for slot."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=2, period=1.0)

        # Use both slots
        await limiter.acquire("test_key", rate)
        await limiter.acquire("test_key", rate)

        # Wait for refill
        start = time.time()
        result = await limiter.wait_for_slot("test_key", rate, timeout=2.0)
        elapsed = time.time() - start

        assert result is True
        assert elapsed >= 0.4  # Had to wait for refill

    async def test_memory_limiter_wait_timeout(self):
        """Test wait timeout."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=1, period=10.0)  # Very slow refill

        # Use slot
        await limiter.acquire("test_key", rate)

        # Try to wait with short timeout
        result = await limiter.wait_for_slot("test_key", rate, timeout=0.1)

        assert result is False

    async def test_memory_limiter_reset(self):
        """Test resetting rate limit."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=2, period=10.0)

        # Use all slots
        await limiter.acquire("test_key", rate)
        await limiter.acquire("test_key", rate)

        # Reset
        await limiter.reset("test_key")

        # Should be able to acquire again
        assert await limiter.acquire("test_key", rate) is True

    async def test_memory_limiter_different_keys(self):
        """Test different keys are independent."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=1, period=10.0)

        # Use slot for key1
        await limiter.acquire("key1", rate)

        # key2 should still have slots
        assert await limiter.acquire("key2", rate) is True

    async def test_memory_limiter_concurrent_access(self):
        """Test concurrent access to same key."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=10, period=1.0)

        async def acquire_task():
            return await limiter.acquire("shared_key", rate)

        # Many concurrent acquires
        results = await asyncio.gather(*[acquire_task() for _ in range(15)])

        # Only 10 should succeed (burst limit)
        successful = sum(1 for r in results if r)
        assert successful == 10


@pytest.mark.asyncio
class TestRateLimitDecorator:
    """Test rate limit decorator."""

    async def test_rate_limit_decorator_basic(self):
        """Test basic rate limit decorator."""
        from aiotasks.rate_limit import rate_limit

        call_count = {"count": 0}

        @rate_limit("5/s")
        async def limited_func():
            call_count["count"] += 1
            return "success"

        # Call 5 times (should all succeed)
        for _ in range(5):
            result = await limited_func()
            assert result == "success"

        assert call_count["count"] == 5

    async def test_rate_limit_decorator_exceeded(self):
        """Test rate limit decorator when exceeded."""
        from aiotasks.rate_limit import rate_limit

        @rate_limit("2/s", wait=False)  # Fail immediately
        async def limited_func():
            return "success"

        # Call twice (OK)
        await limited_func()
        await limited_func()

        # Third should fail
        with pytest.raises(RuntimeError, match="Rate limited"):
            await limited_func()

    async def test_rate_limit_decorator_with_wait(self):
        """Test rate limit decorator with wait."""
        from aiotasks.rate_limit import rate_limit

        @rate_limit("3/s", wait=True)
        async def limited_func(value):
            return value * 2

        start = time.time()

        # Call 6 times - should wait for refill
        results = []
        for i in range(6):
            result = await limited_func(i)
            results.append(result)

        elapsed = time.time() - start

        assert len(results) == 6
        assert results == [0, 2, 4, 6, 8, 10]
        assert elapsed >= 0.8  # Had to wait for refill

    async def test_rate_limit_decorator_with_timeout(self):
        """Test rate limit decorator with timeout."""
        from aiotasks.rate_limit import rate_limit

        @rate_limit("1/s", wait=True, timeout=0.5)
        async def limited_func():
            return "success"

        # First call OK
        await limited_func()

        # Second call should timeout
        with pytest.raises(RuntimeError, match="timeout"):
            await limited_func()

    async def test_rate_limit_decorator_with_arguments(self):
        """Test decorated function with arguments."""
        from aiotasks.rate_limit import rate_limit

        @rate_limit("5/s")
        async def add(a, b):
            return a + b

        result = await add(2, 3)
        assert result == 5

    async def test_rate_limit_decorator_with_kwargs(self):
        """Test decorated function with keyword arguments."""
        from aiotasks.rate_limit import rate_limit

        @rate_limit("5/s")
        async def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = await greet("Alice", greeting="Hi")
        assert result == "Hi, Alice!"


@pytest.mark.asyncio
class TestBuildRateLimiter:
    """Test rate limiter builder."""

    def test_build_memory_limiter(self):
        """Test building memory rate limiter."""
        from aiotasks.rate_limit import MemoryRateLimiter, build_rate_limiter

        limiter = build_rate_limiter("memory")

        assert isinstance(limiter, MemoryRateLimiter)

    def test_build_redis_limiter(self):
        """Test building Redis rate limiter."""
        from aiotasks.rate_limit import RedisRateLimiter, build_rate_limiter

        limiter = build_rate_limiter("redis", redis_url="redis://localhost:6379/0")

        assert isinstance(limiter, RedisRateLimiter)

    def test_build_invalid_backend(self):
        """Test building with invalid backend."""
        from aiotasks.rate_limit import build_rate_limiter

        with pytest.raises(ValueError, match="Unknown rate limiter backend"):
            build_rate_limiter("invalid_backend")


@pytest.mark.asyncio
class TestRateLimitEdgeCases:
    """Test edge cases for rate limiting."""

    async def test_zero_rate_limit(self):
        """Test with zero rate limit (should allow nothing)."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=0, period=1.0)

        # Should fail immediately
        assert await limiter.acquire("test_key", rate) is False

    async def test_very_high_rate_limit(self):
        """Test with very high rate limit."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=1000000, period=1.0)

        # Should succeed easily
        for _ in range(100):
            assert await limiter.acquire("test_key", rate) is True

    async def test_very_long_period(self):
        """Test with very long period."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=1, period=86400.0)  # 1 per day

        assert await limiter.acquire("test_key", rate) is True
        assert await limiter.acquire("test_key", rate) is False

    async def test_fractional_limits(self):
        """Test with fractional rate limits."""
        from aiotasks.rate_limit import TokenBucket

        # 0.5 tokens per second = 1 token every 2 seconds
        bucket = TokenBucket(capacity=5, refill_rate=0.5)

        bucket.consume(5)  # Empty it

        # Wait 2 seconds for 1 token
        await asyncio.sleep(2.1)

        assert bucket.consume(1) is True

    async def test_multiple_burst_patterns(self):
        """Test different burst patterns."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()

        # Small burst
        rate1 = RateLimit(limit=10, period=1.0, burst=5)

        # Large burst
        rate2 = RateLimit(limit=10, period=1.0, burst=20)

        # rate1 should allow max 5 immediate calls
        for _ in range(5):
            assert await limiter.acquire("key1", rate1) is True
        assert await limiter.acquire("key1", rate1) is False

        # rate2 should allow max 20 immediate calls
        for _ in range(20):
            assert await limiter.acquire("key2", rate2) is True
        assert await limiter.acquire("key2", rate2) is False


@pytest.mark.asyncio
class TestRateLimitPerformance:
    """Test rate limiting performance."""

    async def test_high_throughput_acquire(self):
        """Test high throughput of acquire operations."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=10000, period=1.0)

        start = time.time()

        # Many rapid acquires
        for _ in range(1000):
            await limiter.acquire("test_key", rate)

        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 1.0

    async def test_concurrent_different_keys(self):
        """Test concurrent operations on different keys."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=100, period=1.0)

        async def acquire_many(key, count):
            for _ in range(count):
                await limiter.acquire(key, rate)

        start = time.time()

        # Many keys concurrently
        await asyncio.gather(*[acquire_many(f"key_{i}", 50) for i in range(10)])

        elapsed = time.time() - start

        assert elapsed < 2.0  # Should be reasonably fast

    async def test_wait_for_slot_efficiency(self):
        """Test wait_for_slot doesn't busy loop."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=5, period=1.0)

        # Use all slots
        for _ in range(5):
            await limiter.acquire("test_key", rate)

        # This should wait efficiently, not busy loop
        start = time.time()
        await limiter.wait_for_slot("test_key", rate, timeout=0.3)
        elapsed = time.time() - start

        # Should wait close to the calculated time, not loop
        assert 0.15 <= elapsed <= 0.35


@pytest.mark.asyncio
class TestRateLimitedTaskWrapper:
    """Test RateLimitedTask wrapper class."""

    async def test_rate_limited_task_basic(self):
        """Test basic RateLimitedTask usage."""
        from aiotasks.rate_limit import RateLimitedTask

        async def my_task(x):
            return x * 2

        limited_task = RateLimitedTask(task_func=my_task, rate_limit="5/s", wait=True)

        result = await limited_task(5)
        assert result == 10

    async def test_rate_limited_task_with_string_rate(self):
        """Test RateLimitedTask with string rate limit."""
        from aiotasks.rate_limit import RateLimitedTask

        async def my_task():
            return "done"

        limited_task = RateLimitedTask(task_func=my_task, rate_limit="10/m", wait=False)

        result = await limited_task()
        assert result == "done"

    async def test_rate_limited_task_callable(self):
        """Test RateLimitedTask is callable."""
        from aiotasks.rate_limit import RateLimitedTask

        call_count = {"count": 0}

        async def my_task():
            call_count["count"] += 1

        limited_task = RateLimitedTask(task_func=my_task, rate_limit="5/s")

        await limited_task()
        await limited_task()

        assert call_count["count"] == 2
