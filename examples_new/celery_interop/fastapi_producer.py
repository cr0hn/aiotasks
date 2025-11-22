"""FastAPI application using AioTasks to send tasks in Celery format.

This example shows how to use AioTasks in a FastAPI application to send
tasks that can be processed by Celery workers. This enables gradual migration
from Celery to AioTasks or mixed worker deployments.

Usage:
    # Install dependencies:
    pip install fastapi uvicorn aiotasks[redis]

    # Start Redis (required for shared broker):
    docker run -d -p 6379:6379 redis:alpine

    # Start this FastAPI app:
    python fastapi_producer.py

    # In another terminal, start Celery worker:
    celery -A celery_worker worker --loglevel=info

    # Test the API:
    curl http://localhost:8000/send-email/user@example.com
"""

from fastapi import FastAPI

from aiotasks import AioTasks

# Create AioTasks app with Celery compatibility enabled
# This ensures messages are sent in Celery Protocol v2 format
tasks = AioTasks(
    name="myapp",
    broker="redis://localhost:6379/0",
    celery_compat=True,  # ✨ Enable Celery interoperability
)

# Create FastAPI app
app = FastAPI(
    title="AioTasks + Celery Interop Demo",
    description="FastAPI using AioTasks to send tasks, Celery workers to process them",
)


# Define tasks using AioTasks decorator
@tasks.task()
async def send_email(to: str, subject: str = "Hello from AioTasks") -> dict:
    """Send an email task.

    This task is defined in AioTasks but can be processed by Celery workers
    because celery_compat=True sends it in Celery Protocol v2 format.
    """
    return {"status": "sent", "to": to, "subject": subject}


@tasks.task()
async def process_data(data: dict) -> dict:
    """Process data task."""
    return {"status": "processed", "data": data}


@tasks.task()
async def generate_report(report_id: int) -> dict:
    """Generate report task."""
    return {"status": "generated", "report_id": report_id}


# FastAPI endpoints
@app.post("/send-email/{email}")
async def api_send_email(email: str, subject: str = "Hello"):
    """Queue an email task.

    The task will be sent in Celery format and can be processed by either:
    - Celery workers (gradual migration, mixed deployment)
    - AioTasks workers (full async/await benefits)
    """
    # Queue the task using AioTasks
    await send_email.delay(email, subject=subject)

    return {
        "message": "Email task queued",
        "format": "Celery Protocol v2",
        "email": email,
        "subject": subject,
    }


@app.post("/process-data")
async def api_process_data(data: dict):
    """Queue a data processing task."""
    await process_data.delay(data)

    return {
        "message": "Processing task queued",
        "format": "Celery Protocol v2",
        "data": data,
    }


@app.post("/generate-report/{report_id}")
async def api_generate_report(report_id: int):
    """Queue a report generation task."""
    await generate_report.delay(report_id)

    return {
        "message": "Report generation task queued",
        "format": "Celery Protocol v2",
        "report_id": report_id,
    }


@app.get("/")
async def root():
    """API information."""
    return {
        "message": "AioTasks + Celery Interoperability Demo",
        "features": [
            "FastAPI sends tasks using AioTasks API",
            "Tasks are formatted in Celery Protocol v2",
            "Celery workers can process the tasks",
            "Enables gradual migration from Celery to AioTasks",
        ],
        "endpoints": {
            "POST /send-email/{email}": "Queue email task",
            "POST /process-data": "Queue data processing task",
            "POST /generate-report/{report_id}": "Queue report task",
        },
    }


@app.on_event("shutdown")
async def shutdown():
    """Clean shutdown of AioTasks."""
    tasks.stop()


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting FastAPI with AioTasks (Celery-compatible mode)")
    print("📮 Tasks will be sent in Celery Protocol v2 format")
    print("🔄 Celery workers can process these tasks")
    print("\nAPI available at: http://localhost:8000")
    print("API docs at: http://localhost:8000/docs\n")

    uvicorn.run(app, host="0.0.0.0", port=8000)
