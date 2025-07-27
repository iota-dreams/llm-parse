# syntax=docker/dockerfile:1.4

FROM python:3.11.9-slim-bookworm

LABEL maintainer="Srikanth Sripada <srikanth6991@gmail.com>"

# Environment configs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app
# Copy core application folders
COPY src/ src/
COPY deploy/ deploy/
COPY app/ app/
COPY configs/ configs/

# Copy setup and requirements files first for Docker caching
COPY setup.py deploy/requirements.txt ./

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir .

# Expose FastAPI default port
EXPOSE 8000

# Start Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
