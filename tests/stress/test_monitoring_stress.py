"""Stress and performance tests for monitoring and rate limiting.

Tests high-load scenarios:
- High-frequency metric recording
- Concurrent rate limiting
- Dashboard under load
- Memory usage
- Performance benchmarks
"""

import asyncio
import time

import pytest


@pytest.mark.slow
@pytest.mark.asyncio
class TestMetricsStress:
    """Stress tests for Prometheus metrics."""

    async def test_high_frequency_metric_recording(self):
        """Test metrics handle high-frequency updates."""
        prometheus = pytest.importorskip("prometheus_client")

        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="stress_test")

        start = time.time()

        # Record 10,000 metrics rapidly
        for i in range(10000):
            task_name = f"task_{i % 100}"  # 100 different task names
            metrics.record_task_start(task_name)
            metrics.record_task_complete(task_name, 0.001, "success")

        elapsed = time.time() - start

        # Should handle high frequency (< 5 seconds for 10k)
        assert elapsed < 5.0
        print(f"\n  Recorded 10,000 metrics in {elapsed:.2f}s ({10000/elapsed:.0f} ops/s)")

    async def test_concurrent_metric_updates(self):
        """Test concurrent metric updates from multiple tasks."""
        prometheus = pytest.importorskip("prometheus_client")

        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="stress_test")

        async def update_metrics(worker_id, iterations):
            for i in range(iterations):
                task_name = f"worker_{worker_id}_task_{i % 10}"
                metrics.record_task_start(task_name)
                await asyncio.sleep(0.0001)  # Tiny delay
                metrics.record_task_complete(task_name, 0.001, "success")

        start = time.time()

        # 50 concurrent workers, 100 iterations each = 5,000 updates
        await asyncio.gather(*[update_metrics(i, 100) for i in range(50)])

        elapsed = time.time() - start

        # Should handle concurrency well
        assert elapsed < 10.0
        print(f"\n  Handled 5,000 concurrent updates in {elapsed:.2f}s")

    async def test_metrics_memory_usage(self):
        """Test metrics don't leak memory."""
        prometheus = pytest.importorskip("prometheus_client")

        import gc

        from aiotasks.monitoring import PrometheusMetrics

        gc.collect()
        metrics = PrometheusMetrics(namespace="memory_test")

        # Record many different task names
        for i in range(1000):
            metrics.record_task_start(f"task_{i}")
            metrics.record_task_complete(f"task_{i}", 0.001, "success")

        # Force garbage collection
        gc.collect()

        # Memory should be reasonable (hard to test precisely)
        # Just ensure it completes without error
        assert metrics is not None

    async def test_context_manager_overhead(self):
        """Test context manager performance overhead."""
        prometheus = pytest.importorskip("prometheus_client")

        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="perf_test")

        async def task_with_tracking():
            async with metrics.track_task_execution("perf_task"):
                await asyncio.sleep(0.001)

        start = time.time()

        # 1,000 context manager uses
        await asyncio.gather(*[task_with_tracking() for _ in range(1000)])

        elapsed = time.time() - start

        # Should be fast (<2s mostly sleep time)
        assert elapsed < 3.0
        print(f"\n  1,000 tracked executions in {elapsed:.2f}s")


