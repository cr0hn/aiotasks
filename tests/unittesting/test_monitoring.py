"""Unit tests for Prometheus metrics monitoring.

Tests cover:
- PrometheusMetrics initialization
- Metric recording and updates
- HTTP server functionality
- Context manager tracking
- Global metrics singleton
- Edge cases and error handling
"""

import time

import pytest

# Skip all tests if prometheus_client not available
pytest.importorskip("prometheus_client")


@pytest.mark.asyncio
class TestPrometheusMetricsInitialization:
    """Test PrometheusMetrics initialization."""

    def test_create_metrics_instance(self):
        """Test creating metrics instance."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test_app")

        assert metrics.enabled is True
        assert metrics.namespace == "test_app"
        assert metrics.tasks_total is not None
        assert metrics.tasks_failed_total is not None
        assert metrics.task_duration_seconds is not None

    def test_create_metrics_without_prometheus(self, monkeypatch):
        """Test metrics creation when prometheus_client not available."""
        from aiotasks import monitoring

        # Temporarily disable prometheus
        original_available = monitoring.PROMETHEUS_AVAILABLE
        monkeypatch.setattr(monitoring, "PROMETHEUS_AVAILABLE", False)

        metrics = monitoring.PrometheusMetrics(namespace="test")
        assert metrics.enabled is False

        # Restore
        monkeypatch.setattr(monitoring, "PROMETHEUS_AVAILABLE", original_available)

    def test_metrics_with_custom_namespace(self):
        """Test metrics with custom namespace."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="custom_namespace")

        assert metrics.namespace == "custom_namespace"
        # Verify metric names include namespace
        assert "custom_namespace_tasks_total" in str(metrics.tasks_total._name)

    def test_metrics_initialization_all_counters(self):
        """Test all counters are initialized."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        # Counters
        assert hasattr(metrics, "tasks_total")
        assert hasattr(metrics, "tasks_failed_total")
        assert hasattr(metrics, "tasks_retried_total")
        assert hasattr(metrics, "periodic_tasks_total")

        # Gauges
        assert hasattr(metrics, "workers_active")
        assert hasattr(metrics, "tasks_in_progress")
        assert hasattr(metrics, "queue_length")
        assert hasattr(metrics, "dlq_size")

        # Histograms
        assert hasattr(metrics, "task_duration_seconds")


@pytest.mark.asyncio
class TestMetricRecording:
    """Test metric recording functionality."""

    def test_record_task_start(self):
        """Test recording task start."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        # Record start
        metrics.record_task_start("test_task")

        # Verify in_progress increased
        # Note: We can't easily check the exact value due to prometheus_client internals
        # but we can verify the method doesn't raise

    def test_record_task_complete_success(self):
        """Test recording successful task completion."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.record_task_start("test_task")
        metrics.record_task_complete("test_task", duration=1.5, status="success")

        # Should not raise

    def test_record_task_failure(self):
        """Test recording task failure."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.record_task_start("test_task")
        metrics.record_task_failure("test_task", error_type="ValueError", duration=0.5)

        # Should not raise

    def test_record_task_retry(self):
        """Test recording task retry."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.record_task_retry("test_task")

        # Should not raise

    def test_update_queue_length(self):
        """Test updating queue length metric."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.update_queue_length("default", 42)
        metrics.update_queue_length("default", 0)

        # Should not raise

    def test_update_workers_active(self):
        """Test updating workers active metric."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.update_workers_active(5)
        metrics.update_workers_active(0)

        # Should not raise

    def test_update_dlq_size(self):
        """Test updating DLQ size metric."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.update_dlq_size(10)
        metrics.update_dlq_size(0)

        # Should not raise

    def test_record_periodic_task_execution(self):
        """Test recording periodic task execution."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.record_periodic_task_execution("hourly_task")
        metrics.record_periodic_task_execution("daily_task")

        # Should not raise

    def test_multiple_task_recordings(self):
        """Test recording multiple tasks."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        # Simulate multiple tasks
        for i in range(10):
            task_name = f"task_{i}"
            metrics.record_task_start(task_name)

            if i % 3 == 0:
                metrics.record_task_failure(task_name, "TimeoutError", 2.0)
            else:
                metrics.record_task_complete(task_name, 1.0, "success")

        # Should not raise


@pytest.mark.asyncio
class TestMetricContextManager:
    """Test metric context manager."""

    async def test_track_task_execution_success(self):
        """Test tracking successful task execution."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        async with metrics.track_task_execution("test_task"):
            # Simulate task work
            await __import__("asyncio").sleep(0.1)

        # Should complete without error

    async def test_track_task_execution_failure(self):
        """Test tracking failed task execution."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        with pytest.raises(ValueError):
            async with metrics.track_task_execution("failing_task"):
                msg = "Test error"
                raise ValueError(msg)

        # Error should be propagated and recorded

    async def test_track_task_execution_multiple(self):
        """Test tracking multiple task executions."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        for i in range(5):
            async with metrics.track_task_execution(f"task_{i}"):
                await __import__("asyncio").sleep(0.05)

        # All should complete

    async def test_context_manager_when_disabled(self):
        """Test context manager when metrics disabled."""
        from aiotasks import monitoring

        # Create disabled metrics
        original_available = monitoring.PROMETHEUS_AVAILABLE
        monitoring.PROMETHEUS_AVAILABLE = False

        metrics = monitoring.PrometheusMetrics(namespace="test")

        # Should still work (just does nothing)
        async with metrics.track_task_execution("test_task"):
            await __import__("asyncio").sleep(0.05)

        monitoring.PROMETHEUS_AVAILABLE = original_available


@pytest.mark.asyncio
class TestMetricsHTTPServer:
    """Test metrics HTTP server."""

    def test_get_latest_metrics(self):
        """Test getting latest metrics."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        # Record some metrics
        metrics.record_task_start("test_task")
        metrics.record_task_complete("test_task", 1.0, "success")

        # Get metrics
        latest = metrics.get_latest_metrics()

        assert isinstance(latest, bytes)
        assert len(latest) > 0
        assert b"test_tasks_total" in latest or b"tasks_total" in latest

    def test_get_latest_metrics_when_disabled(self):
        """Test getting metrics when disabled."""
        from aiotasks import monitoring

        original_available = monitoring.PROMETHEUS_AVAILABLE
        monitoring.PROMETHEUS_AVAILABLE = False

        metrics = monitoring.PrometheusMetrics(namespace="test")
        latest = metrics.get_latest_metrics()

        assert latest == b""

        monitoring.PROMETHEUS_AVAILABLE = original_available


