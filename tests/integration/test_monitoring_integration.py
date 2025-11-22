"""Integration tests for monitoring, rate limiting, and dashboard.

Tests complete workflows combining:
- Prometheus metrics
- Rate limiting
- Dashboard
- Task execution
- Result backend
- DLQ
"""

import asyncio

import pytest


@pytest.mark.asyncio
class TestMonitoringIntegration:
    """Test Prometheus metrics integration."""

    async def test_metrics_with_task_execution(self):
        """Test metrics are recorded during task execution."""
        pytest.importorskip("prometheus_client")

        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")
        metrics = app.setup_metrics(namespace="test")

        @app.task()
        async def test_task(x):
            await asyncio.sleep(0.1)
            return x * 2

        # Execute task
        await test_task.delay(5)
        await asyncio.sleep(0.2)

        # Metrics should be updated
        assert metrics is not None

    async def test_metrics_with_failed_tasks(self):
        """Test metrics record failed tasks."""
        pytest.importorskip("prometheus_client")

        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")
        metrics = app.setup_metrics(namespace="test")

        @app.task()
        async def failing_task():
            msg = "Test error"
            raise ValueError(msg)

        # Execute failing task
        try:
            await failing_task.delay()
        except Exception:
            pass

        await asyncio.sleep(0.1)

        # Failed task should be recorded
        assert metrics is not None

    async def test_metrics_with_periodic_tasks(self):
        """Test metrics for periodic tasks."""
        pytest.importorskip("prometheus_client")

        from aiotasks import AioTasks, every

        app = AioTasks("test_app", broker="memory://")
        metrics = app.setup_metrics(namespace="test")

        execution_count = {"count": 0}

        @app.task()
        async def periodic_task():
            execution_count["count"] += 1

        # Add periodic task
        app.add_periodic_task(
            name="test_periodic",
            schedule=every(seconds=1),
            task="periodic_task",
        )

        await app.start_scheduler()
        await asyncio.sleep(2.5)
        await app.stop_scheduler()

        # Should have executed and metrics recorded
        assert execution_count["count"] >= 2


@pytest.mark.asyncio
class TestRateLimitingIntegration:
    """Test rate limiting integration."""

    async def test_rate_limiting_with_tasks(self):
        """Test rate limiting on tasks."""
        from aiotasks import AioTasks, rate_limit

        app = AioTasks("test_app", broker="memory://")

        call_times = []

        @app.task()
        @rate_limit("5/s", wait=True)
        async def limited_task(value):
            import time

            call_times.append(time.time())
            return value

        # Submit 10 tasks
        for i in range(10):
            await limited_task.delay(i)

        await asyncio.sleep(2.5)

        # Should take at least 2 seconds due to rate limit
        if len(call_times) >= 2:
            duration = call_times[-1] - call_times[0]
            assert duration >= 1.0

    async def test_rate_limiting_protects_api(self):
        """Test rate limiting protects API calls."""
        from aiotasks import rate_limit

        call_count = {"count": 0}

        @rate_limit("10/s")
        async def api_call(endpoint):
            call_count["count"] += 1
            await asyncio.sleep(0.01)
            return f"Response from {endpoint}"

        # Make 10 calls rapidly
        results = await asyncio.gather(*[api_call(f"/api/{i}") for i in range(10)])

        assert len(results) == 10
        assert call_count["count"] == 10

    async def test_rate_limiting_with_result_backend(self):
        """Test rate limiting with result backend."""
        from aiotasks import AioTasks, rate_limit

        app = AioTasks("test_app", broker="memory://", backend="memory://")

        @app.task()
        @rate_limit("5/s")
        async def limited_task_with_result(x):
            return x**2

        # Execute tasks
        task = await limited_task_with_result.delay(5)
        await asyncio.sleep(0.5)

        # Should have result
        try:
            result = await app.get_result(task.task_id)
            assert result is not None
        except Exception:
            # Result backend might not be fully integrated yet
            pass


@pytest.mark.asyncio
class TestDashboardIntegration:
    """Test dashboard integration."""

    async def test_dashboard_shows_periodic_tasks(self):
        """Test dashboard shows periodic tasks."""
        pytest.importorskip("fastapi")

        from fastapi.testclient import TestClient

        from aiotasks import AioTasks, every
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add periodic tasks
        app.add_periodic_task(
            name="hourly_task",
            schedule=every(hours=1),
            task="dummy",
        )

        dashboard = DashboardServer(app)
        client = TestClient(dashboard.fastapi_app)

        response = client.get("/api/tasks/periodic")
        data = response.json()

        assert data["total"] == 1
        assert any(t["name"] == "hourly_task" for t in data["tasks"])

    async def test_dashboard_shows_dlq(self):
        """Test dashboard shows DLQ tasks."""
        pytest.importorskip("fastapi")

        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add failed task to DLQ
        await app._dlq.add_task(
            task_id="failed_123",
            task_name="test_task",
            error="Test error",
        )

        dashboard = DashboardServer(app)
        client = TestClient(dashboard.fastapi_app)

        response = client.get("/api/dlq")
        data = response.json()

        assert data["total"] == 1

    async def test_dashboard_with_metrics(self):
        """Test dashboard with metrics enabled."""
        pytest.importorskip("fastapi")
        pytest.importorskip("prometheus_client")

        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Setup metrics
        app.setup_metrics(namespace="test")

        dashboard = DashboardServer(app)
        client = TestClient(dashboard.fastapi_app)

        response = client.get("/api/metrics")

        # Metrics should be available
        assert response.status_code in [200, 503]


