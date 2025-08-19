# 📱 Camera Preview Troubleshooting Guide

## Issue: Camera stream started but no video preview visible

### Quick Fixes to Try:

#### 1. **Access the Debug Page First**
Before using the main demo, test with the simplified debug page:
```
http://192.168.0.89:8080/debug
```
This will show detailed information about what's happening with your camera.

#### 2. **Common Mobile Browser Issues**

**For Chrome on Android:**
- Ensure you're using HTTPS or localhost (yours should work on local network)
- Allow camera permissions when prompted
- Try refreshing the page if video doesn't appear
- Check if you're in private/incognito mode (try normal mode)

**For Safari on iPhone:**
- Camera access requires user interaction
- Make sure the `muted` attribute is present (I just added this)
- Try tapping the video area to trigger playback

#### 3. **Video Element Issues**
The fixes I just applied:
- ✅ Added `muted` attribute to video element (required for autoplay)
- ✅ Added explicit `video.play()` call with error handling
- ✅ Fixed conflict between local and remote video streams
- ✅ Added debugging information to track video loading

#### 4. **Step-by-Step Debugging**

1. **Test the debug page first:**
   ```
   http://192.168.0.89:8080/debug
   ```

2. **Check browser console:**
   - Open developer tools (F12)
   - Look for error messages in Console tab
   - Check if camera permissions were granted

3. **Try different browsers:**
   - Chrome (usually best)
   - Safari (on iOS)
   - Firefox
   - Edge

#### 5. **What to Look For**

**In the debug page, you should see:**
- "Camera stream obtained"
- "Video metadata loaded" 
- "Video can play"
- "Video is playing"
- Stream dimensions and video ready state

**If you see errors like:**
- "Permission denied" → Allow camera access
- "NotFoundError" → No camera available
- "NotAllowedError" → Camera blocked by browser/settings

### Updated Code Changes Made:

1. **Fixed video stream conflict** - removed remote stream assignment that was overriding local camera
2. **Added `muted` attribute** - required for autoplay on mobile
3. **Enhanced debugging** - more detailed error reporting
4. **Explicit play() call** - ensures video starts playing
5. **Created debug page** - simpler testing environment

### Test Steps:

1. **Restart the server:**
   ```bash
   uv run python scripts/run.py mobile
   ```

2. **Try debug page first:**
   ```
   http://192.168.0.89:8080/debug
   ```

3. **If debug works, try main page:**
   ```
   http://192.168.0.89:8080
   ```

4. **Check what the debug info shows** - this will tell us exactly what's happening

Let me know what you see on the debug page and I can help further troubleshoot!
