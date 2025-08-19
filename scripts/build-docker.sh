#!/bin/bash

# Build script for YOLO Object Detection Docker image

echo "🐳 Building YOLO Object Detection Docker Image..."

# Build the Docker image
docker build -t yolo-object-detection:latest .

if [ $? -eq 0 ]; then
    echo "✅ Docker image built successfully!"
    echo "📦 Image name: yolo-object-detection:latest"
    echo ""
    echo "🚀 To run the container:"
    echo "   docker run -p 8443:8443 yolo-object-detection:latest"
    echo ""
    echo "🔧 Or use docker-compose:"
    echo "   docker-compose up -d"
else
    echo "❌ Docker build failed!"
    exit 1
fi
