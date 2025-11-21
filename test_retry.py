"""Test retry logic and ACK/NACK functionality."""

import asyncio
import sys

sys.path.insert(0, "/home/user/aiotasks")

from aiotasks.tasks.backends import build_manager


async def main():
    """Test retry logic with a failing task."""
    print("Creating manager with max_retries=2...")
    manager = build_manager("memory://", max_retries=2, task_ttl=3600)

    print(f"Manager attributes: max_retries={manager.max_retries}, task_ttl={manager.task_ttl}")

    # Create a task that fails
    attempt_count = 0

    @manager.task()
    async def failing_task():
        nonlocal attempt_count
        attempt_count += 1
        print(f"Attempt {attempt_count}: Task executing...")
        if attempt_count < 3:
            raise ValueError(f"Simulated failure on attempt {attempt_count}")
        print(f"Attempt {attempt_count}: Task succeeded!")

    # Create a task that always succeeds
    @manager.task()
    async def success_task():
        print("Success task executing...")
        await asyncio.sleep(0.1)
        print("Success task completed!")

    # Start the manager
    manager.run()

    # Queue tasks
    print("\n--- Testing successful task ---")
    await success_task.delay()

    print("\n--- Testing failing task (should retry) ---")
    await failing_task.delay()

    # Wait for completion
    await manager.wait(timeout=10, exit_on_finish=True)

    print(f"\nTotal attempts for failing task: {attempt_count}")
    print("Test completed!")

    manager.stop()


if __name__ == "__main__":
    asyncio.run(main())
