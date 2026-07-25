FROM python:3.13-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# RocketMQ's official Python client wraps librocketmq.
RUN curl -fsSL \
    https://github.com/apache/rocketmq-client-cpp/releases/download/2.0.0/rocketmq-client-cpp-2.0.0.amd64.deb \
    -o /tmp/librocketmq.deb \
    && apt-get update \
    && apt-get install -y --no-install-recommends /tmp/librocketmq.deb \
    && rm -f /tmp/librocketmq.deb \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt requirements-mq.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-mq.txt

# Application
COPY . .

# Create a non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
