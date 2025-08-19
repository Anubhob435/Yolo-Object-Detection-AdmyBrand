/**
 * Client-Side Metrics Collection for WebRTC Object Detection
 * Tracks browser-side performance, device impact, and user experience metrics
 */

class ClientMetricsCollector {
    constructor() {
        this.sessionId = `client_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        this.startTime = performance.now();
        this.metrics = {
            session: {
                id: this.sessionId,
                startTime: new Date().toISOString(),
                userAgent: navigator.userAgent,
                platform: navigator.platform
            },
            network: {
                effectiveType: '4g',
                downlink: 10,
                rtt: 50
            },
            device: {
                cpuCores: navigator.hardwareConcurrency || 4,
                deviceMemory: navigator.deviceMemory || 4,
                maxTouchPoints: navigator.maxTouchPoints || 0
            },
            performance: {
                frameCount: 0,
                droppedFrames: 0,
                avgFrameTime: 0,
                peakMemoryUsage: 0,
                batteryLevel: 100,
                batteryCharging: true
            },
            webrtc: {
                connectionState: 'new',
                iceConnectionState: 'new',
                iceCandidatePairs: 0,
                packetsLost: 0,
                packetsReceived: 0,
                bytesReceived: 0,
                jitter: 0
            },
            detection: {
                totalDetections: 0,
                avgConfidence: 0,
                detectionCategories: {},
                processingTimeMs: 0
            },
            privacy: {
                cameraAccess: false,
                microphoneAccess: false,
                locationRequested: false,
                dataSharedExternal: false
            }
        };
        
        this.frameTimings = [];
        this.detectionHistory = [];
        this.rtcPeerConnection = null;
        this.lastStatsTime = 0;
        
        this.initialize();
    }
    
    async initialize() {
        console.log(`🔍 Client Metrics Collector initialized - Session: ${this.sessionId}`);
        
        // Get network information if available
        if ('connection' in navigator) {
            const connection = navigator.connection;
            this.metrics.network.effectiveType = connection.effectiveType || '4g';
            this.metrics.network.downlink = connection.downlink || 10;
            this.metrics.network.rtt = connection.rtt || 50;
            
            // Listen for network changes
            connection.addEventListener('change', () => {
                this.metrics.network.effectiveType = connection.effectiveType;
                this.metrics.network.downlink = connection.downlink;
                this.metrics.network.rtt = connection.rtt;
            });
        }
        
        // Get battery information if available
        if ('getBattery' in navigator) {
            try {
                const battery = await navigator.getBattery();
                this.metrics.performance.batteryLevel = Math.round(battery.level * 100);
                this.metrics.performance.batteryCharging = battery.charging;
                
                // Listen for battery changes
                battery.addEventListener('chargingchange', () => {
                    this.metrics.performance.batteryCharging = battery.charging;
                });
                battery.addEventListener('levelchange', () => {
                    this.metrics.performance.batteryLevel = Math.round(battery.level * 100);
                });
            } catch (error) {
                console.warn('Battery API not available:', error);
            }
        }
        
        // Monitor memory usage
        if ('memory' in performance) {
            setInterval(() => {
                const memInfo = performance.memory;
                const currentMemory = memInfo.usedJSHeapSize / 1024 / 1024; // MB
                this.metrics.performance.peakMemoryUsage = Math.max(
                    this.metrics.performance.peakMemoryUsage, 
                    currentMemory
                );
            }, 1000);
        }
        
        // Start performance monitoring
        this.startPerformanceMonitoring();
    }
    
    startPerformanceMonitoring() {
        // Monitor frame rate and performance
        let lastTime = performance.now();
        let frameCount = 0;
        
        const measureFrame = (currentTime) => {
            frameCount++;
            const deltaTime = currentTime - lastTime;
            
            if (deltaTime >= 1000) { // Every second
                const fps = Math.round((frameCount * 1000) / deltaTime);
                this.metrics.performance.frameCount += frameCount;
                this.metrics.performance.avgFrameTime = deltaTime / frameCount;
                
                // Reset counters
                frameCount = 0;
                lastTime = currentTime;
                
                // Store frame timing
                this.frameTimings.push({
                    timestamp: new Date().toISOString(),
                    fps: fps,
                    frameTime: this.metrics.performance.avgFrameTime
                });
                
                // Keep only last 60 seconds of data
                if (this.frameTimings.length > 60) {
                    this.frameTimings.shift();
                }
            }
            
            requestAnimationFrame(measureFrame);
        };
        
        requestAnimationFrame(measureFrame);
    }
    
    setRTCPeerConnection(pc) {
        this.rtcPeerConnection = pc;
        
        // Monitor connection state
        pc.addEventListener('connectionstatechange', () => {
            this.metrics.webrtc.connectionState = pc.connectionState;
        });
        
        pc.addEventListener('iceconnectionstatechange', () => {
            this.metrics.webrtc.iceConnectionState = pc.iceConnectionState;
        });
        
        // Start collecting WebRTC stats
        this.startWebRTCStatsCollection();
    }
    
    startWebRTCStatsCollection() {
        if (!this.rtcPeerConnection) return;
        
        const collectStats = async () => {
            try {
                const stats = await this.rtcPeerConnection.getStats();
                
                stats.forEach(report => {
                    if (report.type === 'inbound-rtp' && report.mediaType === 'video') {
                        // Video reception stats
                        this.metrics.webrtc.packetsReceived = report.packetsReceived || 0;
                        this.metrics.webrtc.packetsLost = report.packetsLost || 0;
                        this.metrics.webrtc.bytesReceived = report.bytesReceived || 0;
                        this.metrics.webrtc.jitter = report.jitter || 0;
                        
                        // Calculate frame drop rate
                        if (report.framesDropped && report.framesDecoded) {
                            const totalFrames = report.framesDropped + report.framesDecoded;
                            this.metrics.performance.droppedFrames = 
                                (report.framesDropped / totalFrames) * 100;
                        }
                    }
                    
                    if (report.type === 'candidate-pair' && report.state === 'succeeded') {
                        this.metrics.webrtc.iceCandidatePairs++;
                    }
                });
            } catch (error) {
                console.warn('Error collecting WebRTC stats:', error);
            }
        };
        
        // Collect stats every 5 seconds
        setInterval(collectStats, 5000);
    }
    
    recordCameraAccess(granted) {
        this.metrics.privacy.cameraAccess = granted;
        console.log(`📹 Camera access ${granted ? 'granted' : 'denied'}`);
    }
    
    recordDetection(detections) {
        if (!detections || detections.length === 0) return;
        
        const processingStart = performance.now();
        
        this.metrics.detection.totalDetections += detections.length;
        
        // Calculate average confidence
        const confidences = detections.map(d => d.confidence || 0);
        if (confidences.length > 0) {
            const avgConf = confidences.reduce((a, b) => a + b, 0) / confidences.length;
            this.metrics.detection.avgConfidence = 
                (this.metrics.detection.avgConfidence + avgConf) / 2;
        }
        
        // Count detection categories
        detections.forEach(detection => {
            const className = detection.class || 'unknown';
            if (!this.metrics.detection.detectionCategories[className]) {
                this.metrics.detection.detectionCategories[className] = 0;
            }
            this.metrics.detection.detectionCategories[className]++;
        });
        
        // Record processing time
        this.metrics.detection.processingTimeMs = performance.now() - processingStart;
        
        // Store in history
        this.detectionHistory.push({
            timestamp: new Date().toISOString(),
            count: detections.length,
            avgConfidence: confidences.length > 0 ? 
                confidences.reduce((a, b) => a + b, 0) / confidences.length : 0,
            processingTime: this.metrics.detection.processingTimeMs
        });
        
        // Keep only last 100 detections
        if (this.detectionHistory.length > 100) {
            this.detectionHistory.shift();
        }
    }
    
    recordDataSharing(type, size) {
        this.metrics.privacy.dataSharedExternal = true;
        console.log(`🔒 Data shared: ${type}, Size: ${size} bytes`);
    }
    
    getMetrics() {
        return {
            ...this.metrics,
            runtime: {
                sessionDuration: performance.now() - this.startTime,
                currentTime: new Date().toISOString()
            },
            statistics: this.calculateStatistics()
        };
    }
    
    calculateStatistics() {
        const stats = {};
        
        // Frame rate statistics
        if (this.frameTimings.length > 0) {
            const fpsList = this.frameTimings.map(f => f.fps);
            stats.frameRate = {
                avg: fpsList.reduce((a, b) => a + b, 0) / fpsList.length,
                min: Math.min(...fpsList),
                max: Math.max(...fpsList),
                current: fpsList[fpsList.length - 1] || 0
            };
        }
        
        // Detection statistics
        if (this.detectionHistory.length > 0) {
            const detectionCounts = this.detectionHistory.map(d => d.count);
            const processingTimes = this.detectionHistory.map(d => d.processingTime);
            
            stats.detection = {
                avgDetectionsPerFrame: detectionCounts.reduce((a, b) => a + b, 0) / detectionCounts.length,
                avgProcessingTime: processingTimes.reduce((a, b) => a + b, 0) / processingTimes.length,
                maxProcessingTime: Math.max(...processingTimes),
                detectionRate: this.detectionHistory.filter(d => d.count > 0).length / this.detectionHistory.length * 100
            };
        }
        
        // Network performance
        const packetLossRate = this.metrics.webrtc.packetsReceived > 0 ? 
            (this.metrics.webrtc.packetsLost / this.metrics.webrtc.packetsReceived) * 100 : 0;
        
        stats.network = {
            packetLossRate: packetLossRate,
            effectiveConnection: this.metrics.network.effectiveType,
            estimatedBandwidth: this.metrics.network.downlink
        };
        
        return stats;
    }
    
    exportMetrics() {
        const exportData = {
            metadata: {
                sessionId: this.sessionId,
                exportTime: new Date().toISOString(),
                userAgent: navigator.userAgent,
                sessionDuration: performance.now() - this.startTime
            },
            metrics: this.getMetrics(),
            rawData: {
                frameTimings: this.frameTimings,
                detectionHistory: this.detectionHistory
            }
        };
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], 
            { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = `client_metrics_${this.sessionId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        console.log(`📊 Client metrics exported for session ${this.sessionId}`);
    }
    
    sendMetricsToServer() {
        // Send metrics to server endpoint
        fetch('/metrics/client', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(this.getMetrics())
        }).catch(error => {
            console.warn('Failed to send metrics to server:', error);
        });
    }
    
    startAutoReporting(intervalMs = 30000) {
        setInterval(() => {
            this.sendMetricsToServer();
        }, intervalMs);
        
        console.log(`📡 Started auto-reporting metrics every ${intervalMs}ms`);
    }
}

// Global client metrics instance
window.clientMetrics = new ClientMetricsCollector();
