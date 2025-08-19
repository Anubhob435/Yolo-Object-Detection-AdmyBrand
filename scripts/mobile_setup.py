#!/usr/bin/env python3
"""
Mobile-friendly server setup for WebRTC Object Detection.
This script helps you access the demo from your phone on the same network.
"""

import socket
import subprocess
import sys
from pathlib import Path

def get_local_ip():
    """Get the local IP address of this machine."""
    try:
        # Connect to a remote address to determine local IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"

def print_mobile_instructions(local_ip, port=8080):
    """Print instructions for accessing from mobile."""
    url = f"http://{local_ip}:{port}"
    
    print("📱 MOBILE ACCESS INSTRUCTIONS")
    print("=" * 60)
    print(f"🌐 Your Server URL: {url}")
    print("=" * 60)
    print()
    
    print("� STEPS TO CONNECT YOUR PHONE:")
    print(f"1. Connect your phone to the SAME WiFi network as this computer")
    print(f"2. Open your phone's browser (Chrome recommended)")
    print(f"3. Type this URL: {url}")
    print(f"4. Allow camera permissions when prompted")
    print(f"5. Click 'Start Camera' and point at objects!")
    print()
    
    print("⚠️  IMPORTANT:")
    print("• Both devices MUST be on the same WiFi network")
    print("• Use Chrome browser on your phone for best results")
    print("• Allow camera permissions when asked")
    print("• Point your phone's rear camera at objects to detect")
    print()
    
    print("🔧 IF IT DOESN'T WORK:")
    print("• Check Windows Firewall (may need to allow port 8080)")
    print("• Try restarting both devices' WiFi connections")
    print("• Ensure your router allows device-to-device communication")
    print("• Some browsers may require HTTPS - use Chrome if possible")
    print()

def setup_mobile_server():
    """Set up the server for mobile access."""
    local_ip = get_local_ip()
    
    print("🚀 Setting up WebRTC Object Detection for mobile access...")
    print()
    
    print_mobile_instructions(local_ip)
    
    # Get project paths
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    server_path = project_root / "src" / "server" / "inference.py"
    
    print("🎯 Starting server in 3 seconds...")
    print("   (Press Ctrl+C to stop)")
    print()
    
    import time
    time.sleep(3)
    
    try:
        # Run the inference server
        subprocess.run([sys.executable, str(server_path)])
    except KeyboardInterrupt:
        print("\n✅ Server stopped")

if __name__ == "__main__":
    setup_mobile_server()