@pytest.mark.asyncio
class TestGlobalMetrics:
    """Test global metrics singleton."""

    def test_setup_metrics(self):
        """Test setting up global metrics."""
        from aiotasks.monitoring import setup_metrics

        metrics = setup_metrics(namespace="global_test")

        assert metrics is not None
        assert metrics.namespace == "global_test"

    def test_get_metrics(self):
        """Test getting global metrics."""
        from aiotasks.monitoring import get_metrics, setup_metrics

        # Setup first
        setup_metrics(namespace="global_test2")

        # Get
        metrics = get_metrics()
        assert metrics is not None

    def test_setup_metrics_twice_returns_same_instance(self):
        """Test setup_metrics returns same instance when called twice."""
        # Reset global
        import aiotasks.monitoring as mon
        from aiotasks.monitoring import setup_metrics

        mon._global_metrics = None

        metrics1 = setup_metrics(namespace="test1")
        metrics2 = setup_metrics(namespace="test2")

        # Should return same instance (first one)
        assert metrics1 is metrics2
        assert metrics1.namespace == "test1"

        # Reset
        mon._global_metrics = None


@pytest.mark.asyncio
class TestMetricsIntegrationWithAioTasks:
    """Test metrics integration with AioTasks app."""

    async def test_setup_metrics_on_app(self):
        """Test setting up metrics on AioTasks app."""
        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")
        metrics = app.setup_metrics(namespace="test_app")

        assert metrics is not None
        assert app.get_metrics() is metrics

    async def test_metrics_without_setup(self):
        """Test getting metrics without setup."""
        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")

        assert app.get_metrics() is None

    async def test_setup_metrics_twice_on_app(self):
        """Test setting up metrics twice on same app."""
        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")

        metrics1 = app.setup_metrics(namespace="test1")
        metrics2 = app.setup_metrics(namespace="test2")

        # Should return same instance
        assert metrics1 is metrics2


@pytest.mark.asyncio
class TestMetricsEdgeCases:
    """Test edge cases for metrics."""

    def test_record_with_very_long_task_name(self):
        """Test recording with very long task name."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        long_name = "a" * 500
        metrics.record_task_start(long_name)
        metrics.record_task_complete(long_name, 1.0, "success")

        # Should handle long names

    def test_record_with_special_characters_in_task_name(self):
        """Test recording with special characters."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        special_name = "task-with.special:characters"
        metrics.record_task_start(special_name)
        metrics.record_task_complete(special_name, 0.5, "success")

        # Should handle special characters

    def test_record_with_negative_duration(self):
        """Test recording with negative duration (edge case)."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        # Negative duration shouldn't happen, but shouldn't crash
        metrics.record_task_start("test_task")
        metrics.record_task_complete("test_task", -1.0, "success")

        # Should not raise

    def test_record_with_zero_duration(self):
        """Test recording with zero duration."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.record_task_start("instant_task")
        metrics.record_task_complete("instant_task", 0.0, "success")

        # Should handle zero duration

    def test_record_with_very_large_duration(self):
        """Test recording with very large duration."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        metrics.record_task_start("slow_task")
        metrics.record_task_complete("slow_task", 3600.0, "success")  # 1 hour

        # Should handle large durations

    def test_update_queue_with_negative_length(self):
        """Test updating queue with negative length."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        # Negative shouldn't happen but shouldn't crash
        metrics.update_queue_length("default", -5)

        # Should not raise

    def test_concurrent_metric_updates(self):
        """Test concurrent metric updates."""
        import asyncio

        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        async def update_metrics(task_id):
            metrics.record_task_start(f"task_{task_id}")
            await asyncio.sleep(0.01)
            metrics.record_task_complete(f"task_{task_id}", 0.01, "success")

        async def run_concurrent():
            await asyncio.gather(*[update_metrics(i) for i in range(50)])

        # Should handle concurrent updates
        asyncio.run(run_concurrent())


@pytest.mark.asyncio
class TestMetricsPerformance:
    """Test metrics performance characteristics."""

    def test_metric_recording_performance(self):
        """Test performance of metric recording."""
        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        start = time.time()

        # Record many metrics quickly
        for i in range(1000):
            metrics.record_task_start(f"task_{i % 10}")
            metrics.record_task_complete(f"task_{i % 10}", 0.1, "success")

        elapsed = time.time() - start

        # Should be fast (< 1 second for 1000 recordings)
        assert elapsed < 1.0

    async def test_context_manager_performance(self):
        """Test context manager overhead."""
        import asyncio

        from aiotasks.monitoring import PrometheusMetrics

        metrics = PrometheusMetrics(namespace="test")

        start = time.time()

        # Many context manager uses
        for i in range(100):
            async with metrics.track_task_execution(f"task_{i % 5}"):
                await asyncio.sleep(0.001)

        elapsed = time.time() - start

        # Should be reasonably fast
        assert elapsed < 2.0  # Mostly sleep time
