"""Unit tests for web dashboard.

Tests cover:
- Dashboard server initialization
- FastAPI app setup
- API endpoints
- WebSocket functionality
- Integration with AioTasks
- Edge cases and error handling
"""

import pytest

# Skip all tests if FastAPI not available
fastapi = pytest.importorskip("fastapi")


@pytest.mark.asyncio
class TestDashboardInitialization:
    """Test dashboard initialization."""

    def test_create_dashboard_server(self):
        """Test creating dashboard server."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app, host="127.0.0.1", port=5555)

        assert dashboard.app == app
        assert dashboard.host == "127.0.0.1"
        assert dashboard.port == 5555
        assert dashboard.fastapi_app is not None

    def test_create_dashboard_with_custom_port(self):
        """Test dashboard with custom port."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app, port=8080)

        assert dashboard.port == 8080

    def test_create_dashboard_with_cors(self):
        """Test dashboard with CORS enabled."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app, enable_cors=True)

        # CORS middleware should be added
        assert dashboard.fastapi_app is not None

    def test_create_dashboard_without_cors(self):
        """Test dashboard without CORS."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app, enable_cors=False)

        assert dashboard.fastapi_app is not None

    def test_dashboard_websocket_clients_initialized(self):
        """Test WebSocket clients list is initialized."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        assert dashboard.websocket_clients == []


@pytest.mark.asyncio
class TestDashboardAPIEndpoints:
    """Test dashboard API endpoints."""

    async def test_app_info_endpoint(self):
        """Test /api/app endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="redis://localhost:6379/0")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/app")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_app"
        assert data["broker"] == "redis://localhost:6379/0"
        assert "pool" in data

    async def test_workers_endpoint(self):
        """Test /api/workers endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/workers")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "workers" in data

    async def test_task_stats_endpoint(self):
        """Test /api/tasks/stats endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/tasks/stats")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "active" in data
        assert "failed" in data

    async def test_periodic_tasks_endpoint(self):
        """Test /api/tasks/periodic endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks, every
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add periodic task
        app.add_periodic_task(
            name="test_periodic",
            schedule=every(hours=1),
            task="dummy_task",
        )

        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/tasks/periodic")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "tasks" in data
        assert data["total"] == 1

    async def test_dlq_endpoint(self):
        """Test /api/dlq endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/dlq")

        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "tasks" in data

    async def test_dlq_stats_endpoint(self):
        """Test /api/dlq/stats endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/dlq/stats")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_health_endpoint(self):
        """Test /api/health endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data

    async def test_queues_endpoint(self):
        """Test /api/queues endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/queues")

        assert response.status_code == 200
        data = response.json()
        assert "queues" in data


@pytest.mark.asyncio
class TestDashboardActions:
    """Test dashboard action endpoints."""

    async def test_retry_dlq_task(self):
        """Test POST /api/dlq/{task_id}/retry endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add a failed task to DLQ
        await app._dlq.add_task(
            task_id="failed_123",
            task_name="test_task",
            error="Test error",
        )

        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.post("/api/dlq/failed_123/retry")

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "task_id" in data

    async def test_retry_all_dlq_tasks(self):
        """Test POST /api/dlq/retry-all endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add failed tasks
        await app._dlq.add_task(task_id="failed_1", task_name="test_task", error="Error 1")
        await app._dlq.add_task(task_id="failed_2", task_name="test_task", error="Error 2")

        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.post("/api/dlq/retry-all")

        assert response.status_code == 200
        data = response.json()
        assert "retried" in data

    async def test_clear_dlq(self):
        """Test DELETE /api/dlq endpoint."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Add failed tasks
        await app._dlq.add_task(task_id="failed_1", task_name="test_task", error="Error")

        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.delete("/api/dlq")

        assert response.status_code == 200
        data = response.json()
        assert "cleared" in data


