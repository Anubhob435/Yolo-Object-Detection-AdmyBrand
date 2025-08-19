# 🐳 Docker Deployment Guide

This guide explains how to build and run the YOLO Object Detection application using Docker.

## 📋 Prerequisites

- Docker installed on your system
- Docker Compose (optional, for easier deployment)
- At least 4GB of available RAM
- Internet connection (for downloading YOLO model on first run)

## 🚀 Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# Build and start the container
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the container
docker-compose down
```

### Option 2: Using Docker Commands

```bash
# Build the image
docker build -t yolo-object-detection:latest .

# Run the container
docker run -d \
    --name yolo-object-detection \
    -p 8443:8443 \
    --restart unless-stopped \
    yolo-object-detection:latest
```

### Option 3: Using Build Scripts

**Linux/macOS:**
```bash
# Build the image
chmod +x scripts/build-docker.sh
./scripts/build-docker.sh

# Run the container
chmod +x scripts/run-docker.sh
./scripts/run-docker.sh
```

**Windows:**
```cmd
REM Build the image
scripts\build-docker.bat

REM Run the container
scripts\run-docker.bat
```

## 🌐 Access Points

Once the container is running, access the application at:

- **📱 Mobile Camera:** `https://localhost:8443/realtime`
- **🖥️ Desktop Stream:** `https://localhost:8443`
- **📊 Metrics Dashboard:** `https://localhost:8443/metrics/dashboard`
- **🔧 Debug Page:** `https://localhost:8443/debug`

## 📦 Container Details

### Exposed Ports
- `8443`: HTTPS server for web interface

### Volumes (Optional)
- `./models:/app/models` - Persistent model storage
- `./logs:/app/logs` - Application logs

### Environment Variables
- `PYTHONPATH=/app` - Python path configuration
- `YOLO_MODEL_PATH=/app/models/yolov8n.pt` - YOLO model location

## 🔧 Configuration

### SSL Certificates
The container automatically generates self-signed SSL certificates on startup. For production use, mount your own certificates:

```bash
docker run -d \
    -p 8443:8443 \
    -v /path/to/your/cert.pem:/app/certs/cert.pem \
    -v /path/to/your/key.pem:/app/certs/key.pem \
    yolo-object-detection:latest
```

### Custom Models
To use a custom YOLO model, mount it to the container:

```bash
docker run -d \
    -p 8443:8443 \
    -v /path/to/your/model.pt:/app/models/yolov8n.pt \
    yolo-object-detection:latest
```

## 📊 Monitoring

### Health Check
The container includes a health check that verifies the server is responding:

```bash
# Check container health
docker ps

# View health check logs
docker inspect yolo-object-detection | grep Health -A 10
```

### Logs
```bash
# View container logs
docker logs -f yolo-object-detection

# View logs with docker-compose
docker-compose logs -f
```

## 🛠️ Troubleshooting

### Common Issues

1. **Port already in use:**
   ```bash
   # Stop existing container
   docker stop yolo-object-detection
   docker rm yolo-object-detection
   ```

2. **Model download fails:**
   - Ensure internet connection
   - Check container logs: `docker logs yolo-object-detection`

3. **SSL certificate issues:**
   - Restart container to regenerate certificates
   - Or mount custom certificates

### Performance Optimization

1. **Increase memory limit:**
   ```bash
   docker run -d \
       --memory=4g \
       -p 8443:8443 \
       yolo-object-detection:latest
   ```

2. **Use GPU acceleration (if available):**
   ```bash
   docker run -d \
       --gpus all \
       -p 8443:8443 \
       yolo-object-detection:latest
   ```

## 🔄 Updates

To update the application:

```bash
# Pull latest code
git pull

# Rebuild image
docker build -t yolo-object-detection:latest .

# Restart container
docker-compose down
docker-compose up -d
```

## 📱 Mobile Access

1. Open camera app on mobile device
2. Scan QR code displayed on the web interface
3. Or manually navigate to: `https://[YOUR_IP]:8443/realtime`
4. Accept SSL certificate warning
5. Click "Start Camera" to begin detection

## 🛡️ Security Notes

- The container uses self-signed SSL certificates by default
- For production, use proper SSL certificates
- Consider using a reverse proxy (nginx, traefik) for additional security
- The application is designed for local network use

## 📈 Scaling

For production deployment:

1. Use a proper orchestration platform (Kubernetes, Docker Swarm)
2. Implement load balancing for multiple instances
3. Use external storage for models and logs
4. Monitor resource usage and scale accordingly

---

## 📞 Support

If you encounter issues:

1. Check container logs: `docker logs yolo-object-detection`
2. Verify network connectivity
3. Ensure sufficient system resources
4. Check firewall settings for port 8443
