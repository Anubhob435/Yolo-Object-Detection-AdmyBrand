const video = document.getElementById('webcam');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');
const startBtn = document.getElementById('start-btn');
const stopBtn = document.getElementById('stop-btn');
const status = document.getElementById('status');

let detections = [];
let pc = null;
let stream = null;

function updateStatus(message, type = 'info') {
    status.textContent = message;
    status.className = type === 'error' ? 'error' : type === 'warning' ? 'warning' : '';
}

async function main() {
    try {
        updateStatus("Initializing...");
        
        pc = new RTCPeerConnection({
            iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });

        pc.onicecandidate = event => {
            // This event is not used in this simplified offer/answer exchange,
            // but is required for more complex ICE negotiations.
        };

        pc.ontrack = event => {
            // For this architecture, we don't display the remote stream
            // The server processes the video and sends back detection data
            console.log('Server track received (processing only)');
        };
        
        pc.ondatachannel = event => {
            const datachannel = event.channel;
            datachannel.onmessage = (event) => {
                try {
                    detections = JSON.parse(event.data);
                } catch (e) {
                    console.error("Error parsing detection data:", e);
                }
            };
            updateStatus("Data channel established");
        };

        stream = await navigator.mediaDevices.getUserMedia({
            video: { 
                facingMode: 'environment', 
                width: { ideal: 640 }, 
                height: { ideal: 480 } 
            }
        });
        
        console.log('Camera stream obtained:', stream);
        video.srcObject = stream;
        
        // Ensure video plays
        video.play().catch(e => console.log('Video play error:', e));
        
        stream.getTracks().forEach(track => pc.addTrack(track, stream));
        
        video.onloadedmetadata = () => {
            console.log('Video metadata loaded. Dimensions:', video.videoWidth, 'x', video.videoHeight);
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            requestAnimationFrame(drawLoop);
            updateStatus("Camera ready - detecting objects...");
        };

        // Add additional video event listeners for debugging
        video.oncanplay = () => {
            console.log('Video can start playing');
            updateStatus("Video preview ready");
        };
        
        video.onerror = (e) => {
            console.error('Video error:', e);
            updateStatus("Video error", "error");
        };

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);

        updateStatus("Connecting to server...");
        const response = await fetch('/offer', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ sdp: pc.localDescription.sdp, type: pc.localDescription.type }),
        });
        
        if (!response.ok) {
            throw new Error(`Server responded with ${response.status}`);
        }
        
        const answer = await response.json();
        await pc.setRemoteDescription(new RTCSessionDescription(answer));
        
        updateStatus("Connected - Object detection active");
        startBtn.disabled = true;
        stopBtn.disabled = false;
        
    } catch (error) {
        console.error('Error in main():', error);
        updateStatus(`Error: ${error.message}`, 'error');
        cleanup();
    }
}

function drawLoop() {
    if (!video.srcObject) return;
    
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    
    detections.forEach(det => {
        const [x1, y1, x2, y2] = det.box;
        const x = x1 * canvas.width;
        const y = y1 * canvas.height;
        const width = (x2 - x1) * canvas.width;
        const height = (y2 - y1) * canvas.height;

        // Draw bounding box
        ctx.strokeStyle = '#00FF00';
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, width, height);

        // Draw label background
        ctx.fillStyle = 'rgba(0, 255, 0, 0.8)';
        const label = `${det.label} ${(det.confidence * 100).toFixed(1)}%`;
        ctx.font = '14px Arial';
        const textMetrics = ctx.measureText(label);
        const textHeight = 16;
        ctx.fillRect(x, y > textHeight ? y - textHeight : y, textMetrics.width + 8, textHeight);

        // Draw label text
        ctx.fillStyle = '#000000';
        ctx.fillText(label, x + 4, y > textHeight ? y - 4 : y + 12);
    });

    requestAnimationFrame(drawLoop);
}

function cleanup() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }
    if (pc) {
        pc.close();
        pc = null;
    }
    video.srcObject = null;
    detections = [];
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    startBtn.disabled = false;
    stopBtn.disabled = true;
    updateStatus("Stopped");
}

startBtn.addEventListener('click', main);
stopBtn.addEventListener('click', cleanup);

// Handle page unload
window.addEventListener('beforeunload', cleanup);