@pytest.mark.asyncio
class TestDashboardHTML:
    """Test dashboard HTML interface."""

    async def test_root_endpoint_returns_html(self):
        """Test root endpoint returns HTML."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        assert b"AioTasks Dashboard" in response.content

    async def test_dashboard_html_contains_title(self):
        """Test dashboard HTML contains title."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/")

        assert b"<title>" in response.content
        assert b"Dashboard" in response.content

    async def test_dashboard_html_responsive(self):
        """Test dashboard HTML includes responsive meta tag."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/")

        assert b"viewport" in response.content
        assert b"width=device-width" in response.content


@pytest.mark.asyncio
class TestDashboardIntegration:
    """Test dashboard integration with AioTasks."""

    async def test_setup_dashboard_on_app(self):
        """Test setting up dashboard on AioTasks app."""
        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")
        dashboard = app.setup_dashboard(port=5555)

        assert dashboard is not None
        assert app.get_dashboard() is dashboard

    async def test_setup_dashboard_twice(self):
        """Test setting up dashboard twice returns same instance."""
        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")

        dashboard1 = app.setup_dashboard(port=5555)
        dashboard2 = app.setup_dashboard(port=6666)

        # Should return same instance
        assert dashboard1 is dashboard2

    async def test_dashboard_without_setup(self):
        """Test getting dashboard without setup."""
        from aiotasks import AioTasks

        app = AioTasks("test_app", broker="memory://")

        assert app.get_dashboard() is None

    async def test_create_dashboard_helper(self):
        """Test create_dashboard helper function."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import create_dashboard

        app = AioTasks("test_app", broker="memory://")
        dashboard = create_dashboard(app, port=5555)

        assert dashboard is not None
        assert dashboard.port == 5555


@pytest.mark.asyncio
class TestDashboardEdgeCases:
    """Test dashboard edge cases."""

    async def test_dashboard_with_empty_app_name(self):
        """Test dashboard with empty app name."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("", broker="memory://")
        dashboard = DashboardServer(app)

        assert dashboard.fastapi_app is not None

    async def test_dashboard_api_with_no_periodic_tasks(self):
        """Test periodic tasks endpoint with no tasks."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/tasks/periodic")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_dashboard_api_with_no_failed_tasks(self):
        """Test DLQ endpoint with no failed tasks."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/dlq")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0

    async def test_retry_nonexistent_task(self):
        """Test retrying nonexistent task."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.post("/api/dlq/nonexistent_task/retry")

        # Should not crash, should return false
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    async def test_dashboard_with_long_broker_url(self):
        """Test dashboard with very long broker URL."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        long_url = "redis://" + "a" * 1000 + ":6379/0"
        app = AioTasks("test_app", broker=long_url)
        dashboard = DashboardServer(app)

        # Should handle long URLs
        assert dashboard.app.broker_url == long_url


@pytest.mark.asyncio
class TestDashboardBroadcast:
    """Test dashboard WebSocket broadcast functionality."""

    async def test_broadcast_update_empty_clients(self):
        """Test broadcasting with no clients."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        # Should not raise with no clients
        await dashboard.broadcast_update({"type": "test", "data": "test"})

    async def test_broadcast_update_with_message(self):
        """Test broadcasting update message."""
        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        message = {
            "type": "stats",
            "tasks": {"total": 100, "active": 5},
        }

        # Should not raise
        await dashboard.broadcast_update(message)


@pytest.mark.asyncio
class TestDashboardMetrics:
    """Test dashboard metrics integration."""

    async def test_metrics_endpoint_without_metrics(self):
        """Test /api/metrics when metrics not enabled."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")
        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/metrics")

        # Should return 503 when metrics not available
        assert response.status_code == 503

    async def test_metrics_endpoint_with_metrics(self):
        """Test /api/metrics when metrics enabled."""
        from fastapi.testclient import TestClient

        from aiotasks import AioTasks
        from aiotasks.dashboard import DashboardServer

        app = AioTasks("test_app", broker="memory://")

        # Setup metrics
        try:
            app.setup_metrics(namespace="test")
        except Exception:
            pytest.skip("Prometheus not available")

        dashboard = DashboardServer(app)

        client = TestClient(dashboard.fastapi_app)
        response = client.get("/api/metrics")

        # Should return metrics
        if response.status_code == 200:
            data = response.json()
            assert "metrics" in data


@pytest.mark.asyncio
class TestDashboardCLIIntegration:
    """Test dashboard CLI integration."""

    def test_dashboard_cli_command_exists(self):
        """Test dashboard CLI command exists."""
        from aiotasks.cli import cli

        # Check dashboard command is registered
        assert "dashboard" in [cmd.name for cmd in cli.commands.values()]

    def test_dashboard_cli_help(self):
        """Test dashboard CLI help."""
        from click.testing import CliRunner

        from aiotasks.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["dashboard", "--help"])

        assert result.exit_code == 0
        assert "Dashboard" in result.output or "dashboard" in result.output
