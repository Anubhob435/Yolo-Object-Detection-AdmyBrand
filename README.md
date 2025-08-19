# WebRTC Real-Time Object Detection

This project implements real-time object detection over WebRTC using two different architectures:

1. **Server-side inference** using Python with aiortc and YOLO
2. **Client-side inference** using WebAssembly (WASM) with ONNX

## Project Structure

```
webrtc-object-detection/
├── src/
│   ├── server/                  # Server-side components
│   │   ├── signaling.py        # WebSocket signaling server
│   │   └── inference.py        # Object detection inference server
│   └── web/                    # Web frontend components
│       ├── templates/          # HTML pages
│       └── static/            # CSS, JavaScript assets
├── models/                     # ML models (PyTorch & ONNX)
├── scripts/                    # Utility scripts
│   ├── run.py                 # Quick start launcher
│   └── export_model.py        # Model export utility
├── docs/                      # Documentation
└── examples/                  # Example implementations
```

For detailed structure information, see [docs/STRUCTURE.md](docs/STRUCTURE.md).

## Setup Instructions

### 1. Install Dependencies

The project uses `uv` as the package manager. Dependencies are already installed.

### 2. Download YOLO Model

The YOLO model will be automatically downloaded when you first run the server:

```bash
python scripts/run.py inference
```

### 3. Export Model to ONNX (for WASM inference)

To use client-side inference, export the YOLO model to ONNX format:

```bash
python scripts/run.py export
```

This will create a `yolov8n.onnx` file in the `models/` directory.

## Running the Demos

### Option 1: Server-Side Inference

1. **Start the inference server:**
   ```bash
   python scripts/run.py inference
   ```

2. **Open the demo in your browser:**
   Navigate to `http://localhost:8080`

3. **Allow camera access** and click "Start Camera"

4. The server will process the video stream and send detection results back to the browser

### Option 2: Client-Side WASM Inference

1. **Start the basic signaling server:**
   ```bash
   python scripts/run.py signaling
   ```

2. **Serve the files** (you'll need a web server for WASM):
   ```bash
   # Using Python's built-in server
   python -m http.server 8000
   ```

3. **Open the WASM demo:**
   Navigate to `http://localhost:8000/src/web/templates/index_wasm.html`

4. The inference will run entirely in your browser

### Option 3: Basic WebRTC Streaming

1. **Start the signaling server:**
   ```bash
   python scripts/run.py signaling
   ```

2. **Serve the files:**
   ```bash
   python -m http.server 8000
   ```

3. **Open the basic demo:**
   Navigate to `http://localhost:8000/src/web/templates/basic.html`

## Architecture Comparison

| Feature | Server-Side | Client-Side |
|---------|-------------|-------------|
| **Latency** | Higher (network RTT) | Ultra-low (local processing) |
| **Privacy** | Lower (video sent to server) | Higher (video stays local) |
| **Performance** | Consistent (server GPU) | Variable (client device) |
| **Scalability** | Expensive (server resources) | High (distributed processing) |
| **Model Size** | Large models supported | Limited by browser |

## Usage Notes

### For Mobile Testing

- Use HTTPS or `localhost` for camera access
- The `facingMode: 'environment'` constraint requests the rear camera
- For front camera, use `facingMode: 'user'`

### STUN/TURN Servers

The demo uses Google's public STUN server. For production:
- Use your own STUN/TURN servers
- Consider services like Twilio, Agora, or AWS Kinesis

### Security Considerations

- **HTTPS Required**: WebRTC requires secure contexts
- **Camera Permissions**: Users must grant camera access
- **Privacy**: Server-side processing sends video data to your server

## Customization

### Adjusting Detection Confidence

In `server_inference.py`, modify the confidence threshold:
```python
if box.conf > 0.4:  # Change this value (0.0 to 1.0)
```

### Using Different Models

Replace `yolov8n.pt` with other YOLO models:
- `yolov8s.pt` (small)
- `yolov8m.pt` (medium)
- `yolov8l.pt` (large)
- `yolov8x.pt` (extra large)

### Adding Custom Classes

Modify the label mapping in the detection processing code to show custom class names instead of generic labels.

## Troubleshooting

### Common Issues

1. **Camera not working**: Ensure HTTPS or localhost
2. **Model download fails**: Check internet connection
3. **High CPU usage**: Try smaller YOLO model variants
4. **WebRTC connection fails**: Check firewall/NAT settings

### Performance Tips

- Use smaller input resolution for better performance
- Adjust frame rate in camera constraints
- Consider GPU acceleration for ONNX Runtime

## Technical Details

This implementation follows the comprehensive guide detailed in `instructions.md`, which covers:

- WebRTC foundation and signaling
- Peer-to-peer media streaming
- Real-time video processing
- Object detection integration
- Privacy and performance considerations

For the complete technical documentation, refer to the `instructions.md` file.
