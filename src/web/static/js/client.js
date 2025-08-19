const video = document.getElementById('webcam');
const canvas = document.getElementById('overlay');
const ctx = canvas.getContext('2d');

const SIGNALING_SERVER_URL = 'ws://localhost:8765';
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

// This peer will only receive video, not send it.
// The logic to send video will be on the phone's browser.
peerConnection.ontrack = (event) => {
    video.srcObject = event.streams[0];
    video.onloadedmetadata = () => {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
    };
};

async function start() {
    try {
        // For the phone/sending peer
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'environment' } // Use rear camera
        });
        video.srcObject = stream;
        stream.getTracks().forEach(track => peerConnection.addTrack(track, stream));

        const offer = await peerConnection.createOffer();
        await peerConnection.setLocalDescription(offer);
        ws.onopen = () => {
            ws.send(JSON.stringify({ offer: peerConnection.localDescription }));
        };

    } catch (error) {
        console.error('Error accessing media devices.', error);
    }
}

// In a real application, you'd have logic to determine if this client
// is the sender or receiver. For this demo, we assume the first client
// to load the page is the sender.
start();
