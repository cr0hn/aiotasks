"""Celery worker that processes tasks sent by AioTasks.

This demonstrates that Celery workers can process tasks sent by AioTasks
when celery_compat=True is enabled. This allows for:
- Gradual migration from Celery to AioTasks
- Mixed worker deployments (some Celery, some AioTasks)
- Using existing Celery workers with new AioTasks code

Usage:
    # Install Celery:
    pip install celery redis

    # Start Redis:
    docker run -d -p 6379:6379 redis:alpine

    # Start this Celery worker:
    celery -A celery_worker worker --loglevel=info

    # Send tasks from FastAPI app:
    python fastapi_producer.py
    # Then POST to http://localhost:8000/send-email/user@example.com
"""

import time

from celery import Celery

# Create Celery app with same broker as AioTasks
# The broker must match the one in fastapi_producer.py
app = Celery(
    "myapp",  # Same name as in AioTasks
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/1",  # Optional result backend
)

# Configure Celery
app.conf.update(
    task_serializer="json",  # Match AioTasks celery_compat mode
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


# Define tasks that match the ones in fastapi_producer.py
# Note: Function names must match exactly
@app.task(name="send_email")
def send_email(to: str, subject: str = "Hello from AioTasks") -> dict:
    """Process send_email task.

    This is a Celery worker processing a task sent by AioTasks!
    Thanks to celery_compat=True, the message format is compatible.
    """
    print("📧 [Celery Worker] Processing send_email task")
    print(f"   To: {to}")
    print(f"   Subject: {subject}")

    # Simulate email sending
    time.sleep(1)

    result = {
        "status": "sent",
        "to": to,
        "subject": subject,
        "processed_by": "Celery Worker",
    }

    print("   ✅ Email sent successfully")
    return result


@app.task(name="process_data")
def process_data(data: dict) -> dict:
    """Process data task."""
    print("📊 [Celery Worker] Processing data task")
    print(f"   Data: {data}")

    # Simulate data processing
    time.sleep(2)

    result = {
        "status": "processed",
        "data": data,
        "processed_by": "Celery Worker",
        "processing_time": 2.0,
    }

    print("   ✅ Data processed successfully")
    return result


@app.task(name="generate_report")
def generate_report(report_id: int) -> dict:
    """Generate report task."""
    print("📄 [Celery Worker] Generating report")
    print(f"   Report ID: {report_id}")

    # Simulate report generation
    time.sleep(3)

    result = {
        "status": "generated",
        "report_id": report_id,
        "processed_by": "Celery Worker",
        "file_path": f"/reports/report_{report_id}.pdf",
    }

    print("   ✅ Report generated successfully")
    return result


if __name__ == "__main__":
    # This is just for demonstration - normally you'd use:
    # celery -A celery_worker worker --loglevel=info
    print("⚠️  This script should be run with the celery command:")
    print("   celery -A celery_worker worker --loglevel=info")
