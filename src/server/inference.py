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
    content = open(WEB_DIR / "static" / "js" / "client_server_inference.js", "r", encoding='utf-8').read()
    return web.Response(content_type="application/javascript", text=content)

async def client_metrics_js(request):
    content = open(WEB_DIR / "static" / "js" / "client_metrics.js", "r", encoding='utf-8').read()
    return web.Response(content_type="application/javascript", text=content)
    
async def stylesheet(request):
    content = open(WEB_DIR / "static" / "css" / "style.css", "r", encoding='utf-8').read()
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
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        :root {
            --primary-color: #00f5ff;
            --secondary-color: #ff6b6b;
            --success-color: #51cf66;
            --warning-color: #ffd43b;
            --danger-color: #ff6b6b;
            --dark-bg: #0a0a0a;
            --card-bg: rgba(255, 255, 255, 0.02);
            --card-border: rgba(255, 255, 255, 0.05);
            --glass-bg: rgba(255, 255, 255, 0.03);
            --text-primary: #ffffff;
            --text-secondary: #a0a9c0;
            --text-muted: #6c7b7f;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--dark-bg);
            background-image: 
                radial-gradient(circle at 20% 80%, rgba(0, 245, 255, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, rgba(255, 107, 107, 0.1) 0%, transparent 50%),
                radial-gradient(circle at 40% 40%, rgba(81, 207, 102, 0.05) 0%, transparent 50%);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            overflow-x: hidden;
        }

        .container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 2rem;
        }

        .header {
            text-align: center;
            margin-bottom: 3rem;
            position: relative;
        }

        .header::before {
            content: '';
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 200px;
            height: 200px;
            background: radial-gradient(circle, var(--primary-color) 0%, transparent 70%);
            opacity: 0.1;
            border-radius: 50%;
            z-index: -1;
        }

        .header h1 {
            color: var(--text-primary);
            font-size: 3.5rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--success-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
            position: relative;
        }

        .header h1::after {
            content: '';
            position: absolute;
            bottom: -10px;
            left: 50%;
            transform: translateX(-50%);
            width: 100px;
            height: 3px;
            background: linear-gradient(90deg, var(--primary-color), var(--success-color));
            border-radius: 2px;
        }

        .header p {
            color: var(--text-secondary);
            font-size: 1.2rem;
            font-weight: 400;
            margin-bottom: 1rem;
        }

        .system-status {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.5rem 1rem;
            background: var(--glass-bg);
            border: 1px solid var(--card-border);
            border-radius: 25px;
            font-size: 0.9rem;
        }

        .system-status.online {
            border-color: var(--success-color);
            color: var(--success-color);
        }

        .system-status.offline {
            border-color: var(--danger-color);
            color: var(--danger-color);
        }

        .controls {
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 3rem;
            flex-wrap: wrap;
        }

        .btn-group {
            display: flex;
            gap: 0.5rem;
            background: var(--glass-bg);
            border: 1px solid var(--card-border);
            border-radius: 15px;
            padding: 0.25rem;
        }

        .btn {
            background: transparent;
            border: none;
            color: var(--text-primary);
            padding: 0.75rem 1.5rem;
            border-radius: 12px;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            position: relative;
            overflow: hidden;
            white-space: nowrap;
        }

        .btn-group .btn {
            border-radius: 10px;
            padding: 0.6rem 1.2rem;
        }

        .btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
            transition: left 0.5s;
        }

        .btn:hover::before {
            left: 100%;
        }

        .btn:hover {
            transform: translateY(-2px);
            background: var(--glass-bg);
            border-color: var(--primary-color);
            box-shadow: 0 10px 30px rgba(0, 245, 255, 0.2);
        }

        .btn.active {
            background: linear-gradient(135deg, var(--primary-color), var(--success-color));
            border-color: transparent;
            color: white;
        }

        .btn.danger {
            color: var(--danger-color);
        }

        .btn.danger:hover {
            background: rgba(255, 107, 107, 0.1);
            border-color: var(--danger-color);
        }

        .filter-tabs {
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 2rem;
        }

        .filter-tab {
            padding: 0.5rem 1rem;
            background: var(--glass-bg);
            border: 1px solid var(--card-border);
            border-radius: 8px;
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.85rem;
        }

        .filter-tab.active {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }

        .filter-tab:hover:not(.active) {
            border-color: var(--primary-color);
            color: var(--primary-color);
        }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .metric-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 20px;
            padding: 2rem;
            position: relative;
            overflow: hidden;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
        }

        .metric-card.collapsed .metric-content {
            max-height: 60px;
            overflow: hidden;
        }

        .metric-card.collapsed .metric-title::after {
            content: ' ▼';
            font-size: 0.8em;
        }

        .metric-card:not(.collapsed) .metric-title::after {
            content: ' ▲';
            font-size: 0.8em;
        }

        .metric-content {
            transition: max-height 0.3s ease;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary-color), var(--success-color));
            border-radius: 20px 20px 0 0;
        }

        .metric-card.warning::before {
            background: linear-gradient(90deg, var(--warning-color), #ff9500);
        }

        .metric-card.danger::before {
            background: linear-gradient(90deg, var(--danger-color), #ff3030);
        }

        .metric-card:hover {
            transform: translateY(-5px);
            border-color: var(--primary-color);
            box-shadow: 0 20px 60px rgba(0, 245, 255, 0.1);
        }

        .metric-title {
            color: var(--text-primary);
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            cursor: pointer;
            user-select: none;
        }

        .metric-title .title-text {
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        .metric-summary {
            font-size: 0.85rem;
            color: var(--text-muted);
            font-weight: 400;
        }

        .metric-value {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem 0;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            transition: all 0.2s ease;
        }

        .metric-value:last-child {
            border-bottom: none;
        }

        .metric-value:hover {
            background: rgba(255, 255, 255, 0.02);
            margin: 0 -1rem;
            padding-left: 1rem;
            padding-right: 1rem;
            border-radius: 8px;
        }

        .metric-value .label {
            color: var(--text-secondary);
            font-weight: 400;
            font-size: 0.9rem;
        }

        .metric-value .value {
            color: var(--success-color);
            font-weight: 600;
            font-size: 1rem;
            font-family: 'Monaco', 'Menlo', monospace;
        }

        .status-indicator {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success-color);
            margin-left: 0.5rem;
            animation: pulse 2s infinite;
        }

        .status-indicator.warning {
            background: var(--warning-color);
        }

        .status-indicator.danger {
            background: var(--danger-color);
        }

        .real-time {
            animation: glow 2s ease-in-out infinite alternate;
        }

        @keyframes pulse {
            0%, 100% { 
                transform: scale(1);
                opacity: 1;
            }
            50% { 
                transform: scale(1.2);
                opacity: 0.7;
            }
        }

        @keyframes glow {
            from {
                text-shadow: 0 0 5px var(--primary-color);
            }
            to {
                text-shadow: 0 0 20px var(--primary-color), 0 0 30px var(--primary-color);
            }
        }

        .stats-overview {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: var(--glass-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }

        .stat-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 2px;
            background: linear-gradient(90deg, var(--primary-color), var(--success-color));
        }

        .stat-card.warning::before {
            background: var(--warning-color);
        }

        .stat-card.danger::before {
            background: var(--danger-color);
        }

        .stat-card:hover {
            transform: translateY(-3px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
        }

        .stat-number {
            font-size: 2rem;
            font-weight: 700;
            color: var(--primary-color);
            margin-bottom: 0.5rem;
            font-family: 'Monaco', 'Menlo', monospace;
        }

        .stat-number.warning {
            color: var(--warning-color);
        }

        .stat-number.danger {
            color: var(--danger-color);
        }

        .stat-label {
            color: var(--text-secondary);
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .search-box {
            max-width: 400px;
            margin: 0 auto 2rem;
            position: relative;
        }

        .search-input {
            width: 100%;
            padding: 0.75rem 1rem 0.75rem 2.5rem;
            background: var(--glass-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            color: var(--text-primary);
            font-size: 0.9rem;
            transition: all 0.3s ease;
        }

        .search-input:focus {
            outline: none;
            border-color: var(--primary-color);
            box-shadow: 0 0 20px rgba(0, 245, 255, 0.2);
        }

        .search-input::placeholder {
            color: var(--text-muted);
        }

        .search-icon {
            position: absolute;
            left: 0.75rem;
            top: 50%;
            transform: translateY(-50%);
            color: var(--text-muted);
            font-size: 1rem;
        }

        .tooltip {
            position: absolute;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            padding: 0.5rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            z-index: 1000;
            white-space: nowrap;
            opacity: 0;
            transition: opacity 0.3s ease;
            pointer-events: none;
        }

        .tooltip.show {
            opacity: 1;
        }

        @media (max-width: 768px) {
            .container {
                padding: 1rem;
            }
            
            .header h1 {
                font-size: 2.5rem;
            }
            
            .controls {
                gap: 0.5rem;
            }
            
            .btn {
                padding: 0.6rem 1.2rem;
                font-size: 0.8rem;
            }
            
            .metrics-grid {
                grid-template-columns: 1fr;
                gap: 1rem;
            }
            
            .metric-card {
                padding: 1.5rem;
            }
        }

        .loading {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            border-top: 2px solid var(--primary-color);
            animation: spin 1s linear infinite;
            margin-left: 0.5rem;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 WebRTC Object Detection Metrics</h1>
            <p>Real-time performance monitoring and comprehensive analytics</p>
            <div class="system-status online" id="system-status">
                <span class="status-indicator"></span>
                System Online
            </div>
        </div>
        
        <div class="stats-overview" id="stats-overview">
            <!-- Quick stats will be loaded here -->
        </div>
        
        <div class="controls">
            <div class="btn-group">
                <button class="btn" onclick="refreshMetrics()" id="refresh-btn">
                    🔄 Refresh<span id="refresh-loading"></span>
                </button>
                <button class="btn" onclick="toggleAutoRefresh()" id="auto-btn">
                    ⚡ Auto: <span id="auto-status">OFF</span>
                </button>
            </div>
            
            <div class="btn-group">
                <button class="btn" onclick="exportMetrics()">
                    📥 Export
                </button>
                <button class="btn" onclick="openFullscreen()">
                    🔍 Fullscreen
                </button>
            </div>
            
            <div class="btn-group">
                <button class="btn danger" onclick="clearMetrics()">
                    🗑️ Clear
                </button>
            </div>
        </div>

        <div class="search-box">
            <div class="search-icon">🔍</div>
            <input type="text" class="search-input" placeholder="Search metrics..." id="search-input" oninput="filterMetrics()">
        </div>
        
        <div class="filter-tabs">
            <div class="filter-tab active" data-filter="all" onclick="setFilter('all')">All Metrics</div>
            <div class="filter-tab" data-filter="performance" onclick="setFilter('performance')">Performance</div>
            <div class="filter-tab" data-filter="network" onclick="setFilter('network')">Network</div>
            <div class="filter-tab" data-filter="quality" onclick="setFilter('quality')">Quality</div>
            <div class="filter-tab" data-filter="system" onclick="setFilter('system')">System</div>
        </div>
        
        <div class="metrics-grid" id="metrics-container">
            <!-- Metrics will be loaded here -->
        </div>
    </div>
    
    <div class="tooltip" id="tooltip"></div>
    
    <script>
        let autoRefresh = false;
        let refreshInterval;
        let isLoading = false;
        let currentFilter = 'all';
        let metricsData = null;
        
        // Tooltip functionality
        function showTooltip(element, text) {
            const tooltip = document.getElementById('tooltip');
            const rect = element.getBoundingClientRect();
            tooltip.textContent = text;
            tooltip.style.left = rect.left + 'px';
            tooltip.style.top = (rect.top - 30) + 'px';
            tooltip.classList.add('show');
        }
        
        function hideTooltip() {
            const tooltip = document.getElementById('tooltip');
            tooltip.classList.remove('show');
        }
        
        // Card collapse functionality
        function toggleCard(cardElement) {
            cardElement.classList.toggle('collapsed');
        }
        
        // Filter functionality
        function setFilter(filter) {
            currentFilter = filter;
            document.querySelectorAll('.filter-tab').forEach(tab => tab.classList.remove('active'));
            document.querySelector(`[data-filter="${filter}"]`).classList.add('active');
            renderMetrics(metricsData);
        }
        
        function filterMetrics() {
            const searchTerm = document.getElementById('search-input').value.toLowerCase();
            const cards = document.querySelectorAll('.metric-card');
            
            cards.forEach(card => {
                const title = card.querySelector('.metric-title').textContent.toLowerCase();
                const values = card.querySelectorAll('.metric-value .label');
                let matches = title.includes(searchTerm);
                
                values.forEach(value => {
                    if (value.textContent.toLowerCase().includes(searchTerm)) {
                        matches = true;
                    }
                });
                
                card.style.display = matches ? 'block' : 'none';
            });
        }
        
        function formatValue(value, key = '') {
            if (typeof value === 'number') {
                if (key.includes('time') || key.includes('latency')) {
                    return `${value.toFixed(2)}ms`;
                } else if (key.includes('usage') || key.includes('percent') || key.includes('rate')) {
                    return `${value.toFixed(1)}%`;
                } else if (key.includes('memory') || key.includes('size')) {
                    return `${(value / 1024 / 1024).toFixed(1)}MB`;
                } else if (key.includes('bandwidth')) {
                    return `${value.toFixed(2)} Mbps`;
                } else if (value % 1 === 0) {
                    return value.toString();
                } else {
                    return value.toFixed(3);
                }
            }
            return value;
        }
        
        function getStatusIndicator(value, key) {
            if (typeof value !== 'number') return '';
            
            let className = 'status-indicator';
            
            if (key.includes('latency') || key.includes('time')) {
                if (value > 100) className += ' danger';
                else if (value > 50) className += ' warning';
            } else if (key.includes('usage') || key.includes('percent')) {
                if (value > 90) className += ' danger';
                else if (value > 70) className += ' warning';
            } else if (key.includes('loss')) {
                if (value > 5) className += ' danger';
                else if (value > 1) className += ' warning';
            }
            
            return `<span class="${className}"></span>`;
        }
        
        function getCardStatus(data) {
            for (const [key, value] of Object.entries(data)) {
                if (typeof value === 'number') {
                    if ((key.includes('latency') && value > 100) || 
                        (key.includes('usage') && value > 90) ||
                        (key.includes('loss') && value > 5)) {
                        return 'danger';
                    } else if ((key.includes('latency') && value > 50) || 
                               (key.includes('usage') && value > 70) ||
                               (key.includes('loss') && value > 1)) {
                        return 'warning';
                    }
                }
            }
            return 'normal';
        }
        
        function getCardFilter(title) {
            if (title.includes('Latency') || title.includes('Computational')) return 'performance';
            if (title.includes('Network')) return 'network';
            if (title.includes('Detection') || title.includes('Quality')) return 'quality';
            if (title.includes('Device') || title.includes('Privacy') || title.includes('Scalability')) return 'system';
            return 'all';
        }
        
        function createMetricCard(title, data) {
            const status = getCardStatus(data);
            const filter = getCardFilter(title);
            const shouldShow = currentFilter === 'all' || currentFilter === filter;
            
            // Calculate summary info
            const totalMetrics = Object.keys(data).length;
            const activeMetrics = Object.values(data).filter(v => typeof v === 'number' && v > 0).length;
            
            let html = `<div class="metric-card ${status}" data-filter="${filter}" 
                            style="display: ${shouldShow ? 'block' : 'none'}" 
                            onclick="toggleCard(this)">
                <div class="metric-title">
                    <div class="title-text">${title}</div>
                    <div class="metric-summary">${activeMetrics}/${totalMetrics} active</div>
                </div>
                <div class="metric-content">`;
            
            for (const [key, value] of Object.entries(data)) {
                const formattedKey = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                
                if (typeof value === 'object' && value !== null) {
                    html += `<div class="metric-value" 
                                onmouseenter="showTooltip(this, 'Complex data structure')"
                                onmouseleave="hideTooltip()">
                        <span class="label">${formattedKey}</span>
                        <span class="value">${JSON.stringify(value)}</span>
                    </div>`;
                } else {
                    const tooltip = `${formattedKey}: ${formatValue(value, key)}`;
                    html += `<div class="metric-value" 
                                onmouseenter="showTooltip(this, '${tooltip}')"
                                onmouseleave="hideTooltip()">
                        <span class="label">${formattedKey}</span>
                        <span class="value">${formatValue(value, key)}${getStatusIndicator(value, key)}</span>
                    </div>`;
                }
            }
            html += '</div></div>';
            return html;
        }
        
        function createStatsOverview(metrics) {
            const stats = [
                { 
                    label: 'Active Connections', 
                    value: metrics.scalability?.active_connections || 0,
                    status: (metrics.scalability?.active_connections || 0) > 5 ? 'warning' : 'normal'
                },
                { 
                    label: 'Avg Latency', 
                    value: `${(metrics.latency?.frame_processing_ms || 0).toFixed(1)}ms`,
                    status: (metrics.latency?.frame_processing_ms || 0) > 50 ? 'danger' : 
                           (metrics.latency?.frame_processing_ms || 0) > 25 ? 'warning' : 'normal'
                },
                { 
                    label: 'CPU Usage', 
                    value: `${(metrics.computational?.cpu_usage_percent || 0).toFixed(1)}%`,
                    status: (metrics.computational?.cpu_usage_percent || 0) > 80 ? 'danger' : 
                           (metrics.computational?.cpu_usage_percent || 0) > 60 ? 'warning' : 'normal'
                },
                { 
                    label: 'Detection Rate', 
                    value: `${(metrics.detection_quality?.detection_rate || 0).toFixed(1)}%`,
                    status: (metrics.detection_quality?.detection_rate || 0) < 70 ? 'warning' : 'normal'
                }
            ];
            
            return stats.map(stat => `
                <div class="stat-card ${stat.status}">
                    <div class="stat-number ${stat.status}">${stat.value}</div>
                    <div class="stat-label">${stat.label}</div>
                </div>
            `).join('');
        }
        
        function renderMetrics(metrics) {
            if (!metrics) return;
            
            // Update stats overview
            const statsContainer = document.getElementById('stats-overview');
            statsContainer.innerHTML = createStatsOverview(metrics);
            
            // Update main metrics
            const container = document.getElementById('metrics-container');
            container.innerHTML = '';
            
            const metricSections = [
                { title: '⚡ Latency Metrics', data: metrics.latency },
                { title: '💻 Computational Metrics', data: metrics.computational },
                { title: '🌐 Network Metrics', data: metrics.network },
                { title: '🎯 Detection Quality', data: metrics.detection_quality },
                { title: '📱 Device Impact', data: metrics.device_impact },
                { title: '📈 Scalability', data: metrics.scalability },
                { title: '🔒 Privacy & Security', data: metrics.privacy }
            ];
            
            metricSections.forEach(section => {
                if (section.data && Object.keys(section.data).length > 0) {
                    container.innerHTML += createMetricCard(section.title, section.data);
                }
            });
            
            // Add timestamp card
            const timestamp = new Date().toLocaleString();
            const systemCard = `<div class="metric-card" data-filter="system" 
                                     style="display: ${currentFilter === 'all' || currentFilter === 'system' ? 'block' : 'none'}">
                <div class="metric-title">
                    <div class="title-text">📅 System Status</div>
                    <div class="metric-summary">Live</div>
                </div>
                <div class="metric-content">
                    <div class="metric-value">
                        <span class="label">Last Updated</span>
                        <span class="value real-time">${timestamp}</span>
                    </div>
                    <div class="metric-value">
                        <span class="label">Auto Refresh</span>
                        <span class="value">${autoRefresh ? 'Enabled' : 'Disabled'}</span>
                    </div>
                    <div class="metric-value">
                        <span class="label">Session Duration</span>
                        <span class="value">${Math.floor(performance.now() / 1000)}s</span>
                    </div>
                </div>
            </div>`;
            
            container.innerHTML += systemCard;
        }
        
        async function refreshMetrics() {
            if (isLoading) return;
            
            isLoading = true;
            const loadingEl = document.getElementById('refresh-loading');
            const refreshBtn = document.getElementById('refresh-btn');
            const systemStatus = document.getElementById('system-status');
            
            loadingEl.innerHTML = '<span class="loading"></span>';
            refreshBtn.disabled = true;
            
            try {
                const response = await fetch('/metrics');
                const metrics = await response.json();
                
                metricsData = metrics;
                renderMetrics(metrics);
                
                // Update system status
                systemStatus.className = 'system-status online';
                systemStatus.innerHTML = '<span class="status-indicator"></span>System Online';
                
            } catch (error) {
                console.error('Error fetching metrics:', error);
                
                // Update system status
                systemStatus.className = 'system-status offline';
                systemStatus.innerHTML = '<span class="status-indicator"></span>System Offline';
                
                const container = document.getElementById('metrics-container');
                container.innerHTML = `<div class="metric-card danger">
                    <div class="metric-title">
                        <div class="title-text">❌ Connection Error</div>
                    </div>
                    <div class="metric-content">
                        <div class="metric-value">
                            <span class="label">Status</span>
                            <span class="value">Failed to fetch metrics</span>
                        </div>
                        <div class="metric-value">
                            <span class="label">Error</span>
                            <span class="value">${error.message}</span>
                        </div>
                    </div>
                </div>`;
            } finally {
                isLoading = false;
                loadingEl.innerHTML = '';
                refreshBtn.disabled = false;
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
                
                // Show success feedback
                showNotification('Metrics exported successfully!', 'success');
            } catch (error) {
                console.error('Error exporting metrics:', error);
                showNotification('Failed to export metrics', 'error');
            }
        }
        
        function toggleAutoRefresh() {
            autoRefresh = !autoRefresh;
            const status = document.getElementById('auto-status');
            const btn = document.getElementById('auto-btn');
            
            if (autoRefresh) {
                status.textContent = 'ON';
                btn.classList.add('active');
                refreshInterval = setInterval(refreshMetrics, 5000);
                showNotification('Auto refresh enabled', 'success');
            } else {
                status.textContent = 'OFF';
                btn.classList.remove('active');
                if (refreshInterval) {
                    clearInterval(refreshInterval);
                }
                showNotification('Auto refresh disabled', 'info');
            }
        }
        
        function clearMetrics() {
            if (confirm('Are you sure you want to clear all metrics data?')) {
                fetch('/metrics/clear', { method: 'POST' })
                    .then(() => {
                        refreshMetrics();
                        showNotification('Metrics cleared successfully', 'success');
                    })
                    .catch(error => {
                        console.error('Error clearing metrics:', error);
                        showNotification('Failed to clear metrics', 'error');
                    });
            }
        }
        
        function openFullscreen() {
            if (document.documentElement.requestFullscreen) {
                document.documentElement.requestFullscreen();
            } else if (document.documentElement.webkitRequestFullscreen) {
                document.documentElement.webkitRequestFullscreen();
            } else if (document.documentElement.msRequestFullscreen) {
                document.documentElement.msRequestFullscreen();
            }
        }
        
        function showNotification(message, type = 'info') {
            const notification = document.createElement('div');
            notification.className = `notification ${type}`;
            notification.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                background: var(--glass-bg);
                border: 1px solid var(--card-border);
                border-radius: 8px;
                padding: 1rem;
                color: var(--text-primary);
                z-index: 10000;
                transition: all 0.3s ease;
                backdrop-filter: blur(20px);
            `;
            
            if (type === 'success') {
                notification.style.borderColor = 'var(--success-color)';
            } else if (type === 'error') {
                notification.style.borderColor = 'var(--danger-color)';
            } else if (type === 'warning') {
                notification.style.borderColor = 'var(--warning-color)';
            }
            
            notification.textContent = message;
            document.body.appendChild(notification);
            
            setTimeout(() => {
                notification.style.opacity = '0';
                notification.style.transform = 'translateX(100%)';
                setTimeout(() => document.body.removeChild(notification), 300);
            }, 3000);
        }
        
        // Keyboard shortcuts
        document.addEventListener('keydown', function(e) {
            if (e.key === 'r' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                refreshMetrics();
            } else if (e.key === 'e' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                exportMetrics();
            } else if (e.key === ' ') {
                e.preventDefault();
                toggleAutoRefresh();
            } else if (e.key === 'f' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                openFullscreen();
            } else if (e.key === 'c' && (e.ctrlKey || e.metaKey) && e.shiftKey) {
                e.preventDefault();
                clearMetrics();
            } else if (e.key === '/' && !e.ctrlKey && !e.metaKey) {
                e.preventDefault();
                document.getElementById('search-input').focus();
            }
        });
        
        // Initial load with animation
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(refreshMetrics, 500);
            
            // Show keyboard shortcuts on first load
            setTimeout(() => {
                showNotification('Tip: Use Ctrl+R to refresh, / to search, Space for auto-refresh', 'info');
            }, 2000);
        });
        
        // Update page title with status
        setInterval(() => {
            const connectionCount = metricsData?.scalability?.active_connections || 0;
            if (autoRefresh) {
                document.title = `🔴 Live (${connectionCount}) - WebRTC Metrics`;
            } else {
                document.title = `📊 WebRTC Metrics Dashboard`;
            }
        }, 1000);
        
        // Auto-save preferences
        function savePreferences() {
            localStorage.setItem('metrics_auto_refresh', autoRefresh);
            localStorage.setItem('metrics_filter', currentFilter);
        }
        
        function loadPreferences() {
            const savedAutoRefresh = localStorage.getItem('metrics_auto_refresh');
            const savedFilter = localStorage.getItem('metrics_filter');
            
            if (savedAutoRefresh === 'true') {
                toggleAutoRefresh();
            }
            
            if (savedFilter && savedFilter !== 'all') {
                setFilter(savedFilter);
            }
        }
        
        // Load preferences on startup
        window.addEventListener('load', loadPreferences);
        
        // Save preferences before unload
        window.addEventListener('beforeunload', savePreferences);
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
