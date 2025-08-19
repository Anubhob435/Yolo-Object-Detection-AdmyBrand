// NOTE: This script assumes you have included the ONNX Runtime Web library in your HTML:
// <script src="https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js"></script>

const video = document.getElementById('webcam');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');

// --- WebRTC Signaling Setup (from Section 1) ---
const SIGNALING_SERVER_URL = 'ws://localhost:8765'; // Use your signaling server URL
const peerConnection = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
});
const ws = new WebSocket(SIGNALING_SERVER_URL);

ws.onmessage = async (message) => {
    const data = JSON.parse(message.data);
    if (data.offer) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.offer));
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        ws.send(JSON.stringify({ answer: peerConnection.localDescription }));
    } else if (data.answer) {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(data.answer));
    } else if (data.candidate) {
        await peerConnection.addIceCandidate(new RTCIceCandidate(data.candidate));
    }
};

peerConnection.onicecandidate = (event) => {
    if (event.candidate) {
        ws.send(JSON.stringify({ candidate: event.candidate }));
    }
};

peerConnection.ontrack = (event) => {
    video.srcObject = event.streams[0];
    video.onloadedmetadata = () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
    };
};

// --- ONNX Model and Inference Setup ---
let session;
const MODEL_URL = 'yolov8n.onnx'; // Place this in the same directory as your HTML
const modelInputShape = [1, 3, 640, 640];

async function loadModel() {
    try {
        console.log('Loading model...');
        session = await ort.InferenceSession.create(MODEL_URL, {
            executionProviders: ['wasm'], // 'webgl' is another option for GPU
        });
        console.log('Model loaded successfully.');
    } catch (e) {
        console.error(`Failed to load the model: ${e}`);
    }
}

async function detectObjects() {
    if (!session || video.paused || video.ended) {
        requestAnimationFrame(detectObjects);
        return;
    }

    // 1. Preprocess the frame
    const { input, xRatio, yRatio } = preprocess(video);
    
    // 2. Run inference
    const feeds = { images: input };
    const results = await session.run(feeds);

    // 3. Postprocess the results
    const boxes = postprocess(results, xRatio, yRatio);
    
    // 4. Draw the results
    drawBoxes(boxes);

    requestAnimationFrame(detectObjects);
}

function preprocess(source) {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    canvas.width = modelInputShape[2];
    canvas.height = modelInputShape[3];
    
    const xRatio = canvas.width / source.videoWidth;
    const yRatio = canvas.height / source.videoHeight;

    context.drawImage(source, 0, 0, canvas.width, canvas.height);
    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
    const { data } = imageData;
    const float32Data = new Float32Array(modelInputShape[1] * modelInputShape[2] * modelInputShape[3]);

    // Convert pixel data to planar RGB format and normalize
    for (let i = 0; i < data.length; i += 4) {
        const j = i / 4;
        float32Data[j] = data[i] / 255.0;         // R
        float32Data[j + (canvas.width * canvas.height)] = data[i + 1] / 255.0; // G
        float32Data[j + 2 * (canvas.width * canvas.height)] = data[i + 2] / 255.0; // B
    }

    const inputTensor = new ort.Tensor('float32', float32Data, modelInputShape);
    return { input: inputTensor, xRatio, yRatio };
}

function postprocess(results, xRatio, yRatio) {
    // This is a simplified postprocessing function for YOLOv8 ONNX output.
    // The actual tensor shape and parsing logic may vary based on the exact export format.
    const output = results.output0.data;
    const boxes = [];
    // Assuming output shape is [1, 84, 8400] and format is [cx, cy, w, h, class_probs...]
    for (let i = 0; i < 8400; i++) {
        const [class_id, prob] = [...Array(80).keys()]
           .map(col => [col, output[8400 * (col + 4) + i]])
           .reduce((a, b) => a[1] > b[1] ? a : b, [0, 0]);

        if (prob < 0.5) { // Confidence threshold
            continue;
        }

        const xc = output[i];
        const yc = output[i + 8400];
        const w = output[i + 2 * 8400];
        const h = output[i + 3 * 8400];

        boxes.push({
            x: (xc - w / 2) / xRatio,
            y: (yc - h / 2) / yRatio,
            width: w / xRatio,
            height: h / yRatio,
            label: `class_${class_id}`, // Replace with actual class names
            confidence: prob,
        });
    }

    // A simple Non-Max Suppression would be needed here for better results
    return boxes;
}

function drawBoxes(boxes) {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    boxes.forEach(box => {
        ctx.strokeStyle = '#FF0000';
        ctx.lineWidth = 2;
        ctx.strokeRect(box.x, box.y, box.width, box.height);

        ctx.fillStyle = '#FF0000';
        ctx.font = '16px Arial';
        const label = `${box.label} ${box.confidence.toFixed(2)}`;
        ctx.fillText(label, box.x, box.y > 10 ? box.y - 5 : 10);
    });
}

async function setupWebcamAndStart() {
    // This function combines WebRTC setup with model loading and inference start
    // In a real app, you would separate sender/receiver logic.
    // This example assumes the client is both sender and receiver/processor.
    await loadModel();
    
    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } });
    video.srcObject = stream;
    
    video.onloadedmetadata = () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        detectObjects(); // Start the detection loop
    };
}

setupWebcamAndStart();
