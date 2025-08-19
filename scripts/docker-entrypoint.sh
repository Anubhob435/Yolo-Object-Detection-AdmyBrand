#!/bin/bash

# Docker entrypoint script for YOLO Object Detection

set -e

echo "🐳 Starting YOLO Object Detection Container..."

# Check if SSL certificates exist, if not create them
if [ ! -f "/app/certs/cert.pem" ] || [ ! -f "/app/certs/key.pem" ]; then
    echo "📜 Generating SSL certificates..."
    mkdir -p /app/certs
    openssl req -x509 -newkey rsa:4096 -keyout /app/certs/key.pem -out /app/certs/cert.pem -days 365 -nodes \
        -subj "/C=US/ST=State/L=City/O=YoloDetection/CN=localhost"
    echo "✅ SSL certificates generated"
fi

# Check if YOLO model exists, if not it will be downloaded on first run
if [ ! -f "/app/models/yolov8n.pt" ]; then
    echo "📥 YOLO model will be downloaded on first inference..."
    mkdir -p /app/models
fi

# Get container IP for QR code generation
CONTAINER_IP=$(hostname -I | awk '{print $1}')
export CONTAINER_IP

echo "🌐 Container IP: $CONTAINER_IP"
echo "🔒 HTTPS Server will start on port 8443"
echo "📱 Access mobile interface at: https://$CONTAINER_IP:8443/realtime"
echo "🖥️  Access desktop interface at: https://localhost:8443"

# Start the application
echo "🚀 Starting YOLO Object Detection Server..."
exec "$@"
