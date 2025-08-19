#!/usr/bin/env python3
"""
Quick start script for WebRTC Object Detection demo.
"""

import argparse
import subprocess
import sys
import webbrowser
import time
from pathlib import Path
import os

# Get project paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
SERVER_DIR = PROJECT_ROOT / "src" / "server"

def run_signaling_server():
    """Run the basic signaling server."""
    print("🚀 Starting WebSocket signaling server...")
    print("Server running on ws://localhost:8765")
    print("Press Ctrl+C to stop")
    
    try:
        subprocess.run([sys.executable, str(SERVER_DIR / "signaling.py")])
    except KeyboardInterrupt:
        print("\n✅ Signaling server stopped")

def run_inference_server():
    """Run the inference server with web interface."""
    print("🚀 Starting inference server...")
    print("Server running on http://localhost:8080")
    print("YOLO model will be downloaded on first run...")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(2)
        webbrowser.open("http://localhost:8080")
    
    import threading
    browser_thread = threading.Thread(target=open_browser)
    browser_thread.daemon = True
    browser_thread.start()
    
    try:
        subprocess.run([sys.executable, str(SERVER_DIR / "inference.py")])
    except KeyboardInterrupt:
        print("\n✅ Inference server stopped")

def export_model():
    """Export YOLO model to ONNX format."""
    print("🔄 Exporting YOLO model to ONNX format...")
    try:
        result = subprocess.run([sys.executable, str(SCRIPT_DIR / "export_model.py")])
        if result.returncode == 0:
            print("✅ Model exported successfully to models/yolov8n.onnx")
        else:
            print("❌ Model export failed")
    except Exception as e:
        print(f"❌ Error: {e}")

def setup_mobile_access():
    """Set up server for mobile access with instructions."""
    print("📱 Setting up mobile access...")
    try:
        subprocess.run([sys.executable, str(SCRIPT_DIR / "mobile_setup.py")])
    except KeyboardInterrupt:
        print("\n✅ Mobile server stopped")

def main():
    parser = argparse.ArgumentParser(description="WebRTC Object Detection Quick Start")
    parser.add_argument("command", choices=["signaling", "inference", "export", "mobile"], 
                       help="Command to run")
    parser.add_argument("--no-browser", action="store_true", 
                       help="Don't automatically open browser")
    
    args = parser.parse_args()
    
    # Check if we're in the right project structure
    if not (SERVER_DIR / "signaling.py").exists():
        print("❌ Error: Project structure not found")
        print(f"   Make sure you're in the project root and {SERVER_DIR / 'signaling.py'} exists")
        sys.exit(1)
    
    if args.command == "signaling":
        run_signaling_server()
    elif args.command == "inference":
        run_inference_server()
    elif args.command == "export":
        export_model()
    elif args.command == "mobile":
        setup_mobile_access()
        run_inference_server()
    elif args.command == "export":
        export_model()

if __name__ == "__main__":
    main()
