"""AioTasks worker that processes tasks sent by FastAPI.

This demonstrates that AioTasks workers can also process the same tasks,
enabling mixed deployments where you can choose the best worker for each task:
- AioTasks workers: Best for async I/O-bound tasks
- Celery workers: Best for CPU-intensive or legacy tasks

Usage:
    # Install dependencies:
    pip install aiotasks[redis]

    # Start Redis:
    docker run -d -p 6379:6379 redis:alpine

    # Start this AioTasks worker:
    python aiotasks_worker.py

    # Send tasks from FastAPI app:
    python fastapi_producer.py
    # Then POST to http://localhost:8000/send-email/user@example.com
"""

import asyncio

from aiotasks import AioTasks

# Create AioTasks worker with Celery compatibility
# This allows it to process messages sent in Celery format
tasks = AioTasks(
    name="myapp",  # Same name as FastAPI producer
    broker="redis://localhost:6379/0",
    celery_compat=True,  # Can process both Celery and AioTasks formats
    concurrency=10,
)


# Define the same tasks as async functions
@tasks.task()
async def send_email(to: str, subject: str = "Hello from AioTasks") -> dict:
    """Process send_email task using async/await.

    This async version can handle many concurrent emails efficiently
    without blocking the worker.
    """
    print("📧 [AioTasks Worker] Processing send_email task")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")

    # Simulate async email sending (non-blocking I/O)
    await asyncio.sleep(1)

    result = {
        "status": "sent",
        "to": to,
        "subject": subject,
        "processed_by": "AioTasks Worker (async)",
    }

    print("   ✅ Email sent successfully (async)")
    return result


@tasks.task()
async def process_data(data: dict) -> dict:
    """Process data task asynchronously."""
    print("📊 [AioTasks Worker] Processing data task")
    print(f"   Data: {data}")

    # Simulate async data processing
    await asyncio.sleep(2)

    result = {
        "status": "processed",
        "data": data,
        "processed_by": "AioTasks Worker (async)",
        "processing_time": 2.0,
    }

    print("   ✅ Data processed successfully (async)")
    return result


@tasks.task()
async def generate_report(report_id: int) -> dict:
    """Generate report asynchronously."""
    print("📄 [AioTasks Worker] Generating report")
    print(f"   Report ID: {report_id}")

    # Simulate async report generation
    await asyncio.sleep(3)

    result = {
        "status": "generated",
        "report_id": report_id,
        "processed_by": "AioTasks Worker (async)",
        "file_path": f"/reports/report_{report_id}.pdf",
    }

    print("   ✅ Report generated successfully (async)")
    return result


async def main():
    """Run the AioTasks worker."""
    print("🚀 Starting AioTasks Worker (Celery-compatible)")
    print("📮 Can process tasks from both AioTasks and Celery producers")
    print("⚡ Using async/await for efficient concurrent processing\n")

    # Start processing tasks
    tasks.run()

    # Wait for tasks
    try:
        await tasks.wait(exit_on_finish=False)
    except KeyboardInterrupt:
        print("\n👋 Shutting down AioTasks worker...")
        tasks.stop()


if __name__ == "__main__":
    asyncio.run(main())
