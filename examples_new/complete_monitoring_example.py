"""Complete monitoring example with all new features.

This example demonstrates how to use:
- Prometheus metrics
- Rate limiting
- Web dashboard
- Periodic tasks
- Dead Letter Queue
- Result backend

All integrated in a single application.

Requirements:
    pip install aiotasks[all]
    # or
    pip install aiotasks[monitoring,dashboard]
"""

import asyncio
import random

from aiotasks import AioTasks, crontab, every, rate_limit


async def main():
    print("=" * 70)
    print(" " * 15 + "🚀 AioTasks Complete Monitoring Demo")
    print("=" * 70)
    print()

    # Create AioTasks app with full configuration
    app = AioTasks(
        name="production_app",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0",  # Result backend
        concurrency=10,
        max_retries=3,
        pool="async",
    )

    # 1. Setup Prometheus Metrics
    print("📊 Step 1: Setting up Prometheus metrics...")
    metrics = app.setup_metrics(
        namespace="production_app", enable_http_server=True, http_port=9090
    )
    print("   ✓ Metrics server: http://localhost:9090/metrics")
    print()

    # 2. Define rate-limited tasks
    print("🚦 Step 2: Defining rate-limited tasks...")

    @app.task()
    @rate_limit("10/s", wait=True)  # Max 10 per second
    async def call_external_api(endpoint: str) -> dict:
        """Call external API with rate limiting."""
        await asyncio.sleep(random.uniform(0.1, 0.5))

        # Simulate occasional failures
        if random.random() < 0.1:
            msg = f"API error on {endpoint}"
            raise Exception(msg)

        return {"endpoint": endpoint, "status": "success", "data": "..."}

    @app.task()
    @rate_limit("50/m", wait=True)  # Max 50 per minute
    async def send_email(to: str, subject: str) -> bool:
        """Send email with rate limiting."""
        await asyncio.sleep(random.uniform(0.2, 0.8))

        # Track metrics
        if metrics:
            metrics.record_task_start("send_email")

        result = True

        if metrics:
            metrics.record_task_complete("send_email", 0.5, status="success")

        return result

    @app.task()
    async def process_payment(order_id: str, amount: float) -> dict:
        """Process payment (no rate limit, critical operation)."""
        await asyncio.sleep(random.uniform(1.0, 2.0))

        # Simulate occasional payment failures
        if random.random() < 0.05:
            msg = f"Payment gateway error for order {order_id}"
            raise Exception(msg)

        return {"order_id": order_id, "amount": amount, "status": "completed"}

    @app.task()
    async def generate_analytics() -> dict:
        """Generate analytics report."""
        await asyncio.sleep(3)
        return {
            "total_users": random.randint(1000, 10000),
            "active_sessions": random.randint(100, 500),
            "revenue": random.uniform(10000, 50000),
        }

    print("   ✓ Tasks defined with rate limiting")
    print()

    # 3. Setup periodic tasks
    print("⏰ Step 3: Setting up periodic tasks...")

    app.add_periodic_task(
        name="api_health_check",
        schedule=every(seconds=30),
        task="call_external_api",
        args=("/health",),
    )

    app.add_periodic_task(
        name="hourly_analytics",
        schedule=every(hours=1),
        task="generate_analytics",
    )

    app.add_periodic_task(
        name="daily_report",
        schedule=crontab(hour="9", minute="0"),
        task="generate_analytics",
    )

    print("   ✓ Periodic tasks configured")
    print()

    # 4. Submit example tasks
    print("🚀 Step 4: Submitting example tasks...")

    # API calls (rate limited to 10/s)
    api_tasks = []
    for i in range(30):
        api_tasks.append(call_external_api.delay(f"/api/endpoint/{i}"))

    # Emails (rate limited to 50/m)
    email_tasks = []
    for i in range(20):
        email_tasks.append(
            send_email.delay(f"user{i}@example.com", "Important notification")
        )

    # Payments (no rate limit)
    payment_tasks = []
    for i in range(10):
        payment_tasks.append(
            process_payment.delay(f"order_{i}", random.uniform(10.0, 1000.0))
        )

    print(f"   ✓ Submitted {len(api_tasks)} API calls")
    print(f"   ✓ Submitted {len(email_tasks)} emails")
    print(f"   ✓ Submitted {len(payment_tasks)} payments")
    print()

    # Wait a bit for tasks to process
    await asyncio.sleep(2)

    # 5. Check DLQ for failed tasks
    print("💀 Step 5: Checking Dead Letter Queue...")
    dlq_stats = app.get_dlq_stats()
    print(f"   Total failed tasks: {dlq_stats.get('total_tasks', 0)}")
    if dlq_stats.get("by_task_name"):
        print("   Failed by task:")
        for task_name, count in dlq_stats["by_task_name"].items():
            print(f"     - {task_name}: {count}")
    print()

    # 6. Show dashboard info
    print("🎨 Step 6: Starting web dashboard...")
    print()
    print("=" * 70)
    print("  Dashboard URL: http://localhost:5555")
    print("  Metrics URL:   http://localhost:9090/metrics")
    print("=" * 70)
    print()
    print("Features available:")
    print("  ✓ Real-time task monitoring")
    print("  ✓ Prometheus metrics")
    print("  ✓ Rate limiting statistics")
    print("  ✓ Periodic task management")
    print("  ✓ DLQ visualization and retry")
    print("  ✓ Worker statistics")
    print("  ✓ Live WebSocket updates")
    print()
    print("Example Grafana dashboards:")
    print("  - Task throughput: rate(aiotasks_tasks_total[5m])")
    print("  - Success rate: aiotasks_tasks_total{status='success'}")
    print("  - P95 latency: histogram_quantile(0.95, aiotasks_task_duration_seconds)")
    print("  - DLQ size: aiotasks_dlq_size")
    print()
    print("Press Ctrl+C to stop...")
    print()

    # Start dashboard (blocking)
    try:
        await app.start_dashboard(host="0.0.0.0", port=5555)
    except KeyboardInterrupt:
        print("\n")
        print("=" * 70)
        print("Shutdown Summary:")
        print("=" * 70)

        # Show final stats
        final_stats = app.get_dlq_stats()
        print(f"Total failed tasks: {final_stats.get('total_tasks', 0)}")

        periodic_tasks = app.list_periodic_tasks()
        print(f"Periodic tasks: {len(periodic_tasks)}")
        for task in periodic_tasks:
            print(f"  - {task.name}: {task.total_runs} runs")

        print()
        print("👋 Goodbye!")


if __name__ == "__main__":
    print()
    print("Prerequisites:")
    print("  • Redis server running on localhost:6379")
    print("  • pip install aiotasks[all]")
    print()
    input("Press Enter to start the demo...")
    print()

    try:
        asyncio.run(main())
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure Redis is running:")
        print("  docker run -d -p 6379:6379 redis:alpine")
