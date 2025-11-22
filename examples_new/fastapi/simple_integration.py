"""
Simple FastAPI + AioTasks integration.

RECOMMENDED: Run API and workers separately (this example).
ALTERNATIVE: For development, see simple_integration_threaded.py

This example shows the recommended way: API sends tasks, workers run separately.

Install:
    pip install aiotasks

Run:
    # Terminal 1: Start Redis
    docker run -d -p 6379:6379 redis:alpine

    # Terminal 2: Run the FastAPI app (API only, no workers)
    uvicorn simple_integration:api --reload

    # Terminal 3: Run workers separately (recommended!)
    aiotasks -A simple_integration.tasks worker -l INFO -c 10

Test:
    curl -X POST "http://localhost:8000/register?email=user@example.com&name=John"
    curl -X POST "http://localhost:8000/orders?order_id=123&user_id=1"
    curl http://localhost:8000/health
"""

import asyncio

from fastapi import FastAPI

from aiotasks import AioTasks

# Create FastAPI app and AioTasks instance
api = FastAPI(title="Simple AioTasks Integration")
tasks = AioTasks("api_tasks", broker="redis://localhost:6379/0")


# Define background tasks
@tasks.task()
async def send_welcome_email(email: str, name: str) -> dict[str, str]:
    """Send welcome email in the background.

    This will be executed by separate workers.
    The API just queues the task and responds immediately.
    """
    print(f"📧 Sending welcome email to {name} ({email})...")
    await asyncio.sleep(2)  # Simulate email sending
    print(f"✅ Welcome email sent to {name} ({email})")
    return {"status": "sent", "email": email}


@tasks.task()
async def process_order(order_id: int, user_id: int) -> dict[str, int | str]:
    """Process order in the background.

    Heavy processing executed by workers, not blocking the API.
    """
    print(f"⚙️  Processing order {order_id} for user {user_id}...")
    await asyncio.sleep(5)  # Simulate heavy processing
    print(f"✅ Order {order_id} processed for user {user_id}")
    return {"order_id": order_id, "user_id": user_id, "status": "completed"}


# API endpoints - they just queue tasks!
@api.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "Welcome to AioTasks + FastAPI",
        "docs": "/docs",
        "examples": ["/register", "/orders", "/health"],
    }


@api.post("/register")
async def register_user(email: str, name: str) -> dict[str, str]:
    """Register a new user and send welcome email.

    The API just queues the task - workers will process it.
    This endpoint responds immediately.
    """
    # Queue the task - workers will process it
    await send_welcome_email.delay(email, name)

    return {
        "status": "registered",
        "message": f"Welcome email queued for {email}",
    }


@api.post("/orders")
async def create_order(order_id: int, user_id: int) -> dict[str, int | str]:
    """Create a new order.

    The API just queues the task - workers will process it.
    This endpoint responds immediately.
    """
    # Queue the task - workers will process it
    await process_order.delay(order_id, user_id)

    return {
        "order_id": order_id,
        "status": "queued",
        "message": "Order queued for processing",
    }


@api.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # Run only the API - workers should be run separately!
    # In another terminal: aiotasks -A simple_integration.tasks worker -l INFO -c 10
    uvicorn.run(api, host="0.0.0.0", port=8000)
