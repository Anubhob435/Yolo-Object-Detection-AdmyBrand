# Project Structure

```
webrtc-object-detection/
├── README.md                    # Main project documentation
├── pyproject.toml              # Python project configuration
├── requirements.txt            # Python dependencies
├── uv.lock                     # UV package manager lock file
├── .python-version             # Python version specification
├── .gitignore                  # Git ignore patterns
│
├── src/                        # Source code
│   ├── __init__.py
│   ├── server/                 # Server-side components
│   │   ├── __init__.py
│   │   ├── signaling.py        # WebSocket signaling server
│   │   └── inference.py        # Object detection inference server
│   │
│   └── web/                    # Web frontend components
│       ├── __init__.py
│       ├── templates/          # HTML templates
│       │   ├── index.html      # Main demo page (server inference)
│       │   ├── index_wasm.html # WASM inference demo page
│       │   └── basic.html      # Basic WebRTC streaming demo
│       │
│       └── static/             # Static web assets
│           ├── js/             # JavaScript files
│           │   ├── client.js                    # Basic WebRTC client
│           │   ├── client_server_inference.js   # Server-side inference client
│           │   └── client_wasm_inference.js     # WASM inference client
│           │
│           └── css/            # Stylesheets
│               └── style.css   # Main stylesheet
│
├── models/                     # ML models
│   ├── yolov8n.pt             # PyTorch YOLO model (6.2 MB)
│   └── yolov8n.onnx           # ONNX YOLO model (12.2 MB)
│
├── scripts/                    # Utility scripts
│   ├── run.py                 # Quick start script
│   ├── export_model.py        # Model export utility
│   └── test.py                # Test suite
│
├── docs/                       # Documentation
│   ├── instructions.md        # Comprehensive technical guide
│   └── STATUS.md              # Project status and setup info
│
└── examples/                   # Example implementations
    └── (future example code)
```

## Directory Descriptions

### `/src/`
Core application source code organized into logical modules:

- **`server/`**: Backend components for WebRTC and object detection
  - `signaling.py`: WebSocket server for WebRTC signaling
  - `inference.py`: Main server with real-time object detection

- **`web/`**: Frontend web application components
  - `templates/`: HTML pages for different demo modes
  - `static/`: CSS, JavaScript, and other web assets

### `/models/`
Machine learning models in different formats:
- PyTorch models (`.pt`) for server-side inference
- ONNX models (`.onnx`) for browser-based inference

### `/scripts/`
Utility scripts for development and deployment:
- `run.py`: Easy-to-use launcher for different demo modes
- `export_model.py`: Convert PyTorch models to ONNX format
- `test.py`: Comprehensive testing suite

### `/docs/`
Project documentation:
- Technical guides and implementation details
- Setup instructions and troubleshooting

### `/examples/`
Reserved for future example implementations and tutorials

## Benefits of This Structure

1. **Separation of Concerns**: Clear distinction between server, web, and utility code
2. **Scalability**: Easy to add new components without cluttering the root directory
3. **Maintainability**: Related files are grouped together logically
4. **Professional**: Follows Python packaging best practices
5. **Extensibility**: Simple to add new features, models, or examples

## Usage with New Structure

```bash
# Run from project root
python scripts/run.py inference    # Start inference server
python scripts/run.py signaling   # Start signaling server
python scripts/run.py export      # Export models to ONNX
```

## Import Structure

```python
# Server components
from src.server.signaling import *
from src.server.inference import *

# Web components (if needed in Python)
from src.web import *
```
