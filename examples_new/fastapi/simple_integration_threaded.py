"""
FastAPI + AioTasks with in-process worker (development only).

⚠️  DEVELOPMENT ONLY - Not recommended for production!
    For production, use separate workers (see simple_integration.py)

This example shows how to run workers in the same process as the API
using a separate thread. Useful for quick testing without running separate workers.

Install:
    pip install aiotasks

Run:
    # Terminal 1: Start Redis
    docker run -d -p 6379:6379 redis:alpine

    # Terminal 2: Run the app (API + worker in same process)
    python simple_integration_threaded.py

    # Or with uvicorn
    uvicorn simple_integration_threaded:api --reload

Test:
    curl -X POST "http://localhost:8000/register?email=user@example.com&name=John"
    curl -X POST "http://localhost:8000/orders?order_id=123&user_id=1"
    curl http://localhost:8000/health

⚠️  Limitations:
    - Not scalable (single worker thread)
    - Worker competes with API for resources
    - Cannot scale workers independently
    - Not recommended for production

✅  Recommended: Use simple_integration.py with separate workers instead!
"""

import asyncio
import threading

from fastapi import FastAPI

from aiotasks import AioTasks

# Create FastAPI app and AioTasks instance
api = FastAPI(title="AioTasks Integration (Threaded Worker)")
tasks = AioTasks("api_tasks", broker="redis://localhost:6379/0", concurrency=5)


# Define background tasks
@tasks.task()
async def send_welcome_email(email: str, name: str) -> dict[str, str]:
    """Send welcome email in the background."""
    print(f"📧 Sending welcome email to {name} ({email})...")
    await asyncio.sleep(2)  # Simulate email sending
    print(f"✅ Welcome email sent to {name} ({email})")
    return {"status": "sent", "email": email}


@tasks.task()
async def process_order(order_id: int, user_id: int) -> dict[str, int | str]:
    """Process order in the background."""
    print(f"⚙️  Processing order {order_id} for user {user_id}...")
    await asyncio.sleep(5)  # Simulate heavy processing
    print(f"✅ Order {order_id} processed for user {user_id}")
    return {"order_id": order_id, "user_id": user_id, "status": "completed"}


# Start worker in a separate thread
@api.on_event("startup")
async def startup() -> None:
    """Start worker in a separate thread when the app starts.

    ⚠️  The worker runs in a thread because tasks.run() blocks.
         DO NOT call tasks.run() directly in an async function!
    """

    def run_worker() -> None:
        """Run the worker - this blocks, so it must be in a thread."""
        print("🚀 Starting worker thread...")
        tasks.run()  # This blocks - that's why it's in a thread
        print("✅ Worker stopped")

    # Start worker in daemon thread
    worker_thread = threading.Thread(target=run_worker, daemon=True, name="AioTasksWorker")
    worker_thread.start()
    print(f"✅ Worker started in thread: {worker_thread.name}")


@api.on_event("shutdown")
async def shutdown() -> None:
    """Stop worker gracefully when the app shuts down."""
    print("🛑 Stopping worker...")
    tasks.stop()
    print("✅ Worker stopped")


# API endpoints
@api.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {
        "message": "AioTasks with in-process worker (development only)",
        "warning": "Not recommended for production - use separate workers instead",
        "docs": "/docs",
        "examples": ["/register", "/orders", "/health"],
    }


@api.post("/register")
async def register_user(email: str, name: str) -> dict[str, str]:
    """Register a new user and send welcome email."""
    # Queue the task - in-process worker will process it
    await send_welcome_email.delay(email, name)

    return {
        "status": "registered",
        "message": f"Welcome email queued for {email}",
    }


@api.post("/orders")
async def create_order(order_id: int, user_id: int) -> dict[str, int | str]:
    """Create a new order."""
    # Queue the task - in-process worker will process it
    await process_order.delay(order_id, user_id)

    return {
        "order_id": order_id,
        "status": "queued",
        "message": "Order queued for processing",
    }


@api.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mode": "in-process worker (development)",
        "warning": "Use separate workers for production",
    }


if __name__ == "__main__":
    import uvicorn

    print("⚠️  Running with in-process worker (development only)")
    print("✅  For production, use: aiotasks -A simple_integration.tasks worker")
    print("")

    # Run the application
    uvicorn.run(api, host="0.0.0.0", port=8000)
