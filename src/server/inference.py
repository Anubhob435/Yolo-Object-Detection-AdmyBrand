import asyncio
import json
import logging
import uuid
import ssl
import weakref
import time
from pathlib import Path
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from aiohttp import web, WSMsgType
from av import VideoFrame
import numpy as np
from ultralytics import YOLO
from .metrics import get_metrics_collector

# Configure logging
logging.basicConfig(level=logging.INFO)

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
WEB_DIR = PROJECT_ROOT / "src" / "web"

# Load the YOLO model
model = YOLO(MODELS_DIR / 'yolov8n.pt')
pcs = set()
relay = MediaRelay()
websockets = set()  # Store WebSocket connections for real-time detection data

# Initialize metrics collector
metrics = get_metrics_collector()

class ObjectDetectionTrack(VideoStreamTrack):
    """
    A video stream track that runs object detection on frames with comprehensive metrics.
    """
    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track
        self.frame_count = 0

    async def recv(self):
        # Generate unique frame ID for tracking
        frame_id = f"frame_{self.frame_count}_{time.time()}"
        self.frame_count += 1
        
        # Start frame processing timing
        metrics.start_frame_processing(frame_id)
        
        try:
            frame = await self.track.recv()
            img = frame.to_ndarray(format="bgr24")
            
            # Get frame dimensions
            height, width = img.shape[:2]

            # Start inference timing
            metrics.start_inference(frame_id)
            
            # Perform detection
            results = model.predict(img, verbose=False)
            
            # End inference timing
            metrics.end_inference(frame_id)
            
            detections = []
            for result in results:
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        if box.conf > 0.5:  # Confidence threshold
                            xyxy = box.xyxy.tolist()[0]  # Absolute coordinates
                            cls = int(box.cls)
                            label = model.names[cls]
                            conf = float(box.conf)
                            
                            # Convert to the format expected by the frontend
                            detections.append({
                                "x1": int(xyxy[0]),
                                "y1": int(xyxy[1]), 
                                "x2": int(xyxy[2]),
                                "y2": int(xyxy[3]),
                                "class": label,
                                "confidence": conf
                            })

            # Send detection results via WebSocket
            detection_data_size = 0
            if detections and websockets:
                detection_data = json.dumps({"detections": detections, "frame_id": frame_id, "timestamp": time.time()})
                detection_data_size = len(detection_data.encode('utf-8'))
                
                # Send to all connected WebSocket clients
                for ws in websockets.copy():
                    try:
                        await ws.send_str(detection_data)
                        metrics.record_network_metrics(bytes_sent=detection_data_size)
                    except Exception as e:
                        # Remove failed connections
                        websockets.discard(ws)
                        logging.error(f"Failed to send detection data: {e}")

            # End frame processing and update metrics
            metrics.end_frame_processing(frame_id, detections)
            
            # Record privacy event if data was transmitted
            if detection_data_size > 0:
                metrics.record_privacy_event("data_transmitted", f"Detection data: {detection_data_size} bytes")

            return frame
            
        except Exception as e:
            logging.error(f"Error in object detection track: {e}")
            metrics.end_frame_processing(frame_id, [])
            return frame

async def index(request):
    content = open(WEB_DIR / "templates" / "index.html", "r").read()
    return web.Response(content_type="text/html", text=content)

async def javascript(request):
    content = open(WEB_DIR / "static" / "js" / "client_server_inference.js", "r").read()
    return web.Response(content_type="application/javascript", text=content)

async def client_metrics_js(request):
    content = open(WEB_DIR / "static" / "js" / "client_metrics.js", "r").read()
    return web.Response(content_type="application/javascript", text=content)
    
