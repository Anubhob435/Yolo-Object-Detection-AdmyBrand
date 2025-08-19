#!/usr/bin/env python3
"""
Test script for the WebRTC Object Detection project.
This script helps verify that all components are working correctly.
"""

import asyncio
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def check_requirements():
    """Check if all required files exist."""
    required_files = [
        "server.py",
        "server_inference.py", 
        "index.html",
        "style.css",
        "client_server_inference.js"
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ Missing required files: {', '.join(missing_files)}")
        return False
    
    print("✅ All required files found")
    return True

def test_basic_signaling():
    """Test the basic signaling server."""
    print("\n🚀 Testing basic signaling server...")
    print("Starting server on ws://localhost:8765")
    print("Press Ctrl+C to stop")
    
    try:
        subprocess.run([sys.executable, "server.py"])
    except KeyboardInterrupt:
        print("\n✅ Signaling server test completed")

def test_inference_server():
    """Test the inference server."""
    print("\n🚀 Testing inference server...")
    print("Starting server on http://localhost:8080")
    print("This will download the YOLO model on first run...")
    print("Press Ctrl+C to stop")
    
    try:
        subprocess.run([sys.executable, "server_inference.py"])
    except KeyboardInterrupt:
        print("\n✅ Inference server test completed")

def export_onnx_model():
    """Export YOLO model to ONNX format."""
    print("\n🔄 Exporting YOLO model to ONNX...")
    try:
        result = subprocess.run([sys.executable, "export_model.py"], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Model exported successfully")
            print(result.stdout)
        else:
            print("❌ Model export failed")
            print(result.stderr)
    except Exception as e:
        print(f"❌ Error during model export: {e}")

def main():
    """Main test function."""
    print("🧪 WebRTC Object Detection Test Suite")
    print("=" * 50)
    
    if not check_requirements():
        print("\nPlease ensure all files are present before running tests.")
        return
    
    while True:
        print("\nSelect test to run:")
        print("1. Test basic signaling server")
        print("2. Test inference server (downloads YOLO model)")
        print("3. Export ONNX model for WASM inference")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            test_basic_signaling()
        elif choice == "2":
            test_inference_server()
        elif choice == "3":
            export_onnx_model()
        elif choice == "4":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-4.")

if __name__ == "__main__":
    main()
