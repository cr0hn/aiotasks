"""Basic FastAPI application with aiotasks integration."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

from aiotasks.integrations.fastapi import aiotasks_lifespan


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):  # type: ignore[no-untyped-def]
    """Manage aiotasks lifecycle."""
    async with aiotasks_lifespan(
        app,
        dsn="memory://",  # Use memory backend for this example
        prefix="myapp",
    ) as state:
        yield state


# Create FastAPI app
app = FastAPI(
    title="AioTasks FastAPI Example",
    description="Demonstrating background task processing with aiotasks",
    version="1.0.0",
    lifespan=lifespan,
)


# Define task models
class EmailTask(BaseModel):
    """Email task data."""

    to: EmailStr
    subject: str
    body: str


class DataProcessingTask(BaseModel):
    """Data processing task."""

    data_id: int
    operation: str


# Define background tasks
@app.state.aiotasks.task()  # type: ignore[attr-defined]
async def send_email(to: str, subject: str, body: str) -> None:
    """Send an email asynchronously.

    Args:
        to: Recipient email address
        subject: Email subject
        body: Email body
    """
    print(f"Sending email to {to}")
    print(f"Subject: {subject}")
    await asyncio.sleep(2)  # Simulate email sending
    print(f"Email sent to {to}!")


@app.state.aiotasks.task()  # type: ignore[attr-defined]
async def process_data(data_id: int, operation: str) -> None:
    """Process data asynchronously.

    Args:
        data_id: ID of the data to process
        operation: Operation to perform
    """
    print(f"Processing data {data_id} with operation: {operation}")
    await asyncio.sleep(3)  # Simulate processing
    print(f"Data {data_id} processed successfully!")


# API Endpoints
@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Welcome to AioTasks FastAPI Example",
        "docs": "/docs",
    }


@app.post("/tasks/email")
async def create_email_task(email_task: EmailTask) -> dict[str, str]:
    """Queue an email sending task.

    Args:
        email_task: Email task data

    Returns:
        Task status message
    """
    try:
        await send_email.delay(  # type: ignore[attr-defined]
            email_task.to,
            email_task.subject,
            email_task.body,
        )
        return {
            "status": "queued",
            "message": f"Email task queued for {email_task.to}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/tasks/process")
async def create_processing_task(task: DataProcessingTask) -> dict[str, str]:
    """Queue a data processing task.

    Args:
        task: Data processing task

    Returns:
        Task status message
    """
    try:
        await process_data.delay(  # type: ignore[attr-defined]
            task.data_id,
            task.operation,
        )
        return {
            "status": "queued",
            "message": f"Processing task queued for data {task.data_id}",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "tasks": "running"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
