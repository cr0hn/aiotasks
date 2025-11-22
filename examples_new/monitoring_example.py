"""Example: Prometheus metrics monitoring with AioTasks.

This example demonstrates how to use Prometheus metrics to monitor
task execution in real-time.

Requirements:
    pip install aiotasks[monitoring]
"""

import asyncio

from aiotasks import AioTasks


async def main():
    # Create AioTasks app with Redis broker
    app = AioTasks("monitoring_app", broker="redis://localhost:6379/0")

    # Setup Prometheus metrics with HTTP server on port 9090
    metrics = app.setup_metrics(
        namespace="myapp", enable_http_server=True, http_port=9090
    )

    print("📊 Prometheus metrics server started on http://localhost:9090/metrics")
    print()

    # Define some tasks
    @app.task()
    async def process_data(item_id: int) -> dict:
        """Process data item."""
        await asyncio.sleep(0.5)  # Simulate processing
        return {"item_id": item_id, "status": "processed"}

    @app.task()
    async def send_email(to: str, subject: str) -> bool:
        """Send email notification."""
        await asyncio.sleep(0.2)  # Simulate sending
        return True

    @app.task()
    async def failing_task(should_fail: bool = True) -> str:
        """Task that sometimes fails."""
        await asyncio.sleep(0.1)
        if should_fail:
            msg = "Intentional failure for demo"
            raise ValueError(msg)
        return "success"

    print("🚀 Submitting tasks...")
    print()

    # Submit successful tasks
    for i in range(10):
        await process_data.delay(i)

    # Submit email tasks
    for i in range(5):
        await send_email.delay(f"user{i}@example.com", "Test notification")

    # Submit some failing tasks
    for _ in range(3):
        try:
            await failing_task.delay(should_fail=True)
        except Exception:
            pass

    print("✅ Tasks submitted!")
    print()
    print("Metrics being collected:")
    print("  - aiotasks_tasks_total (by task_name, status)")
    print("  - aiotasks_tasks_failed_total (by task_name, error_type)")
    print("  - aiotasks_task_duration_seconds (histogram)")
    print("  - aiotasks_tasks_in_progress (gauge)")
    print("  - aiotasks_workers_active (gauge)")
    print("  - aiotasks_queue_length (gauge)")
    print("  - aiotasks_dlq_size (gauge)")
    print()
    print(f"📈 View metrics at: http://localhost:9090/metrics")
    print()
    print("Example Prometheus queries:")
    print("  - rate(aiotasks_tasks_total[5m])")
    print("  - histogram_quantile(0.95, aiotasks_task_duration_seconds)")
    print("  - aiotasks_tasks_failed_total")
    print()
    print("Press Ctrl+C to stop...")

    # Keep running to serve metrics
    try:
        await asyncio.sleep(3600)  # Run for 1 hour
    except KeyboardInterrupt:
        print("\n👋 Shutting down...")


if __name__ == "__main__":
    asyncio.run(main())
