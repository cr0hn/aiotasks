"""Pool Types Example - Demonstrating async, thread, and process pools.

This example shows how to use different execution pools for different workload types:
- async pool: For I/O-bound async tasks (default)
- thread pool: For blocking I/O and sync libraries
- process pool: For CPU-intensive tasks

Run examples:
    # Async pool (default)
    python examples_new/pool_types_example.py async

    # Thread pool
    python examples_new/pool_types_example.py thread

    # Process pool
    python examples_new/pool_types_example.py process
"""

import asyncio
import sys
import time

from aiotasks import AioTasks

# =============================================================================
# ASYNC POOL EXAMPLE (Default)
# =============================================================================

app_async = AioTasks("pool_async", broker="memory://", pool="async")


@app_async.task()
async def io_bound_task(url: str) -> str:
    """I/O-bound task - best for async pool."""
    await asyncio.sleep(1)  # Simulate async I/O
    return f"Downloaded {url}"


# =============================================================================
# THREAD POOL EXAMPLE
# =============================================================================

app_thread = AioTasks("pool_thread", broker="memory://", pool="thread", concurrency=10)


@app_thread.task()
def blocking_io_task(file_path: str) -> str:
    """Blocking I/O task - best for thread pool."""
    time.sleep(1)  # Simulate blocking I/O
    return f"Processed {file_path}"


# =============================================================================
# PROCESS POOL EXAMPLE
# =============================================================================

app_process = AioTasks("pool_process", broker="memory://", pool="process", concurrency=4)


@app_process.task()
def cpu_intensive_task(n: int) -> int:
    """CPU-intensive task - best for process pool."""
    # Simulate CPU-intensive computation
    result = sum(i * i for i in range(n))
    return result


# =============================================================================
# MAIN DEMO
# =============================================================================


async def demo_async_pool():
    """Demo async pool for I/O-bound async tasks."""
    print("\n" + "=" * 60)
    print("ASYNC POOL DEMO - I/O-bound async tasks")
    print("=" * 60)
    print(f"Pool type: {app_async._manager.pool}")
    print(f"Concurrency: {app_async._manager.task_concurrency}")
    print()

    # Queue tasks
    tasks = []
    for i in range(5):
        task = await io_bound_task.delay(f"https://example.com/page{i}")
        tasks.append(task)

    print(f"Queued {len(tasks)} async I/O tasks")
    print("Workers will process them concurrently using asyncio...")


async def demo_thread_pool():
    """Demo thread pool for blocking I/O tasks."""
    print("\n" + "=" * 60)
    print("THREAD POOL DEMO - Blocking I/O tasks")
    print("=" * 60)
    print(f"Pool type: {app_thread._manager.pool}")
    print(f"Concurrency: {app_thread._manager.task_concurrency}")
    print()

    # Queue tasks
    tasks = []
    for i in range(5):
        task = await blocking_io_task.delay(f"/data/file{i}.dat")
        tasks.append(task)

    print(f"Queued {len(tasks)} blocking I/O tasks")
    print("Workers will process them using ThreadPoolExecutor...")


async def demo_process_pool():
    """Demo process pool for CPU-intensive tasks."""
    print("\n" + "=" * 60)
    print("PROCESS POOL DEMO - CPU-intensive tasks")
    print("=" * 60)
    print(f"Pool type: {app_process._manager.pool}")
    print(f"Concurrency: {app_process._manager.task_concurrency}")
    print()

    # Queue tasks
    tasks = []
    for i in range(4):
        task = await cpu_intensive_task.delay(1000000 * (i + 1))
        tasks.append(task)

    print(f"Queued {len(tasks)} CPU-intensive tasks")
    print("Workers will process them using ProcessPoolExecutor...")
    print("(bypasses GIL for true parallel execution)")


def main():
    """Main entry point."""
    pool_type = sys.argv[1] if len(sys.argv) > 1 else "async"

    if pool_type == "async":
        asyncio.run(demo_async_pool())
        print("\nTo run worker: aiotasks -A examples_new.pool_types_example:app_async worker")
    elif pool_type == "thread":
        asyncio.run(demo_thread_pool())
        print("\nTo run worker: aiotasks -A examples_new.pool_types_example:app_thread worker")
    elif pool_type == "process":
        asyncio.run(demo_process_pool())
        print("\nTo run worker: aiotasks -A examples_new.pool_types_example:app_process worker")
    else:
        print(f"Unknown pool type: {pool_type}")
        print("Usage: python pool_types_example.py [async|thread|process]")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Example completed! Check worker output for task execution.")
    print("=" * 60)


if __name__ == "__main__":
    main()
