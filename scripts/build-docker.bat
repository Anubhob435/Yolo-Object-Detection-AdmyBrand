@echo off
echo 🐳 Building YOLO Object Detection Docker Image...

docker build -t yolo-object-detection:latest .

if %ERRORLEVEL% EQU 0 (
    echo ✅ Docker image built successfully!
    echo 📦 Image name: yolo-object-detection:latest
    echo.
    echo 🚀 To run the container:
    echo    docker run -p 8443:8443 yolo-object-detection:latest
    echo.
    echo 🔧 Or use docker-compose:
    echo    docker-compose up -d
) else (
    echo ❌ Docker build failed!
    exit /b 1
)

pause
