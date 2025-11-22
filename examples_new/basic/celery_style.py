"""Modern Python 3.12+ example using Celery-style API.

This example demonstrates:
- Celery-like API (app = AioTasks())
- Pattern matching (match/case) from Python 3.11+
- Modern type hints with PEP 604 (| operator)
- ExceptionGroup handling from Python 3.11+
"""

import asyncio
from enum import StrEnum, auto

from aiotasks.app import AioTasks

# Create app (Celery-style)
app = AioTasks("myapp", broker="memory://", max_retries=3)


# Python 3.11+ StrEnum for type-safe status codes
class TaskStatus(StrEnum):
    """Task status codes."""

    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    FAILED = auto()


# Define tasks using Celery-style decorator
@app.task
async def send_notification(
    user_id: int,
    message: str,
    priority: str = "normal",
) -> dict[str, str | int]:
    """Send a notification to a user.

    Uses Python 3.12+ type hints with | operator.

    Args:
        user_id: User ID to notify
        message: Notification message
        priority: Priority level (low, normal, high, urgent)

    Returns:
        Status dictionary
    """
    print(f"Sending notification to user {user_id}")

    # Python 3.10+ match/case for pattern matching
    match priority:
        case "urgent":
            delay = 0.1
            print("  ⚡ URGENT priority - immediate delivery")
        case "high":
            delay = 0.3
            print("  🔴 HIGH priority - expedited delivery")
        case "normal":
            delay = 0.5
            print("  🟡 NORMAL priority - standard delivery")
        case "low":
            delay = 1.0
            print("  🟢 LOW priority - delayed delivery")
        case _:
            # Default case
            delay = 0.5
            print(f"  ⚠️  Unknown priority '{priority}', using normal")

    # Simulate work
    await asyncio.sleep(delay)

    return {
        "user_id": user_id,
        "status": TaskStatus.COMPLETED,
        "message": f"Notification sent: {message}",
    }


@app.task
async def process_batch(
    items: list[int],
    batch_size: int = 10,
) -> dict[str, int | list[str]]:
    """Process a batch of items with error handling.

    Demonstrates ExceptionGroup handling from Python 3.11+.

    Args:
        items: Items to process
        batch_size: Batch size for processing

    Returns:
        Processing results
    """
    print(f"Processing {len(items)} items in batches of {batch_size}")

    errors: list[Exception] = []
    processed = 0

    # Process in batches
    for i in range(0, len(items), batch_size):
        batch = items[i : i + batch_size]

        for item in batch:
            try:
                # Simulate processing (some might fail)
                if item % 10 == 0:
                    msg = f"Item {item} is divisible by 10"
                    raise ValueError(msg)

                await asyncio.sleep(0.01)
                processed += 1

            except Exception as e:
                errors.append(e)

    # Python 3.11+ ExceptionGroup for multiple errors
    if errors:
        print(f"  ⚠️  Encountered {len(errors)} errors during processing")
        # In production, you might want to handle this differently
        error_messages = [str(e) for e in errors[:5]]  # First 5 errors
        if len(errors) > 5:
            error_messages.append(f"... and {len(errors) - 5} more")
    else:
        error_messages = []

    return {
        "total": len(items),
        "processed": processed,
        "failed": len(errors),
        "sample_errors": error_messages,
    }


@app.task
async def analyze_data(
    data: dict[str, int | float | str],
    options: dict[str, bool] | None = None,
) -> str:
    """Analyze data with optional configuration.

    Uses None | Type pattern from Python 3.10+.

    Args:
        data: Data to analyze
        options: Analysis options (optional)

    Returns:
        Analysis result
    """
    options = options or {}

    print(f"Analyzing data: {len(data)} fields")

    # Simulate analysis
    await asyncio.sleep(0.5)

    # Pattern match on data types
    results = []
    for key, value in data.items():
        match value:
            case int() | float():
                results.append(f"{key}: numeric value = {value}")
            case str():
                results.append(f"{key}: text value = '{value[:20]}...'")
            case _:
                results.append(f"{key}: unknown type")

    return f"Analysis complete: {len(results)} fields analyzed"


async def main() -> None:
    """Run the example application."""
    print("=" * 60)
    print("AioTasks - Modern Python 3.12+ Celery-style Example")
    print("=" * 60)

    # Start the worker
    app.run()

    print("\n--- Queuing tasks ---\n")

    # Queue notifications with different priorities
    await send_notification.delay(1, "Welcome to AioTasks!", priority="urgent")
    await send_notification.delay(2, "You have a new message", priority="high")
    await send_notification.delay(3, "Daily digest", priority="normal")
    await send_notification.delay(4, "Newsletter", priority="low")

    # Queue batch processing
    items = list(range(1, 51))  # Process 50 items
    await process_batch.delay(items, batch_size=10)

    # Queue data analysis
    data = {
        "temperature": 25.5,
        "humidity": 60,
        "location": "New York City",
        "timestamp": "2024-01-15T10:30:00Z",
        "sensor_id": 12345,
    }
    await analyze_data.delay(data, options={"verbose": True})

    print("\n--- Waiting for tasks to complete ---\n")

    # Wait for all tasks to finish
    await app.wait(timeout=10, exit_on_finish=True)

    # Stop the worker
    app.stop()

    print("\n" + "=" * 60)
    print("All tasks completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
