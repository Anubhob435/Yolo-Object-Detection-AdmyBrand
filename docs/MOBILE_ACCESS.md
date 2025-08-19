# 📱 Mobile Access Guide

## How to Access WebRTC Object Detection on Your Phone

### Quick Setup (3 Steps)

#### 1. **Find Your Computer's IP Address**
```bash
# On Windows (PowerShell)
ipconfig | findstr "IPv4"

# On Mac/Linux
ifconfig | grep "inet "
```
Look for an IP address like `192.168.1.XXX` or `10.0.0.XXX`

#### 2. **Start the Server**
```bash
# From the project directory
uv run python scripts/run.py inference
```

#### 3. **Connect from Your Phone**
- Connect your phone to the **same WiFi network** as your computer
- Open your phone's browser (Chrome recommended)
- Navigate to: `http://YOUR_IP_ADDRESS:8080`
- Example: `http://192.168.1.105:8080`

### 🎯 Complete Step-by-Step Guide

#### Step 1: Get Your Network IP
1. **Windows**: Open PowerShell and run:
   ```powershell
   ipconfig
   ```
   Look for "IPv4 Address" under your WiFi adapter (usually starts with 192.168 or 10.0)

2. **Mac**: Open Terminal and run:
   ```bash
   ifconfig en0 | grep inet
   ```

3. **Linux**: Run:
   ```bash
   hostname -I
   ```

#### Step 2: Start the WebRTC Server
```bash
# Navigate to your project directory
cd "D:\Project Archive\Gemini-answer"

# Start the inference server
uv run python scripts/run.py inference
```

You should see:
```
🚀 Starting inference server...
Server running on http://localhost:8080
======== Running on http://0.0.0.0:8080 ========
```

#### Step 3: Access from Your Phone
1. **Connect to Same WiFi**: Ensure your phone is on the same WiFi network as your computer
2. **Open Browser**: Use Chrome or Safari on your phone
3. **Navigate to Server**: Go to `http://YOUR_IP:8080`
   - Replace `YOUR_IP` with the IP address from Step 1
   - Example: `http://192.168.1.105:8080`
4. **Allow Camera**: When prompted, allow camera access
5. **Start Detection**: Click "Start Camera" button

### 🔧 Troubleshooting

#### Camera Not Working?
- **Use HTTPS**: Some browsers require HTTPS for camera access
- **Try Different Browser**: Chrome usually works best
- **Check Permissions**: Ensure camera permissions are granted
- **Reload Page**: Sometimes a refresh helps

#### Can't Connect to Server?
- **Same Network**: Verify both devices are on the same WiFi
- **Firewall**: Windows Firewall might block connections
  ```powershell
  # Temporarily disable (be careful!)
  netsh advfirewall set allprofiles state off
  # Re-enable after testing
  netsh advfirewall set allprofiles state on
  ```
- **Port Blocking**: Check if port 8080 is available
- **Router Settings**: Some routers block device-to-device communication

#### Alternative: Use ngrok for HTTPS
If you need HTTPS (for camera access), use ngrok:

1. **Install ngrok**: Download from https://ngrok.com/
2. **Start your server**: `uv run python scripts/run.py inference`
3. **Create tunnel**: 
   ```bash
   ngrok http 8080
   ```
4. **Use HTTPS URL**: ngrok will provide an HTTPS URL you can use on your phone

### 🎪 Demo Features on Mobile

Once connected, you can:
- ✅ **Real-time object detection** using your phone's camera
- ✅ **Live bounding boxes** around detected objects
- ✅ **Confidence scores** for each detection
- ✅ **Multiple object types** (people, cars, animals, etc.)
- ✅ **Smooth video streaming** via WebRTC

### 📱 Mobile-Specific Tips

#### Best Experience:
- **Use rear camera**: Better for object detection
- **Good lighting**: Improves detection accuracy
- **Stable connection**: Stay close to WiFi router
- **Chrome browser**: Most compatible with WebRTC

#### Phone Settings:
- **Keep screen on**: Prevent sleep during demo
- **Close other apps**: Free up resources for smooth video
- **Use landscape mode**: Better viewing area

### 🔐 Security Notes

- **Local Network Only**: This setup only works on your local network
- **No Internet Required**: Everything runs locally for privacy
- **Temporary Access**: Server stops when you close the terminal
- **Development Only**: For production, implement proper HTTPS and authentication

### 🌐 Network Architecture

```
Your Computer                    Your Phone
┌─────────────────┐             ┌──────────────┐
│  WebRTC Server  │◄────WiFi────►│   Browser    │
│  (Port 8080)    │             │   (Camera)   │
│  AI Processing  │             │   Display    │
└─────────────────┘             └──────────────┘
```

The phone captures video, sends it to your computer for AI processing, and receives back the detection results - all in real-time!
