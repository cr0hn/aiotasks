FROM python:3.12-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    celery[redis] \
    redis \
    flower \
    aiotasks[redis]

# Copy application files
COPY . .

# Default command (can be overridden in docker-compose)
CMD ["python", "fastapi_producer.py"]