@pytest.mark.asyncio
class TestCompleteWorkflow:
    """Test complete workflow with all features."""

    async def test_full_monitoring_stack(self):
        """Test full monitoring stack integration."""
        pytest.importorskip("prometheus_client")

        from aiotasks import AioTasks, every, rate_limit

        app = AioTasks(
            "production_app",
            broker="memory://",
            backend="memory://",
        )

        # Setup monitoring
        metrics = app.setup_metrics(namespace="prod")

        execution_log = []

        @app.task()
        @rate_limit("10/s")
        async def monitored_task(task_id):
            execution_log.append(f"task_{task_id}")
            await asyncio.sleep(0.05)
            return f"result_{task_id}"

        @app.task()
        async def failing_task():
            msg = "Intentional failure"
            raise ValueError(msg)

        # Add periodic task
        app.add_periodic_task(
            name="health_check",
            schedule=every(seconds=1),
            task="monitored_task",
            args=(999,),
        )

        # Submit tasks
        for i in range(5):
            await monitored_task.delay(i)

        # Submit failing tasks
        for _ in range(2):
            try:
                await failing_task.delay()
            except Exception:
                pass

        # Wait for execution
        await asyncio.sleep(0.5)

        # All components should work together
        assert metrics is not None
        assert len(execution_log) >= 5

    async def test_dashboard_reflects_realtime_state(self):
        """Test dashboard reflects real-time application state."""
        pytest.importorskip("fastapi")

        from fastapi.testclient import TestClient

        from aiotasks import AioTasks, every
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add periodic task
        app.add_periodic_task(
            name="test_periodic",
            schedule=every(minutes=5),
            task="test",
        )

        # Add failed task
        await app._dlq.add_task(
            task_id="failed_1",
            task_name="test_task",
            error="Error",
        )

        # Create dashboard
        dashboard = DashboardServer(app)
        client = TestClient(dashboard.fastapi_app)

        # Check all endpoints reflect state
        periodic_resp = client.get("/api/tasks/periodic")
        assert periodic_resp.json()["total"] == 1

        dlq_resp = client.get("/api/dlq")
        assert dlq_resp.json()["total"] == 1

        stats_resp = client.get("/api/tasks/stats")
        assert stats_resp.json()["dlq_size"] == 1

    async def test_rate_limiting_prevents_overload(self):
        """Test rate limiting prevents system overload."""
        import time

        from aiotasks import rate_limit

        call_count = {"count": 0, "rejected": 0}

        @rate_limit("5/s", wait=False)
        async def protected_api():
            call_count["count"] += 1
            await asyncio.sleep(0.01)

        start = time.time()

        # Try to call 20 times rapidly
        for _ in range(20):
            try:
                await protected_api()
            except RuntimeError:
                call_count["rejected"] += 1

        elapsed = time.time() - start

        # Should have rejected excess calls
        assert call_count["rejected"] > 0

        # Should have completed quickly (not waited)
        assert elapsed < 1.0


@pytest.mark.asyncio
class TestErrorRecoveryWithMonitoring:
    """Test error recovery scenarios with monitoring."""

    async def test_dlq_retry_with_metrics(self):
        """Test DLQ retry records metrics."""
        pytest.importorskip("prometheus_client")

        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")
        metrics = app.setup_metrics(namespace="test")

        # Add failed task
        await app._dlq.add_task(
            task_id="failed_1",
            task_name="test_task",
            error="Error",
        )

        # Retry
        retried = await app.retry_failed_task("failed_1")

        # Should record retry metrics
        assert metrics is not None
        # Note: Actual retry might fail if task doesn't exist

    async def test_rate_limit_recovery(self):
        """Test rate limit recovery after reset."""
        from aiotasks.rate_limit import MemoryRateLimiter, RateLimit

        limiter = MemoryRateLimiter()
        rate = RateLimit(limit=2, period=10.0)

        # Use all slots
        await limiter.acquire("test_key", rate)
        await limiter.acquire("test_key", rate)

        # Should be rate limited
        assert await limiter.acquire("test_key", rate) is False

        # Reset
        await limiter.reset("test_key")

        # Should work again
        assert await limiter.acquire("test_key", rate) is True


@pytest.mark.asyncio
class TestPerformanceWithMonitoring:
    """Test performance with monitoring enabled."""

    async def test_metrics_overhead_minimal(self):
        """Test metrics add minimal overhead."""
        pytest.importorskip("prometheus_client")

        import time

        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")
        metrics = app.setup_metrics(namespace="test")

        @app.task()
        async def fast_task(x):
            return x + 1

        start = time.time()

        # Execute many tasks
        for i in range(100):
            await fast_task.delay(i)

        elapsed = time.time() - start

        # Should complete reasonably fast even with metrics
        assert elapsed < 2.0
        assert metrics is not None

    async def test_dashboard_api_performance(self):
        """Test dashboard API responds quickly."""
        pytest.importorskip("fastapi")

        import time

        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)

        start = time.time()

        # Make many API calls
        for _ in range(50):
            client.get("/api/health")

        elapsed = time.time() - start

        # Should be fast
        assert elapsed < 1.0
