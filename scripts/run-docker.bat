@echo off
echo 🚀 Starting YOLO Object Detection Container...

REM Stop and remove existing container if it exists
docker stop yolo-object-detection >nul 2>&1
docker rm yolo-object-detection >nul 2>&1

REM Run the container
docker run -d --name yolo-object-detection -p 8443:8443 --restart unless-stopped yolo-object-detection:latest

if %ERRORLEVEL% EQU 0 (
    echo ✅ Container started successfully!
    echo 🌐 Access the application at:
    echo    📱 Mobile: https://localhost:8443/realtime
    echo    🖥️  Desktop: https://localhost:8443
    echo    📊 Dashboard: https://localhost:8443/metrics/dashboard
    echo.
    echo 📋 Container status:
    docker ps | findstr yolo-object-detection
    echo.
    echo 📝 To view logs:
    echo    docker logs -f yolo-object-detection
) else (
    echo ❌ Failed to start container!
    exit /b 1
)

pause
