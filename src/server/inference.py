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

class ObjectDetectionTrack(VideoStreamTrack):
    """
    A video stream track that runs object detection on frames.
    """
    kind = "video"

    def __init__(self, track):
        super().__init__()
        self.track = track

    async def recv(self):
        frame = await self.track.recv()
        img = frame.to_ndarray(format="bgr24")
        
        # Get frame dimensions
        height, width = img.shape[:2]

        # Perform detection
        results = model.predict(img, verbose=False)
        
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
        if detections and websockets:
            detection_data = json.dumps({"detections": detections})
            # Send to all connected WebSocket clients
            for ws in websockets.copy():
                try:
                    await ws.send_str(detection_data)
                except Exception as e:
                    # Remove failed connections
                    websockets.discard(ws)
                    logging.error(f"Failed to send detection data: {e}")

        return frame
        
        # This track just processes frames; we don't return a new video stream.
        # We return the original frame to keep the connection alive if needed,
        # but the client will display the original stream and overlay our data.
        return frame

async def index(request):
    content = open(WEB_DIR / "templates" / "index.html", "r").read()
    return web.Response(content_type="text/html", text=content)

async def javascript(request):
    content = open(WEB_DIR / "static" / "js" / "client_server_inference.js", "r").read()
    return web.Response(content_type="application/javascript", text=content)
    
async def stylesheet(request):
    content = open(WEB_DIR / "static" / "css" / "style.css", "r").read()
    return web.Response(content_type="text/css", text=content)

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pc_id = f"PeerConnection({uuid.uuid4()})"
    pcs.add(pc)

    logging.info(f"[{pc_id}] Created for {request.remote}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logging.info(f"[{pc_id}] Connection state is {pc.connectionState}")
        if pc.connectionState == "closed":
            pcs.discard(pc)

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
app.router.add_get("/style.css", stylesheet)
app.router.add_post("/offer", offer)

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
        print("⚠️  Accept the security warning in your browser")
        web.run_app(app, host="0.0.0.0", port=8443, ssl_context=ssl_context)
    else:
        # Fallback to HTTP
        print("🌐 Starting HTTP server...")
        print("🌐 HTTP URLs:")
        print("   🖥️  Desktop: http://localhost:8080")
        print("   ⚡ Real-time: http://localhost:8080/realtime")
        print("📱 Mobile browsers may not allow camera access over HTTP")
        web.run_app(app, host="0.0.0.0", port=8080)