async def stylesheet(request):
    content = open(WEB_DIR / "static" / "css" / "style.css", "r").read()
    return web.Response(content_type="text/css", text=content)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    # Record connection attempt
    connection_id = int(time.time() * 1000)  # Use timestamp as connection ID
    metrics.record_connection_attempt()

    pc = RTCPeerConnection()
    pc_id = f"PeerConnection({uuid.uuid4()})"
    pcs.add(pc)

    logging.info(f"[{pc_id}] Created for {request.remote}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info(f"[{pc_id}] Connection state is {pc.connectionState}")
        if pc.connectionState == "connected":
            metrics.record_connection_success(connection_id)
            metrics.current_scalability.concurrent_users = len(pcs)
        elif pc.connectionState == "closed":
            pcs.discard(pc)
            metrics.current_scalability.concurrent_users = len(pcs)

    @pc.on("track")
    def on_track(track):
        logging.info(f"[{pc_id}] Track {track.kind} received")
        if track.kind == "video":
            # Add object detection to the track
            detection_track = ObjectDetectionTrack(relay.subscribe(track))
            pc.addTrack(detection_track)

    # Handle the offer
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.Response(
        content_type="application/json",
        text=json.dumps({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    )

async def websocket_handler(request):
    """WebSocket handler for real-time detection data."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    
    websockets.add(ws)
    logging.info(f"WebSocket connected: {request.remote}")
    
    try:
        async for msg in ws:
            if msg.type == WSMsgType.ERROR:
                logging.error(f'WebSocket error: {ws.exception()}')
                break
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        websockets.discard(ws)
        logging.info(f"WebSocket disconnected: {request.remote}")
    
    return ws

async def realtime_demo(request):
    """Serve real-time demo page with WebSocket detection data."""
    template_path = WEB_DIR / "templates" / "realtime_demo.html"
    with open(template_path, 'r', encoding='utf-8') as f:
        content = f.read()
    return web.Response(text=content, content_type='text/html')

async def debug_page(request):
    content = open(WEB_DIR / "templates" / "debug.html", "r").read()
    return web.Response(content_type="text/html", text=content)

async def camera_test(request):
    content = open(WEB_DIR / "templates" / "camera_test.html", "r").read()
    return web.Response(content_type="text/html", text=content)

async def metrics_api(request):
    """API endpoint to get current metrics as JSON."""
    current_metrics = metrics.get_current_metrics()
    return web.Response(
        content_type="application/json",
        text=json.dumps(current_metrics, indent=2, default=str)
    )

async def metrics_statistics(request):
    """API endpoint to get statistical analysis of metrics."""
    stats = metrics.get_statistics()
    return web.Response(
        content_type="application/json", 
        text=json.dumps(stats, indent=2, default=str)
    )

async def metrics_export(request):
    """API endpoint to export all metrics to a file."""
    try:
        filepath = metrics.export_metrics()
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Return the file content as JSON response
        return web.Response(
            content_type="application/json",
            text=content,
            headers={'Content-Disposition': f'attachment; filename="{filepath}"'}
        )
    except Exception as e:
        return web.Response(
            content_type="application/json",
            text=json.dumps({"error": str(e)}),
            status=500
        )

async def metrics_client(request):
    """Receive client-side metrics data."""
    try:
        data = await request.json()
        metrics_collector = get_metrics_collector()
        
        # Store client metrics
        if hasattr(metrics_collector, 'client_metrics'):
            metrics_collector.client_metrics.append({
                'timestamp': time.time(),
                'data': data
            })
        else:
            metrics_collector.client_metrics = [{
                'timestamp': time.time(),
                'data': data
            }]
        
        logging.info(f"📱 Received client metrics from session: {data.get('session', {}).get('id', 'unknown')}")
        
        return web.Response(
            content_type="application/json",
            text=json.dumps({"status": "success", "message": "Client metrics received"})
        )
    except Exception as e:
        logging.error(f"Error processing client metrics: {e}")
        return web.Response(
            content_type="application/json",
            text=json.dumps({"error": str(e)}),
            status=500
        )

async def metrics_dashboard(request):
    """Serve metrics dashboard page."""
    dashboard_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WebRTC Object Detection - Metrics Dashboard</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a1a1a, #2d2d2d);
            color: white;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .header h1 {
            color: #4CAF50;
            font-size: 2.5em;
            text-shadow: 0 0 20px rgba(76, 175, 80, 0.3);
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .metric-card {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 15px;
            padding: 20px;
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }
        .metric-title {
            color: #4CAF50;
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 15px;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 5px;
        }
        .metric-value {
            font-size: 1.1em;
            margin: 8px 0;
        }
        .metric-value .label {
            color: #ccc;
            display: inline-block;
            width: 150px;
        }
        .metric-value .value {
            color: #4CAF50;
            font-weight: bold;
        }
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        .btn {
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 25px;
            font-size: 16px;
            cursor: pointer;
            margin: 0 10px;
            transition: all 0.3s ease;
        }
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(76, 175, 80, 0.4);
        }
        .real-time {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 WebRTC Object Detection Metrics Dashboard</h1>
            <p>Real-time performance monitoring and analysis</p>
        </div>
        
        <div class="controls">
            <button class="btn" onclick="refreshMetrics()">🔄 Refresh Metrics</button>
            <button class="btn" onclick="exportMetrics()">📥 Export Data</button>
            <button class="btn" onclick="toggleAutoRefresh()">⚡ Auto Refresh: <span id="auto-status">OFF</span></button>
        </div>
        
        <div class="metrics-grid" id="metrics-container">
            <!-- Metrics will be loaded here -->
        </div>
    </div>
    
    <script>
        let autoRefresh = false;
        let refreshInterval;
        
        function formatValue(value) {
            if (typeof value === 'number') {
                if (value % 1 === 0) return value.toString();
                return value.toFixed(3);
            }
            return value;
        }
        
        function createMetricCard(title, data) {
            let html = `<div class="metric-card">
                <div class="metric-title">${title}</div>`;
            
            for (const [key, value] of Object.entries(data)) {
                if (typeof value === 'object' && value !== null) {
                    html += `<div class="metric-value">
                        <span class="label">${key}:</span>
                        <span class="value">${JSON.stringify(value)}</span>
                    </div>`;
                } else {
                    html += `<div class="metric-value">
                        <span class="label">${key}:</span>
                        <span class="value">${formatValue(value)}</span>
                    </div>`;
                }
            }
            html += '</div>';
            return html;
        }
        
        async function refreshMetrics() {
            try {
                const response = await fetch('/metrics');
                const metrics = await response.json();
                
                const container = document.getElementById('metrics-container');
                container.innerHTML = '';
                
                container.innerHTML += createMetricCard('⚡ Latency Metrics', metrics.latency);
                container.innerHTML += createMetricCard('💻 Computational Metrics', metrics.computational);
                container.innerHTML += createMetricCard('🌐 Network Metrics', metrics.network);
                container.innerHTML += createMetricCard('🎯 Detection Quality', metrics.detection_quality);
                container.innerHTML += createMetricCard('📱 Device Impact', metrics.device_impact);
                container.innerHTML += createMetricCard('📈 Scalability', metrics.scalability);
                container.innerHTML += createMetricCard('🔒 Privacy & Security', metrics.privacy);
                
                // Add timestamp
                const timestamp = new Date().toLocaleString();
                container.innerHTML += `<div class="metric-card">
                    <div class="metric-title">📅 Last Updated</div>
                    <div class="metric-value">
                        <span class="value real-time">${timestamp}</span>
                    </div>
                </div>`;
                
            } catch (error) {
                console.error('Error fetching metrics:', error);
            }
        }
        
        async function exportMetrics() {
            try {
                const response = await fetch('/metrics/export');
                const blob = await response.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `metrics_${new Date().toISOString().slice(0,19).replace(/:/g, '-')}.json`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);
            } catch (error) {
                console.error('Error exporting metrics:', error);
            }
        }
        
        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const status = document.getElementById('auto-status');
            
            if (autoRefresh) {
                status.textContent = 'ON';
                refreshInterval = setInterval(refreshMetrics, 5000); // Refresh every 5 seconds
            } else {
                status.textContent = 'OFF';
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
            }
        }
        
        // Initial load
        document.addEventListener('DOMContentLoaded', refreshMetrics);
    </script>
</body>
</html>
    """
    
    return web.Response(text=dashboard_html, content_type='text/html')

async def on_shutdown(app):
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()

app = web.Application()
app.on_shutdown.append(on_shutdown)
app.router.add_get("/", index)
app.router.add_get("/realtime", realtime_demo)
app.router.add_get("/detection-stream", websocket_handler)
app.router.add_get("/debug", debug_page)
app.router.add_get("/camera-test", camera_test)
app.router.add_get("/client_server_inference.js", javascript)
app.router.add_get("/client_metrics.js", client_metrics_js)
app.router.add_get("/style.css", stylesheet)
app.router.add_post("/offer", offer)
# Metrics endpoints
app.router.add_get("/metrics", metrics_api)
app.router.add_get("/metrics/stats", metrics_statistics)
app.router.add_get("/metrics/export", metrics_export)
app.router.add_get("/metrics/dashboard", metrics_dashboard)
app.router.add_post("/metrics/client", metrics_client)

if __name__ == "__main__":
    # Check if SSL certificates exist
    cert_path = PROJECT_ROOT / "certs" / "cert.pem"
    key_path = PROJECT_ROOT / "certs" / "key.pem"
    
    if cert_path.exists() and key_path.exists():
        # Run with HTTPS
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_path, key_path)
        print("🔒 Starting HTTPS server for mobile camera access...")
        print("🌐 HTTPS URLs:")
        print("   📱 Mobile: https://192.168.0.89:8443")
        print("   🖥️  Desktop: https://localhost:8443")
        print("   ⚡ Real-time: https://localhost:8443/realtime")
        print("   📊 Metrics Dashboard: https://localhost:8443/metrics/dashboard")
        print("   🔧 Debug: https://localhost:8443/debug")
        print("⚠️  Accept the security warning in your browser")
        web.run_app(app, host="0.0.0.0", port=8443, ssl_context=ssl_context)
    else:
        # Fallback to HTTP
        print("🌐 Starting HTTP server...")
        print("🌐 HTTP URLs:")
        print("   🖥️  Desktop: http://localhost:8080")
        print("   ⚡ Real-time: http://localhost:8080/realtime")
        print("   📊 Metrics Dashboard: http://localhost:8080/metrics/dashboard")
        print("   🔧 Debug: http://localhost:8080/debug")
        print("📱 Mobile browsers may not allow camera access over HTTP")
        web.run_app(app, host="0.0.0.0", port=8080)
