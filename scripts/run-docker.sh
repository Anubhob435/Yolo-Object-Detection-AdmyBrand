#!/bin/bash

# Run script for YOLO Object Detection Docker container

echo "🚀 Starting YOLO Object Detection Container..."

# Stop and remove existing container if it exists
docker stop yolo-object-detection 2>/dev/null || true
docker rm yolo-object-detection 2>/dev/null || true

# Run the container
docker run -d \
    --name yolo-object-detection \
    -p 8443:8443 \
    --restart unless-stopped \
    yolo-object-detection:latest

if [ $? -eq 0 ]; then
    echo "✅ Container started successfully!"
    echo "🌐 Access the application at:"
    echo "   📱 Mobile: https://localhost:8443/realtime"
    echo "   🖥️  Desktop: https://localhost:8443"
    echo "   📊 Dashboard: https://localhost:8443/metrics/dashboard"
    echo ""
    echo "📋 Container status:"
    docker ps | grep yolo-object-detection
    echo ""
    echo "📝 To view logs:"
    echo "   docker logs -f yolo-object-detection"
else
    echo "❌ Failed to start container!"
    exit 1
fi
