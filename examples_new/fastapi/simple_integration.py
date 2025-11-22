"""
Ultra-simple FastAPI + AioTasks integration.

This example shows the simplest way to integrate AioTasks with FastAPI.
Perfect for learning and small applications.

Install:
    pip install aiotasks[fastapi,redis]

Run:
    # Start Redis
    docker run -d -p 6379:6379 redis:alpine

    # Run the app
    python simple_integration.py

    # Or with uvicorn
    uvicorn simple_integration:api --reload

Test:
    curl -X POST "http://localhost:8000/register?email=user@example.com&name=John"
    curl -X POST "http://localhost:8000/orders?order_id=123&user_id=1"
    curl http://localhost:8000/health
"""

import asyncio

from fastapi import FastAPI

from aiotasks import AioTasks

# Step 1: Create FastAPI app and AioTasks instance
api = FastAPI(title="Simple AioTasks Integration")
tasks = AioTasks("api_tasks", broker="redis://localhost:6379/0")


# Step 2: Define background tasks
@tasks.task()
async def send_welcome_email(email: str, name: str) -> dict[str, str]:
    """Send welcome email in the background.

    This runs outside the request/response cycle, so the API responds immediately.
    """
    print(f"📧 Sending welcome email to {name} ({email})...")
    await asyncio.sleep(2)  # Simulate email sending
    print(f"✅ Welcome email sent to {name} ({email})")
    return {"status": "sent", "email": email}


@tasks.task()
async def process_order(order_id: int, user_id: int) -> dict[str, int | str]:
    """Process order in the background.

    Heavy processing that doesn't block the API response.
    """
    print(f"⚙️  Processing order {order_id} for user {user_id}...")
    await asyncio.sleep(5)  # Simulate heavy processing
    print(f"✅ Order {order_id} processed for user {user_id}")
    return {"order_id": order_id, "user_id": user_id, "status": "completed"}


# Step 3: Start/stop task worker with app lifecycle
@api.on_event("startup")
async def startup() -> None:
    """Start task worker when the app starts."""
    print("🚀 Starting task worker...")
    tasks.run()  # Start processing background tasks
    print("✅ Task worker started")


@api.on_event("shutdown")
async def shutdown() -> None:
    """Stop task worker gracefully when the app shuts down."""
    print("🛑 Stopping task worker...")
    tasks.stop()  # Graceful shutdown
    print("✅ Task worker stopped")


# Your API endpoints - they respond instantly!
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

    The welcome email is sent in the background, so this endpoint
    responds immediately without waiting for the email to be sent.
    """
    # Queue the task - returns immediately
    await send_welcome_email.delay(email, name)

    return {
        "status": "registered",
        "message": f"Welcome email will be sent to {email}",
    }


@api.post("/orders")
async def create_order(order_id: int, user_id: int) -> dict[str, int | str]:
    """Create a new order.

    The heavy order processing happens in the background,
    so the API responds instantly.
    """
    # Queue the task - heavy processing happens asynchronously
    await process_order.delay(order_id, user_id)

    return {
        "order_id": order_id,
        "status": "processing",
        "message": "Order is being processed",
    }


@api.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "tasks": "running"}


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(api, host="0.0.0.0", port=8000)
