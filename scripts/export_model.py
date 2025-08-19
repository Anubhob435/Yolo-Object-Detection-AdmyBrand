from ultralytics import YOLO
from pathlib import Path
import os

def export_yolo_to_onnx():
    """
    Export a pre-trained YOLOv8 model to ONNX format for browser inference.
    """
    # Get the project root directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    models_dir = project_root / "models"
    
    # Ensure models directory exists
    models_dir.mkdir(exist_ok=True)
    
    # Change to models directory for export
    original_cwd = os.getcwd()
    os.chdir(models_dir)
    
    try:
        # Load a pre-trained YOLOv8 model
        model = YOLO("yolov8n.pt")
        
        # Export the model to ONNX format
        # opset=12 is a good choice for compatibility with older runtimes
        model.export(format="onnx", opset=12)
        print(f"Model exported to {models_dir / 'yolov8n.onnx'} successfully!")
    finally:
        # Restore original working directory
        os.chdir(original_cwd)

if __name__ == "__main__":
    export_yolo_to_onnx()