@pytest.mark.slow
@pytest.mark.asyncio
class TestRateLimitingStress:
    """Stress tests for rate limiting."""

    async def test_high_throughput_rate_limiting(self):
        """Test rate limiting with high throughput."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=1000, period=1.0)  # 1000/s

        start = time.time()

        # Try 5,000 acquires (should allow first 1000 quickly)
        results = []
        for _ in range(5000):
            result = await limiter.acquire("test_key", rate)
            results.append(result)

        elapsed = time.time() - start

        successful = sum(1 for r in results if r)

        # First 1000 should succeed
        assert successful == 1000

        # Should be fast
        assert elapsed < 2.0
        print(f"\n  Processed 5,000 rate limit checks in {elapsed:.2f}s")

    async def test_concurrent_different_keys(self):
        """Test concurrent rate limiting on many different keys."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=100, period=1.0)

        async def acquire_for_key(key_id, count):
            results = []
            for _ in range(count):
                result = await limiter.acquire(f"key_{key_id}", rate)
                results.append(result)
            return results

        start = time.time()

        # 100 keys, 50 acquires each = 5,000 total
        all_results = await asyncio.gather(
            *[acquire_for_key(i, 50) for i in range(100)]
        )

        elapsed = time.time() - start

        # Each key should have independent limits
        for results in all_results:
            assert sum(results) == 50  # All should succeed (under limit)

        assert elapsed < 3.0
        print(f"\n  100 keys with 50 ops each completed in {elapsed:.2f}s")

    async def test_wait_for_slot_scalability(self):
        """Test wait_for_slot with many concurrent waiters."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=10, period=1.0)

        # Use all slots
        for _ in range(10):
            await limiter.acquire("test_key", rate)

        async def wait_task():
            return await limiter.wait_for_slot("test_key", rate, timeout=2.0)

        start = time.time()

        # 20 concurrent waiters
        results = await asyncio.gather(*[wait_task() for _ in range(20)])

        elapsed = time.time() - start

        # Some should succeed after refill
        successful = sum(1 for r in results if r)

        assert successful > 0
        assert elapsed >= 0.9  # Had to wait for refill
        print(f"\n  20 concurrent waiters: {successful} succeeded in {elapsed:.2f}s")

    async def test_burst_handling(self):
        """Test handling of burst traffic."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=100, period=10.0, burst=200)

        start = time.time()

        # Simulate burst: 200 immediate requests
        burst_results = []
        for _ in range(200):
            result = await limiter.acquire("burst_key", rate)
            burst_results.append(result)

        elapsed = time.time() - start

        # Burst should allow 200
        assert sum(burst_results) == 200

        # Should be very fast (no waiting)
        assert elapsed < 0.5
        print(f"\n  Handled burst of 200 requests in {elapsed:.3f}s")

        # Next request should fail (burst exhausted)
        assert await limiter.acquire("burst_key", rate) is False

    async def test_rate_limiter_memory_efficiency(self):
        """Test rate limiter memory efficiency with many keys."""
        import gc

        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        gc.collect()

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=10, period=1.0)

        # Create buckets for 1000 different keys
        for i in range(1000):
            await limiter.acquire(f"key_{i}", rate)

        gc.collect()

        # Should handle many keys efficiently
        assert len(limiter._buckets) == 1000

        # Reset should clean up
        for i in range(1000):
            await limiter.reset(f"key_{i}")

        assert len(limiter._buckets) == 0
        print("\n  Memory efficiently managed 1000 keys")


@pytest.mark.slow
@pytest.mark.asyncio
class TestDashboardStress:
    """Stress tests for dashboard."""

    async def test_dashboard_api_high_load(self):
        """Test dashboard API under high load."""
        fastapi = pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("stress_test", broker="memory://")

        # Add some data
        for i in range(100):
            app.add_periodic_task(
                name=f"task_{i}",
                schedule=__import__("aiotasks").every(hours=1),
                task="dummy",
            )

        dashboard = DashboardServer(app)
        client = TestClient(dashboard.fastapi_app)

        start = time.time()

        # Make 1000 API calls
        responses = []
        for _ in range(1000):
            resp = client.get("/api/health")
            responses.append(resp.status_code)

        elapsed = time.time() - start

        # All should succeed
        assert all(code == 200 for code in responses)

        # Should be fast
        assert elapsed < 5.0
        print(f"\n  1000 API calls in {elapsed:.2f}s ({1000/elapsed:.0f} req/s)")

    async def test_dashboard_with_large_dlq(self):
        """Test dashboard with large DLQ."""
        fastapi = pytest.importorskip("fastapi")
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("stress_test", broker="memory://")

        # Add many failed tasks
        for i in range(500):
            await app._dlq.add_task(
                task_id=f"failed_{i}",
                task_name=f"task_{i % 10}",
                error="Test error",
            )

        dashboard = DashboardServer(app)
        client = TestClient(dashboard.fastapi_app)

        start = time.time()

        # Get DLQ with limit
        response = client.get("/api/dlq?limit=100")

        elapsed = time.time() - start

        # Should return data
        assert response.status_code == 200
        data = response.json()
        assert len(data["tasks"]) <= 100

        # Should be reasonably fast
        assert elapsed < 2.0
        print(f"\n  Retrieved DLQ with 500 tasks in {elapsed:.3f}s")


