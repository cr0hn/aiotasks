"""Example: Web Dashboard for AioTasks.

This example demonstrates the modern monitoring dashboard
with FastAPI backend and responsive frontend.

Requirements:
    pip install aiotasks[dashboard]
"""

import asyncio

from aiotasks import AioTasks, crontab, every


async def main():
    # Create AioTasks app with Redis broker
    app = AioTasks(
        "dashboard_app",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0",  # Enable result backend
    )

    print("🎨 AioTasks Dashboard Example")
    print("=" * 60)
    print()

    # Define example tasks
    @app.task()
    async def process_order(order_id: str) -> dict:
        """Process customer order."""
        await asyncio.sleep(2)
        return {"order_id": order_id, "status": "completed", "total": 99.99}

    @app.task()
    async def send_notification(user_id: int, message: str) -> bool:
        """Send user notification."""
        await asyncio.sleep(0.5)
        return True

    @app.task()
    async def generate_report(report_type: str) -> str:
        """Generate analytics report."""
        await asyncio.sleep(3)
        return f"report_{report_type}.pdf"

    @app.task()
    async def failing_task(should_fail: bool = True) -> str:
        """Task that sometimes fails (for DLQ demo)."""
        await asyncio.sleep(1)
        if should_fail:
            msg = "Simulated error for DLQ demonstration"
            raise ValueError(msg)
        return "success"

    # Setup periodic tasks for demonstration
    print("⏰ Setting up periodic tasks...")

    # Task that runs every 30 seconds
    app.add_periodic_task(
        name="frequent_check",
        schedule=every(seconds=30),
        task="process_order",
        args=("periodic_order_1",),
    )

    # Task that runs every 5 minutes
    app.add_periodic_task(
        name="notifications_batch",
        schedule=every(minutes=5),
        task="send_notification",
        args=(123, "Batch notification"),
    )

    # Task that runs daily at 9:00 AM
    app.add_periodic_task(
        name="daily_report",
        schedule=crontab(hour="9", minute="0"),
        task="generate_report",
        args=("daily",),
    )

    # Task that runs every Monday at 8:00 AM
    app.add_periodic_task(
        name="weekly_summary",
        schedule=crontab(hour="8", minute="0", day_of_week="1"),
        task="generate_report",
        args=("weekly",),
    )

    print("✅ Periodic tasks configured")
    print()

    # Submit some example tasks
    print("🚀 Submitting example tasks...")

    # Successful tasks
    for i in range(5):
        await process_order.delay(f"order_{i}")

    for i in range(10):
        await send_notification.delay(i, f"Notification {i}")

    # Some failing tasks (will go to DLQ)
    for i in range(3):
        try:
            await failing_task.delay(should_fail=True)
        except Exception:
            pass

    print("✅ Tasks submitted")
    print()

    # Start the dashboard
    print("🌐 Starting web dashboard...")
    print()
    print("=" * 60)
    print("  Dashboard URL: http://localhost:5555")
    print("=" * 60)
    print()
    print("Dashboard Features:")
    print("  📊 Real-time task statistics")
    print("  ⏰ Periodic tasks overview")
    print("  💀 Dead Letter Queue management")
    print("  📈 Task execution metrics")
    print("  🔄 Live WebSocket updates")
    print("  📱 Responsive mobile-friendly design")
    print()
    print("API Endpoints:")
    print("  GET  /api/app           - Application info")
    print("  GET  /api/workers       - Workers status")
    print("  GET  /api/tasks/stats   - Task statistics")
    print("  GET  /api/tasks/periodic - Periodic tasks")
    print("  GET  /api/dlq           - Failed tasks (DLQ)")
    print("  POST /api/dlq/{id}/retry - Retry specific task")
    print("  POST /api/dlq/retry-all - Retry all failed tasks")
    print("  DELETE /api/dlq         - Clear DLQ")
    print("  GET  /api/metrics       - Prometheus metrics")
    print("  WS   /ws                - WebSocket for real-time updates")
    print()
    print("Press Ctrl+C to stop the dashboard...")
    print()

    # Start dashboard (this will block)
    try:
        await app.start_dashboard(host="0.0.0.0", port=5555)
    except KeyboardInterrupt:
        print("\n👋 Shutting down dashboard...")


# For running with uvicorn directly
def create_app():
    """Create FastAPI app for uvicorn."""
    app = AioTasks("dashboard_app", broker="redis://localhost:6379/0")

    # Define tasks
    @app.task()
    async def example_task(data: str) -> str:
        await asyncio.sleep(1)
        return f"processed: {data}"

    # Setup dashboard
    dashboard = app.setup_dashboard(host="0.0.0.0", port=5555)
    return dashboard.fastapi_app


if __name__ == "__main__":
    print()
    print("💡 Tip: You can also run the dashboard with uvicorn:")
    print("   uvicorn dashboard_example:create_app --reload --port 5555")
    print()

    asyncio.run(main())
