# Use Python 3.12 slim image as base
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libgl1-mesa-dev \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    gstreamer1.0-libav \
    gstreamer1.0-tools \
    libavcodec-dev \
    libavformat-dev \
    libswscale-dev \
    libavutil-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock ./

# Install uv package manager
RUN pip install uv

# Install dependencies using uv
RUN uv sync --frozen

# Copy application code
COPY . .

# Make entrypoint script executable
RUN chmod +x /app/scripts/docker-entrypoint.sh

# Create SSL certificates directory
RUN mkdir -p /app/certs

# Generate self-signed SSL certificate
RUN openssl req -x509 -newkey rsa:4096 -keyout /app/certs/key.pem -out /app/certs/cert.pem -days 365 -nodes \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Create models directory and download YOLO model
RUN mkdir -p /app/models

# Expose port
EXPOSE 8443

# Set environment variables for the application
ENV PYTHONPATH=/app
ENV YOLO_MODEL_PATH=/app/models/yolov8n.pt

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -k -f https://localhost:8443/metrics || exit 1

# Set entrypoint
ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]

# Run the application
CMD ["uv", "run", "-m", "src.server.inference"]
