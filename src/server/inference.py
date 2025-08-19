import asyncio
import json
import logging
import uuid
import ssl
import weakref
import time
import socket
from pathlib import Path
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaRelay
from aiohttp import web, WSMsgType
from av import VideoFrame
import numpy as np
from ultralytics import YOLO
from .metrics import get_metrics_collector

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO)

def get_local_ip():
    """Get the local IP address of the machine."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except Exception:
        return "localhost"

def generate_qr_code(url):
    """Generate and display a QR code for the given URL."""
    if not QR_AVAILABLE:
        print("📱 QR Code generation not available (qrcode package not installed)")
        print(f"   Mobile URL: {url}")
        return
    
    try:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        
        print("📱 Scan this QR code with your mobile phone:")
        qr.print_ascii(invert=True)
        print(f"   Or visit directly: {url}")
    except Exception as e:
        print(f"📱 QR Code generation failed: {e}")
        print(f"   Mobile URL: {url}")

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
    """Redirect root URL to metrics dashboard."""
    return web.Response(
        status=302,
        headers={'Location': '/metrics/dashboard'}
    )

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
    
    # Update connection count immediately
    metrics.current_scalability.concurrent_users = len(pcs)
    metrics.current_scalability.active_connections = len(pcs)

    logging.info(f"[{pc_id}] Created for {request.remote}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info(f"[{pc_id}] Connection state is {pc.connectionState}")
        if pc.connectionState == "connected":
            metrics.record_connection_success(connection_id)
            metrics.current_scalability.concurrent_users = len(pcs)
            metrics.current_scalability.active_connections = len(pcs)
        elif pc.connectionState == "closed":
            pcs.discard(pc)
            metrics.current_scalability.concurrent_users = len(pcs)
            metrics.current_scalability.active_connections = len(pcs)

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
    """
    Serve metrics dashboard page from external HTML file.
    Loads interface.html from the same directory as this script.
    """
    try:
        # Get the path to the interface.html file in the same directory
        interface_html_path = Path(__file__).parent / "interface.html"
        
        with open(interface_html_path, 'r', encoding='utf-8') as f:
            dashboard_html = f.read()
        
        return web.Response(text=dashboard_html, content_type='text/html')
    except FileNotFoundError:
        return web.Response(
            text="<h1>Error: interface.html not found</h1>",
            content_type='text/html',
            status=404
        )
    except Exception as e:
        return web.Response(
            text=f"<h1>Error loading dashboard: {str(e)}</h1>",
            content_type='text/html',
            status=500
        )

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
    # Check if interface.html exists
    interface_html_path = Path(__file__).parent / "interface.html"
    if not interface_html_path.exists():
        print("❌ Error: interface.html not found in server directory")
        print(f"   Expected path: {interface_html_path}")
        exit(1)
    else:
        print("✅ Found interface.html for metrics dashboard")
    
    # Check if SSL certificates exist
    cert_path = PROJECT_ROOT / "certs" / "cert.pem"
    key_path = PROJECT_ROOT / "certs" / "key.pem"
    
    if cert_path.exists() and key_path.exists():
        # Get local IP address for mobile access
        local_ip = get_local_ip()
        
        # Run with HTTPS
        ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_path, key_path)
        print("🔒 Starting HTTPS server for mobile camera access...")
        print("🌐 HTTPS URLs:")
        print(f"   📱 Mobile: https://{local_ip}:8443")
        print("   🖥️  Desktop: https://localhost:8443")
        print("   ⚡ Real-time: https://localhost:8443/realtime")
        print("   📊 Metrics Dashboard: https://localhost:8443/metrics/dashboard")
        print("   🔧 Debug: https://localhost:8443/debug")
        print("⚠️  Accept the security warning in your browser")
        print()
        
        # Generate QR code for mobile realtime demo
        mobile_realtime_url = f"https://{local_ip}:8443/realtime"
        generate_qr_code(mobile_realtime_url)
        print()
        
        web.run_app(app, host="0.0.0.0", port=8443, ssl_context=ssl_context)
    else:
        # Get local IP address for mobile access
        local_ip = get_local_ip()
        
        # Fallback to HTTP
        print("🌐 Starting HTTP server...")
        print("🌐 HTTP URLs:")
        print(f"   📱 Mobile: http://{local_ip}:8080")
        print("   🖥️  Desktop: http://localhost:8080")
        print("   ⚡ Real-time: http://localhost:8080/realtime")
        print("   📊 Metrics Dashboard: http://localhost:8080/metrics/dashboard")
        print("   🔧 Debug: http://localhost:8080/debug")
        print("📱 Mobile browsers may not allow camera access over HTTP")
        print()
        
        # Generate QR code for mobile realtime demo
        mobile_realtime_url = f"http://{local_ip}:8080/realtime"
        generate_qr_code(mobile_realtime_url)
        print()
        
        web.run_app(app, host="0.0.0.0", port=8080)
