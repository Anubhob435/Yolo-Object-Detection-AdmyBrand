# 🎯 YOLO Object Detection - AdmyBrand

A comprehensive real-time object detection system with WebRTC streaming, live video processing, and advanced metrics collection. Features mobile camera streaming to desktop with real-time YOLO inference and modern dashboard interface.

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.12+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![Docker](https://img.shields.io/badge/docker-supported-blue.svg)

## ✨ Features

### 🎥 **Real-Time Video Processing**
- **📱 Mobile to Desktop Streaming**: Stream mobile camera to PC browser with live object detection
- **🔴 Live MJPEG Stream**: Real-time video streaming with detection overlays
- **⚡ 480p Optimization**: Optimized resolution for better performance and battery life
- **🎛️ Stream Controls**: Auto-refresh, manual refresh, and fullscreen viewing

### 🧠 **AI-Powered Detection**
- **🎯 YOLO Integration**: YOLOv8 model for accurate object detection
- **📊 Real-Time Inference**: Live object detection with confidence scores
- **🎨 Visual Overlays**: Green bounding boxes with labels and confidence percentages
- **⚡ Performance Optimized**: Efficient processing for smooth real-time experience

### 📊 **Comprehensive Metrics System**
- **📈 7 Metric Categories**: Performance, network, detection, privacy, user interaction, system health, and custom metrics
- **🔄 Real-Time Dashboard**: Live updating metrics with modern glass morphism design
- **💾 Data Export**: JSON and CSV export capabilities for analysis
- **📱 System Monitoring**: CPU, memory, GPU, and disk usage tracking

### 🌐 **Web Interface**
- **📱 QR Code Integration**: Easy mobile access via QR codes
- **🎨 Modern UI**: Glass morphism design with responsive layout
- **🔧 Multiple Pages**: Stream viewer, metrics dashboard, camera test, and debug pages
- **🌙 Dark Theme**: Professional dark interface with blue accent colors

### 🐳 **Docker Support**
- **📦 Complete Containerization**: Ready-to-deploy Docker image
- **🔧 Docker Compose**: Easy deployment with docker-compose
- **🚀 Build Scripts**: Automated build scripts for Windows, Linux, and macOS
- **🏥 Health Checks**: Container monitoring and auto-restart capabilities

## 🚀 Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Anubhob435/Yolo-Object-Detection-AdmyBrand.git
cd Yolo-Object-Detection-AdmyBrand

# Start with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t yolo-object-detection .
docker run -d -p 8443:8443 --name yolo-detection yolo-object-detection
```

### Option 2: Local Development

```bash
# Install UV package manager (if not installed)
pip install uv

# Install dependencies
uv sync

# Run the inference server
uv run -m src.server.inference
```

## 🌐 Access Points

Once running, access the application at:

- **🏠 Home/Stream:** `https://localhost:8443/` - Live video stream viewer
- **📱 Mobile Camera:** `https://192.168.0.89:8443/realtime` - Mobile camera interface
- **📊 Metrics Dashboard:** `https://localhost:8443/metrics/dashboard` - Comprehensive metrics
- **🔧 Debug Console:** `https://localhost:8443/debug` - Debug and testing interface

## 📱 Mobile Setup

1. **🔍 Scan QR Code**: Use the QR code displayed on the web interface
2. **📱 Or Manual Access**: Navigate to `https://[YOUR_IP]:8443/realtime` on mobile
3. **✅ Accept SSL Warning**: Accept the self-signed certificate
4. **📹 Start Camera**: Click "Start Camera" to begin streaming
5. **🖥️ View on Desktop**: Watch live stream with detection at `https://localhost:8443/`

## 🏗️ Project Structure

```
Yolo-Object-Detection-AdmyBrand/
├── 🐳 Docker Configuration
│   ├── Dockerfile                 # Container definition
│   ├── docker-compose.yml         # Easy deployment
│   ├── .dockerignore              # Docker exclusions
│   └── DOCKER.md                  # Docker documentation
├── 📁 src/
│   ├── server/                    # Backend services
│   │   ├── inference.py           # Main server with WebRTC & streaming
│   │   ├── signaling.py           # WebSocket signaling
│   │   ├── metrics.py             # Metrics collection system
│   │   ├── resources.py           # System resource monitoring
│   │   └── interface.html         # Metrics dashboard UI
│   └── web/                       # Frontend assets
│       ├── templates/             # HTML pages
│       │   ├── video_stream.html  # Live stream viewer
│       │   ├── realtime_demo.html # Mobile camera interface
│       │   ├── index.html         # Main landing page
│       │   └── debug.html         # Debug console
│       └── static/               # CSS, JavaScript assets
├── 🎯 models/                     # AI models storage
│   ├── yolov8n.pt               # PyTorch model
│   └── yolov8n.onnx             # ONNX model (optional)
├── 🔧 scripts/                   # Utility scripts
│   ├── run.py                    # Quick launcher
│   ├── export_model.py           # Model export utility
│   ├── docker-entrypoint.sh      # Docker startup script
│   ├── build-docker.sh/.bat      # Docker build scripts
│   └── run-docker.sh/.bat        # Docker run scripts
├── 🔐 certs/                     # SSL certificates
│   ├── cert.pem                  # SSL certificate
│   └── key.pem                   # SSL private key
└── 📚 docs/                      # Documentation
    ├── STRUCTURE.md              # Project structure
    ├── CAMERA_TROUBLESHOOTING.md # Camera setup help
    └── MOBILE_ACCESS.md          # Mobile access guide
```

## 🔧 Configuration

### Performance Settings

**Resolution Optimization:**
- Default: 480p (854x480) for optimal performance
- Maintains aspect ratio for different camera orientations
- JPEG quality: 85% for size/quality balance

**Detection Settings:**
- Confidence threshold: 50% (adjustable)
- Frame rate: 15 FPS for web streaming
- Model: YOLOv8n (nano) for speed

### System Requirements

**Minimum:**
- Python 3.12+
- 4GB RAM
- CPU with AVX support
- Webcam/Camera access

**Recommended:**
- 8GB+ RAM
- GPU support (CUDA/Metal)
- Fast internet connection
- Modern browser with WebRTC support

## 📊 Metrics & Analytics

### 7-Category Metrics System

1. **⚡ Performance Metrics**
   - Frame processing time
   - Inference latency
   - Memory usage

2. **🌐 Network Metrics**
   - Data transferred
   - Connection quality
   - Bandwidth usage

3. **🎯 Detection Metrics**
   - Objects detected
   - Detection confidence
   - Processing accuracy

4. **🔒 Privacy Metrics**
   - Data transmission logs
   - Security events
   - Access tracking

5. **👤 User Interaction**
   - Page views
   - Button clicks
   - Session duration

6. **💻 System Health**
   - CPU usage
   - Memory consumption
   - Error rates

7. **🎛️ Custom Metrics**
   - Application-specific data
   - Custom events
   - Business metrics

## 🐳 Docker Deployment

### Quick Deploy

```bash
# Production deployment
docker-compose up -d

# Development with logs
docker-compose up

# Stop services
docker-compose down
```

### Manual Docker Commands

```bash
# Build image
docker build -t yolo-object-detection .

# Run container
docker run -d \
  --name yolo-detection \
  -p 8443:8443 \
  --restart unless-stopped \
  yolo-object-detection

# View logs
docker logs -f yolo-detection

# Health check
docker inspect yolo-detection | grep Health -A 10
```

### Environment Variables

```bash
# Custom configuration
docker run -d \
  -e YOLO_MODEL_PATH=/app/models/custom_model.pt \
  -e PYTHONPATH=/app \
  -p 8443:8443 \
  yolo-object-detection
```

## 🔒 Security Features

### SSL/TLS Support
- **🔐 Automatic HTTPS**: Self-signed certificates generated automatically
- **📱 Mobile Compatible**: Works with mobile browsers
- **🔄 Certificate Renewal**: Easy certificate management

### Privacy Protection
- **🏠 Local Processing**: Option for client-side inference
- **📊 Privacy Metrics**: Track data transmission and access
- **🛡️ Secure Streaming**: Encrypted WebRTC connections

## 🛠️ Development

### Local Development Setup

```bash
# Clone repository
git clone https://github.com/Anubhob435/Yolo-Object-Detection-AdmyBrand.git
cd Yolo-Object-Detection-AdmyBrand

# Setup environment
uv sync

# Run in development mode
uv run -m src.server.inference

# Or use the run script
python scripts/run.py inference
```

### Build Tools

```bash
# Export model to ONNX
python scripts/run.py export

# Create SSL certificates
python scripts/create_ssl_cert.py

# Setup mobile access
python scripts/mobile_setup.py
```

## 🧪 Testing

### Camera Test Page
Access `https://localhost:8443/camera-test` to:
- Test camera functionality
- Check WebRTC compatibility
- Verify media constraints
- Debug connection issues

### Debug Console
Access `https://localhost:8443/debug` for:
- Real-time logs
- Connection status
- Performance metrics
- Error tracking


### 📚 **Education/Research**
- Computer vision learning
- AI demonstration
- Research prototyping
- Student projects

5. **Open Pull Request**

### Development Guidelines
- Follow Python PEP 8 style guide
- Add tests for new features
- Update documentation
- Use meaningful commit messages

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.


### 📚 Documentation
- [Docker Guide](DOCKER.md) - Complete Docker documentation
- [Project Structure](docs/STRUCTURE.md) - Detailed architecture
- [Camera Troubleshooting](docs/CAMERA_TROUBLESHOOTING.md) - Camera setup help


---

Made with ❤️ for [AdmyBrand](https://github.com/Anubhob435)

[🔝 Back to Top](#-yolo-object-detection---admybrand)


