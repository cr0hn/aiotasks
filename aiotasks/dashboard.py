"""Modern web dashboard for AioTasks monitoring and management.

FastAPI-based dashboard with real-time monitoring, worker control,
and task management capabilities. More beautiful and feature-rich
than Celery Flower.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .app import AioTasks

log = logging.getLogger("aiotasks.dashboard")

# Try to import FastAPI
try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.staticfiles import StaticFiles

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    log.warning(
        "FastAPI not installed. Dashboard will not be available. "
        "Install with: pip install aiotasks[dashboard]"
    )


class DashboardServer:
    """AioTasks monitoring dashboard server.

    Provides web-based monitoring and control interface with:
    - Real-time task monitoring
    - Worker management
    - Queue statistics
    - DLQ management
    - Prometheus metrics visualization
    - Task history and details

    Usage:
        >>> from aiotasks import AioTasks
        >>> from aiotasks.dashboard import DashboardServer
        >>>
        >>> app = AioTasks('myapp', broker='redis://localhost')
        >>> dashboard = DashboardServer(app, host='0.0.0.0', port=5555)
        >>> await dashboard.start()
        >>>
        >>> # Dashboard available at http://localhost:5555
    """

    def __init__(
        self,
        app: AioTasks,
        host: str = "127.0.0.1",
        port: int = 5555,
        enable_cors: bool = True,
    ) -> None:
        """Initialize dashboard server.

        Args:
            app: AioTasks application instance
            host: Server host address
            port: Server port
            enable_cors: Enable CORS for API access
        """
        if not FASTAPI_AVAILABLE:
            msg = "FastAPI not installed. Install with: pip install aiotasks[dashboard]"
            raise ImportError(msg)

        self.app = app
        self.host = host
        self.port = port

        # Create FastAPI app
        self.fastapi_app = FastAPI(
            title="AioTasks Dashboard",
            description="Modern monitoring and management dashboard for AioTasks",
            version="1.0.0",
        )

        # Enable CORS if requested
        if enable_cors:
            self.fastapi_app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # WebSocket connections for real-time updates
        self.websocket_clients: list[WebSocket] = []

        # Setup routes
        self._setup_routes()

        log.info(f"Dashboard initialized for app '{app.name}'")

    def _setup_routes(self) -> None:
        """Setup FastAPI routes."""

        # Root - serve dashboard HTML
        @self.fastapi_app.get("/", response_class=HTMLResponse)
        async def dashboard_home() -> str:
            return self._get_dashboard_html()

        # API: Get application info
        @self.fastapi_app.get("/api/app")
        async def get_app_info() -> dict[str, Any]:
            return {
                "name": self.app.name,
                "broker": self.app.broker_url,
                "backend": self.app.backend_url,
                "pool": self.app.pool,
                "celery_compat": self.app.celery_compat,
            }

        # API: Get workers info
        @self.fastapi_app.get("/api/workers")
        async def get_workers() -> dict[str, Any]:
            # Get worker stats from manager
            stats = {
                "total": 1,  # TODO: implement worker tracking
                "active": 1,
                "idle": 0,
                "workers": [
                    {
                        "id": "worker-1",
                        "status": "active",
                        "pool": self.app.pool,
                        "concurrency": getattr(self.app._manager, "_concurrency", 5),
                        "tasks_active": 0,
                        "tasks_completed": 0,
                    }
                ],
            }
            return stats

        # API: Get tasks statistics
        @self.fastapi_app.get("/api/tasks/stats")
        async def get_task_stats() -> dict[str, Any]:
            stats = {
                "total": 0,
                "active": 0,
                "completed": 0,
                "failed": 0,
                "retried": 0,
            }

            # Add DLQ stats
            dlq_stats = self.app.get_dlq_stats()
            stats["dlq_size"] = dlq_stats.get("total_tasks", 0)

            return stats

        # API: Get periodic tasks
        @self.fastapi_app.get("/api/tasks/periodic")
        async def get_periodic_tasks() -> dict[str, Any]:
            tasks = self.app.list_periodic_tasks()
            return {
                "total": len(tasks),
                "tasks": [
                    {
                        "name": task.name,
                        "schedule": str(task.schedule),
                        "enabled": task.enabled,
                        "last_run": task.last_run.isoformat() if task.last_run else None,
                        "total_runs": task.total_runs,
                    }
                    for task in tasks
                ],
            }

        # API: Get DLQ tasks
        @self.fastapi_app.get("/api/dlq")
        async def get_dlq_tasks(limit: int = 100) -> dict[str, Any]:
            failed_tasks = await self.app.list_failed_tasks(limit=limit)
            return {
                "total": len(failed_tasks),
                "tasks": [
                    {
                        "task_id": task.task_id,
                        "task_name": task.task_name,
                        "error": task.error,
                        "retry_count": task.retry_count,
                        "failed_at": task.failed_at.isoformat(),
                    }
                    for task in failed_tasks
                ],
            }

        # API: Get DLQ statistics
        @self.fastapi_app.get("/api/dlq/stats")
        async def get_dlq_stats() -> dict[str, Any]:
            return self.app.get_dlq_stats()

        # API: Retry DLQ task
        @self.fastapi_app.post("/api/dlq/{task_id}/retry")
        async def retry_dlq_task(task_id: str) -> dict[str, Any]:
            success = await self.app.retry_failed_task(task_id)
            return {"success": success, "task_id": task_id}

        # API: Retry all DLQ tasks
        @self.fastapi_app.post("/api/dlq/retry-all")
        async def retry_all_dlq_tasks() -> dict[str, Any]:
            count = await self.app.retry_failed_tasks()
            return {"retried": count}

        # API: Clear DLQ
        @self.fastapi_app.delete("/api/dlq")
        async def clear_dlq() -> dict[str, Any]:
            count = await self.app.clear_failed_tasks()
            return {"cleared": count}

        # API: Get queue stats
        @self.fastapi_app.get("/api/queues")
        async def get_queue_stats() -> dict[str, Any]:
            # TODO: implement queue statistics
            return {
                "queues": [
                    {
                        "name": "default",
                        "length": 0,
                        "consumers": 1,
                    }
                ]
            }

        # API: Health check
        @self.fastapi_app.get("/api/health")
        async def health_check() -> dict[str, Any]:
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
            }

        # API: Get Prometheus metrics
        @self.fastapi_app.get("/api/metrics")
        async def get_metrics() -> JSONResponse:
            # Try to get metrics from monitoring module
            try:
                from .monitoring import get_metrics

                metrics = get_metrics()
                if metrics and metrics.enabled:
                    data = metrics.get_latest_metrics()
                    return JSONResponse(
                        content={"metrics": data.decode("utf-8")},
                        media_type="application/json",
                    )
            except Exception as e:
                log.warning(f"Failed to get metrics: {e}")

            return JSONResponse(
                content={"metrics": None, "error": "Metrics not available"},
                status_code=503,
            )

        # WebSocket for real-time updates
        @self.fastapi_app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket) -> None:
            await websocket.accept()
            self.websocket_clients.append(websocket)

            try:
                while True:
                    # Send periodic updates
                    data = {
                        "type": "stats",
                        "timestamp": datetime.utcnow().isoformat(),
                        "tasks": await get_task_stats(),
                        "dlq": await get_dlq_stats(),
                    }

                    await websocket.send_json(data)
                    await asyncio.sleep(2)  # Update every 2 seconds

            except WebSocketDisconnect:
                self.websocket_clients.remove(websocket)

    def _get_dashboard_html(self) -> str:
        """Get dashboard HTML content.

        Returns:
            HTML content for dashboard
        """
        # This will be replaced with a proper frontend file
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AioTasks Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
        }

        .header {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            margin-bottom: 30px;
        }

        .header h1 {
            color: #667eea;
            font-size: 2.5rem;
            margin-bottom: 10px;
        }

        .header p {
            color: #666;
            font-size: 1.1rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 25px rgba(0,0,0,0.15);
        }

        .stat-label {
            color: #888;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }

        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #667eea;
        }

        .content-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
        }

        .panel {
            background: white;
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }

        .panel h2 {
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }

        .task-list {
            list-style: none;
        }

        .task-item {
            padding: 15px;
            margin-bottom: 10px;
            background: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #667eea;
        }

        .task-name {
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }

        .task-meta {
            color: #666;
            font-size: 0.9rem;
        }

        .status-badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }

        .status-active {
            background: #d4edda;
            color: #155724;
        }

        .status-failed {
            background: #f8d7da;
            color: #721c24;
        }

        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 5px;
            font-size: 1rem;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn-primary {
            background: #667eea;
            color: white;
        }

        .btn-primary:hover {
            background: #5568d3;
        }

        .btn-danger {
            background: #dc3545;
            color: white;
        }

        .btn-danger:hover {
            background: #c82333;
        }

        .loading {
            text-align: center;
            padding: 40px;
            color: #888;
        }

        @media (max-width: 768px) {
            .stats-grid,
            .content-grid {
                grid-template-columns: 1fr;
            }

            .header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 AioTasks Dashboard</h1>
            <p>Modern async task queue monitoring</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Tasks</div>
                <div class="stat-value" id="stat-total">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Tasks</div>
                <div class="stat-value" id="stat-active">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Failed Tasks</div>
                <div class="stat-value" id="stat-failed">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">DLQ Size</div>
                <div class="stat-value" id="stat-dlq">-</div>
            </div>
        </div>

        <div class="content-grid">
            <div class="panel">
                <h2>⏰ Periodic Tasks</h2>
                <div id="periodic-tasks" class="loading">Loading...</div>
            </div>

            <div class="panel">
                <h2>💀 Dead Letter Queue</h2>
                <div id="dlq-tasks" class="loading">Loading...</div>
                <div style="margin-top: 20px;">
                    <button class="btn btn-primary" onclick="retryAllDLQ()">Retry All</button>
                    <button class="btn btn-danger" onclick="clearDLQ()">Clear All</button>
                </div>
            </div>
        </div>
    </div>

    <script>
        // WebSocket connection for real-time updates
        let ws;

        function connectWebSocket() {
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(`${protocol}//${window.location.host}/ws`);

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === 'stats') {
                    updateStats(data);
                }
            };

            ws.onclose = () => {
                setTimeout(connectWebSocket, 3000);
            };
        }

        function updateStats(data) {
            document.getElementById('stat-total').textContent = data.tasks.total || 0;
            document.getElementById('stat-active').textContent = data.tasks.active || 0;
            document.getElementById('stat-failed').textContent = data.tasks.failed || 0;
            document.getElementById('stat-dlq').textContent = data.tasks.dlq_size || 0;
        }

        async function loadPeriodicTasks() {
            try {
                const response = await fetch('/api/tasks/periodic');
                const data = await response.json();

                const container = document.getElementById('periodic-tasks');
                if (data.total === 0) {
                    container.innerHTML = '<p style="color: #888;">No periodic tasks configured</p>';
                    return;
                }

                container.innerHTML = '<ul class="task-list">' +
                    data.tasks.map(task => `
                        <li class="task-item">
                            <div class="task-name">${task.name}</div>
                            <div class="task-meta">
                                <span class="status-badge ${task.enabled ? 'status-active' : 'status-failed'}">
                                    ${task.enabled ? 'Enabled' : 'Disabled'}
                                </span>
                                Schedule: ${task.schedule} | Runs: ${task.total_runs}
                            </div>
                        </li>
                    `).join('') +
                    '</ul>';
            } catch (error) {
                console.error('Failed to load periodic tasks:', error);
            }
        }

        async function loadDLQTasks() {
            try {
                const response = await fetch('/api/dlq');
                const data = await response.json();

                const container = document.getElementById('dlq-tasks');
                if (data.total === 0) {
                    container.innerHTML = '<p style="color: #888;">No failed tasks</p>';
                    return;
                }

                container.innerHTML = '<ul class="task-list">' +
                    data.tasks.slice(0, 5).map(task => `
                        <li class="task-item">
                            <div class="task-name">${task.task_name}</div>
                            <div class="task-meta">
                                Error: ${task.error || 'Unknown'}<br>
                                Retries: ${task.retry_count} | Failed: ${new Date(task.failed_at).toLocaleString()}
                            </div>
                        </li>
                    `).join('') +
                    '</ul>';
            } catch (error) {
                console.error('Failed to load DLQ tasks:', error);
            }
        }

        async function retryAllDLQ() {
            if (!confirm('Retry all failed tasks?')) return;

            try {
                const response = await fetch('/api/dlq/retry-all', { method: 'POST' });
                const data = await response.json();
                alert(`Retried ${data.retried} tasks`);
                loadDLQTasks();
            } catch (error) {
                alert('Failed to retry tasks');
            }
        }

        async function clearDLQ() {
            if (!confirm('Clear all failed tasks? This cannot be undone.')) return;

            try {
                const response = await fetch('/api/dlq', { method: 'DELETE' });
                const data = await response.json();
                alert(`Cleared ${data.cleared} tasks`);
                loadDLQTasks();
            } catch (error) {
                alert('Failed to clear DLQ');
            }
        }

        // Initialize
        connectWebSocket();
        loadPeriodicTasks();
        loadDLQTasks();

        // Refresh periodic tasks and DLQ every 30 seconds
        setInterval(loadPeriodicTasks, 30000);
        setInterval(loadDLQTasks, 30000);
    </script>
</body>
</html>
        """

    async def start(self) -> None:
        """Start dashboard server."""
        try:
            import uvicorn

            config = uvicorn.Config(
                app=self.fastapi_app,
                host=self.host,
                port=self.port,
                log_level="info",
            )
            server = uvicorn.Server(config)

            log.info(f"Starting dashboard server at http://{self.host}:{self.port}")
            await server.serve()

        except ImportError:
            msg = "uvicorn not installed. Install with: pip install aiotasks[dashboard]"
            raise ImportError(msg) from None

    async def broadcast_update(self, message: dict[str, Any]) -> None:
        """Broadcast update to all WebSocket clients.

        Args:
            message: Message to broadcast
        """
        disconnected = []

        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)

        # Remove disconnected clients
        for client in disconnected:
            if client in self.websocket_clients:
                self.websocket_clients.remove(client)


def create_dashboard(
    app: AioTasks,
    host: str = "127.0.0.1",
    port: int = 5555,
    enable_cors: bool = True,
) -> DashboardServer:
    """Create dashboard server for AioTasks app.

    Args:
        app: AioTasks application
        host: Server host
        port: Server port
        enable_cors: Enable CORS

    Returns:
        DashboardServer instance

    Usage:
        >>> from aiotasks import AioTasks
        >>> from aiotasks.dashboard import create_dashboard
        >>>
        >>> app = AioTasks('myapp', broker='redis://localhost')
        >>> dashboard = create_dashboard(app, port=5555)
        >>> await dashboard.start()
    """
    return DashboardServer(app, host=host, port=port, enable_cors=enable_cors)