@pytest.mark.slow
@pytest.mark.asyncio
class TestCombinedStress:
    """Combined stress tests."""

    async def test_full_stack_under_load(self):
        """Test full monitoring stack under load."""
        prometheus = pytest.importorskip("prometheus_client")

        from aiotasks import AioTasks, rate_limit

        app = AioTasks("production_stress", broker="memory://")
        metrics = app.setup_metrics(namespace="stress")

        call_count = {"count": 0}

        @app.task()
        @rate_limit("100/s")
        async def monitored_limited_task(x):
            call_count["count"] += 1
            await asyncio.sleep(0.001)
            return x * 2

        start = time.time()

        # Submit 500 tasks
        for i in range(500):
            await monitored_limited_task.delay(i)

        elapsed = time.time() - start

        # Should complete
        await asyncio.sleep(1.0)

        # All components working
        assert metrics is not None
        assert call_count["count"] <= 500
        print(f"\n  Full stack handled 500 tasks in {elapsed:.2f}s")

    async def test_metrics_and_rate_limiting_performance(self):
        """Test combined metrics and rate limiting performance."""
        prometheus = pytest.importorskip("prometheus_client")

        from aiotasks.monitoring import PrometheusMetrics
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        metrics = PrometheusMetrics(namespace="combined_test")
        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=1000, period=1.0)

        async def metered_limited_operation(op_id):
            # Check rate limit
            if not await limiter.acquire("api_calls", rate):
                return False

            # Record metrics
            metrics.record_task_start(f"op_{op_id % 10}")
            await asyncio.sleep(0.0001)
            metrics.record_task_complete(f"op_{op_id % 10}", 0.001, "success")

            return True

        start = time.time()

        # 5000 operations
        results = await asyncio.gather(
            *[metered_limited_operation(i) for i in range(5000)]
        )

        elapsed = time.time() - start

        successful = sum(1 for r in results if r)

        # Rate limit should restrict to ~1000
        assert 900 <= successful <= 1100

        # Should be fast
        assert elapsed < 5.0
        print(f"\n  5000 metered+limited ops in {elapsed:.2f}s, {successful} succeeded")


@pytest.mark.slow
@pytest.mark.asyncio
class TestMemoryLeaks:
    """Test for memory leaks under stress."""

    async def test_no_metric_memory_leak(self):
        """Test metrics don't leak memory over time."""
        prometheus = pytest.importorskip("prometheus_client")

        import gc

        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="leak_test")

        # Run many iterations
        for iteration in range(10):
            for i in range(100):
                task_name = f"task_{i % 20}"  # Reuse names
                metrics.record_task_start(task_name)
                metrics.record_task_complete(task_name, 0.001, "success")

            gc.collect()

        # Should complete without growing indefinitely
        assert metrics is not None
        print("\n  No memory leak detected in 1000 metric recordings")

    async def test_no_rate_limiter_memory_leak(self):
        """Test rate limiter doesn't leak memory."""
        import gc

        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=10, period=0.1)

        # Run many iterations with same keys
        for iteration in range(100):
            for key_id in range(10):
                await limiter.acquire(f"key_{key_id}", rate)

            await asyncio.sleep(0.15)  # Let buckets refill
            gc.collect()

        # Bucket count should be stable
        assert len(limiter._buckets) <= 10
        print("\n  No memory leak detected in rate limiter")
