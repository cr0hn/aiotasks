"""Example: Rate limiting with AioTasks.

This example demonstrates how to use rate limiting to control
task execution rates and protect external APIs.

Requirements:
    pip install aiotasks
"""

import asyncio
import time

from aiotasks import AioTasks, rate_limit


async def main():
    # Create AioTasks app
    app = AioTasks("ratelimit_app", broker="memory://")

    print("🚦 Rate Limiting Example")
    print("=" * 50)
    print()

    # Example 1: Using rate_limit decorator
    @rate_limit("5/s")  # Max 5 per second
    async def api_call(endpoint: str) -> dict:
        """Call external API (rate limited)."""
        print(f"  📞 Calling API: {endpoint}")
        return {"status": "success", "endpoint": endpoint}

    # Example 2: Using rate_limit with Redis backend
    @rate_limit("10/m", backend="memory")  # Max 10 per minute
    async def send_sms(phone: str, message: str) -> bool:
        """Send SMS (rate limited)."""
        print(f"  📱 Sending SMS to {phone}")
        return True

    # Example 3: Rate limiting on tasks
    @app.task()
    @rate_limit("3/s", wait=True, timeout=10.0)  # Wait up to 10 seconds
    async def process_item(item_id: int) -> str:
        """Process item with rate limiting."""
        print(f"  ⚙️  Processing item {item_id}")
        await asyncio.sleep(0.1)
        return f"processed_{item_id}"

    # Test Example 1: API calls
    print("Example 1: API Calls (5/second)")
    print("-" * 50)
    start_time = time.time()

    tasks = []
    for i in range(15):  # Try 15 calls (should take ~3 seconds)
        tasks.append(api_call(f"/endpoint/{i}"))

    await asyncio.gather(*tasks)
    elapsed = time.time() - start_time

    print(f"✅ Completed 15 API calls in {elapsed:.2f} seconds")
    print(f"   (Expected ~3 seconds due to 5/second limit)")
    print()

    # Test Example 2: SMS sending
    print("Example 2: SMS Sending (10/minute)")
    print("-" * 50)
    start_time = time.time()

    sms_tasks = []
    for i in range(5):
        sms_tasks.append(send_sms(f"+1234567890{i}", "Hello!"))

    await asyncio.gather(*sms_tasks)
    elapsed = time.time() - start_time

    print(f"✅ Sent 5 SMS messages in {elapsed:.2f} seconds")
    print()

    # Test Example 3: Task processing with rate limit
    print("Example 3: Task Processing (3/second)")
    print("-" * 50)
    start_time = time.time()

    process_tasks = []
    for i in range(9):  # Try 9 tasks (should take ~3 seconds)
        process_tasks.append(process_item(i))

    await asyncio.gather(*process_tasks)
    elapsed = time.time() - start_time

    print(f"✅ Processed 9 items in {elapsed:.2f} seconds")
    print(f"   (Expected ~3 seconds due to 3/second limit)")
    print()

    # Example 4: Rate limiting with timeout
    print("Example 4: Rate Limiting with Timeout")
    print("-" * 50)

    @rate_limit("2/s", wait=True, timeout=2.0)
    async def slow_task(task_id: int) -> str:
        print(f"  🐌 Executing slow task {task_id}")
        return f"result_{task_id}"

    try:
        # Submit 10 tasks with 2/second limit and 2-second timeout
        # Some should timeout
        timeout_tasks = []
        for i in range(10):
            timeout_tasks.append(slow_task(i))

        results = await asyncio.gather(*timeout_tasks, return_exceptions=True)

        successful = sum(1 for r in results if not isinstance(r, Exception))
        failed = sum(1 for r in results if isinstance(r, Exception))

        print(f"✅ Successful: {successful}, ❌ Timeout: {failed}")
        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        print()

    # Example 5: Different rate formats
    print("Example 5: Different Rate Formats")
    print("-" * 50)
    print()

    from aiotasks.rate_limit import RateLimit

    # Parse different rate formats
    rates = [
        "10/s",  # 10 per second
        "100/m",  # 100 per minute
        "1000/h",  # 1000 per hour
        "10000/d",  # 10000 per day
    ]

    print("Supported rate formats:")
    for rate_str in rates:
        rate = RateLimit.parse(rate_str)
        print(f"  {rate_str:12s} -> {rate.limit} executions per {rate.period:.0f} seconds")

    print()
    print("✨ Rate limiting examples completed!")
    print()
    print("Benefits of rate limiting:")
    print("  ✓ Protect external APIs from overload")
    print("  ✓ Comply with API rate limits")
    print("  ✓ Control resource consumption")
    print("  ✓ Prevent service disruption")
    print("  ✓ Smooth traffic distribution")


if __name__ == "__main__":
    asyncio.run(main())
