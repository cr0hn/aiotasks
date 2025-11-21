"""Simple task example using memory backend."""

import asyncio

from aiotasks import build_manager


async def main() -> None:
    """Run a simple task example."""
    # Create manager with memory backend (for development/testing)
    manager = build_manager("memory://")

    # Define a task
    @manager.task()
    async def greet(name: str) -> None:
        """Greet someone after a delay."""
        print(f"Processing greeting for {name}...")
        await asyncio.sleep(1)
        print(f"Hello, {name}!")

    # Start the manager
    manager.run()

    print("Queuing tasks...")

    # Queue multiple tasks
    await greet.delay("Alice")
    await greet.delay("Bob")
    await greet.delay("Charlie")

    print("Tasks queued! Waiting for completion...")

    # Wait for all tasks to complete
    await manager.wait(timeout=10, exit_on_finish=True)

    # Stop the manager
    manager.stop()

    print("All done!")


if __name__ == "__main__":
    asyncio.run(main())
