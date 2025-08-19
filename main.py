#!/usr/bin/env python3
"""
Main entry point for WebRTC Object Detection project.
This file provides easy access to the main functionalities.
"""

import sys
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Main entry point with command-line interface."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebRTC Object Detection")
    parser.add_argument("command", choices=["signaling", "inference", "export"], 
                       help="Command to run")
    
    args = parser.parse_args()
    
    if args.command == "signaling":
        from src.server.signaling import main as signaling_main
        signaling_main()
    elif args.command == "inference":
        from src.server.inference import main as inference_main
        inference_main()
    elif args.command == "export":
        from scripts.export_model import export_yolo_to_onnx
        export_yolo_to_onnx()

if __name__ == "__main__":
    main()
