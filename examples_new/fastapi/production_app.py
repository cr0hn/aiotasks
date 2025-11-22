"""
Production-ready FastAPI + AioTasks integration.

This example shows how to run FastAPI and workers separately for production.
This architecture allows independent scaling of API servers and task workers.

Install:
    pip install aiotasks

Setup:
    # Start Redis
    docker run -d -p 6379:6379 redis:alpine

Run API servers (no workers):
    # Run multiple API servers
    uvicorn production_app:api --workers 4 --host 0.0.0.0 --port 8000

Run dedicated workers (in separate terminals/processes):
    # Terminal 1: High-priority worker
    aiotasks -A production_app.tasks worker -l INFO -c 20 -Q high

    # Terminal 2: Normal-priority worker
    aiotasks -A production_app.tasks worker -l INFO -c 10 -Q normal

    # Terminal 3: Low-priority worker
    aiotasks -A production_app.tasks worker -l INFO -c 5 -Q low

Test:
    curl -X POST "http://localhost:8000/tasks/urgent?task_id=123"
    curl -X POST "http://localhost:8000/tasks/normal?task_id=456"
    curl http://localhost:8000/health/tasks
"""

import asyncio
import logging
import os
from enum import StrEnum, auto

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from aiotasks import AioTasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


# Priority levels
class TaskPriority(StrEnum):
    """Task priority levels."""

    HIGH = auto()
    NORMAL = auto()
    LOW = auto()


# Task models
class EmailRequest(BaseModel):
    """Email request model."""

    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=200)
    body: str = Field(..., min_length=1)
    priority: TaskPriority = TaskPriority.NORMAL


class ReportRequest(BaseModel):
    """Report generation request."""

    report_id: int = Field(..., gt=0)
    user_id: int = Field(..., gt=0)
    report_type: str = Field(..., min_length=1)


# Create AioTasks instance
# NOTE: In production, workers run separately, so we DON'T call tasks.run() here
tasks = AioTasks(
    "production_app",
    broker=REDIS_URL,
    concurrency=20,  # Only used if running workers in-process
    max_retries=3,  # Retry failed tasks up to 3 times
    task_ttl=3600,  # Tasks expire after 1 hour
)


# Define background tasks
@tasks.task()
async def send_email(
    to: str, subject: str, body: str, priority: TaskPriority = TaskPriority.NORMAL
) -> dict[str, str]:
    """Send email with priority handling.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
        priority: Task priority level

    Returns:
        dict: Email send status
    """
    # Priority-based delay simulation
    match priority:
        case TaskPriority.HIGH:
            delay = 0.5
        case TaskPriority.NORMAL:
            delay = 1.0
        case TaskPriority.LOW:
            delay = 2.0

    logger.info(f"Sending {priority} priority email to {to}")
    await asyncio.sleep(delay)
    logger.info(f"Email sent to {to}")

    return {"status": "sent", "to": to, "priority": priority}


@tasks.task()
async def generate_report(report_id: int, user_id: int, report_type: str) -> dict[str, int | str]:
    """Generate heavy report asynchronously.

    Args:
        report_id: Report identifier
        user_id: User who requested the report
        report_type: Type of report to generate

    Returns:
        dict: Report generation status
    """
    logger.info(f"Generating {report_type} report {report_id} for user {user_id}")

    # Simulate heavy processing
    await asyncio.sleep(10)

    logger.info(f"Report {report_id} generated successfully")

    return {
        "report_id": report_id,
        "user_id": user_id,
        "report_type": report_type,
        "status": "completed",
    }


@tasks.task()
async def cleanup_old_data(days: int = 30) -> dict[str, int]:
    """Cleanup old data (scheduled task).

    Args:
        days: Number of days to keep

    Returns:
        dict: Cleanup statistics
    """
    logger.info(f"Cleaning up data older than {days} days")
    await asyncio.sleep(5)

    # Simulate cleanup
    deleted_count = 1000  # Mock value

    logger.info(f"Cleaned up {deleted_count} records")

    return {"deleted": deleted_count, "days": days}


# Create FastAPI app
api = FastAPI(
    title="Production AioTasks API",
    description="Production-ready FastAPI with separate task workers",
    version="2.0.0",
)


# NOTE: No @api.on_event("startup") to start workers!
# In production, workers run as separate processes.

# If you want to run workers in-process (development only), uncomment:
# @api.on_event("startup")
# async def startup():
#     tasks.run()


# API Endpoints
@api.get("/")
async def root() -> dict[str, str]:
    """Root endpoint with API information."""
    return {
        "service": "Production AioTasks API",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "docs": "/docs",
        "health": "/health/tasks",
    }


@api.post("/tasks/email")
async def queue_email(email: EmailRequest) -> dict[str, str]:
    """Queue an email task.

    Args:
        email: Email request data

    Returns:
        dict: Task queue status
    """
    try:
        await send_email.delay(email.to, email.subject, email.body, email.priority)

        return {
            "status": "queued",
            "message": f"Email queued with {email.priority} priority",
            "to": email.to,
        }

    except Exception as e:
        logger.error(f"Failed to queue email: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue task") from e


@api.post("/tasks/report")
async def queue_report(report: ReportRequest) -> dict[str, int | str]:
    """Queue a report generation task.

    Args:
        report: Report request data

    Returns:
        dict: Task queue status
    """
    try:
        await generate_report.delay(report.report_id, report.user_id, report.report_type)

        return {
            "status": "queued",
            "report_id": report.report_id,
            "message": "Report generation queued",
        }

    except Exception as e:
        logger.error(f"Failed to queue report: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue task") from e


@api.post("/tasks/cleanup")
async def queue_cleanup(days: int = 30) -> dict[str, str | int]:
    """Queue a cleanup task (admin only in real app).

    Args:
        days: Days to keep data

    Returns:
        dict: Task queue status
    """
    try:
        await cleanup_old_data.delay(days)

        return {"status": "queued", "days": days, "message": "Cleanup task queued"}

    except Exception as e:
        logger.error(f"Failed to queue cleanup: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue task") from e


@api.get("/health")
async def health() -> dict[str, str]:
    """Basic health check."""
    return {"status": "healthy"}


@api.get("/health/tasks")
async def task_health() -> dict[str, str | int]:
    """Task system health check."""
    return {
        "status": "healthy",
        "broker": tasks.broker_url,
        "environment": ENVIRONMENT,
        "tasks_registered": len(tasks._manager._tasks),
        "max_retries": tasks._manager.max_retries,
        "task_ttl": tasks._manager.task_ttl,
    }


@api.get("/metrics")
async def metrics() -> dict[str, int]:
    """Expose basic metrics for monitoring."""
    return {
        "tasks_total": len(tasks._manager._tasks),
        "concurrency": tasks._manager.concurrency,
        "max_retries": tasks._manager.max_retries,
    }


if __name__ == "__main__":
    import uvicorn

    # Run with single worker for development
    # In production, use: uvicorn production_app:api --workers 4
    uvicorn.run(api, host="0.0.0.0", port=8000)
