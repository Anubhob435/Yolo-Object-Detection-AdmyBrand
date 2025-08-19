"""
Comprehensive Metrics Collection System for WebRTC Object Detection
Tracks all performance, network, device, and quality metrics as specified in the architecture document.
"""

import time
import psutil
import json
import asyncio
import statistics
from collections import defaultdict, deque
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging

@dataclass
class LatencyMetrics:
    """Latency-related performance metrics"""
    network_rtt: float = 0.0  # Network round-trip time
    glass_to_glass: float = 0.0  # Total end-to-end latency
    inference_time: float = 0.0  # Model inference time
    frame_processing_time: float = 0.0  # Total frame processing time
    webrtc_connection_time: float = 0.0  # Connection establishment time

@dataclass
class ComputationalMetrics:
    """Computational performance metrics"""
    inference_fps: float = 0.0  # Inference frames per second
    model_load_time: float = 0.0  # Model initialization time
    cpu_usage: float = 0.0  # CPU utilization percentage
    memory_usage: float = 0.0  # Memory usage in MB
    gpu_usage: float = 0.0  # GPU utilization (if available)
    device_temperature: float = 0.0  # Device temperature

@dataclass
class NetworkMetrics:
    """Network-related metrics"""
    video_bandwidth: float = 0.0  # Video stream bandwidth (bytes/sec)
    detection_bandwidth: float = 0.0  # Detection data bandwidth
    packet_loss_rate: float = 0.0  # Packet loss percentage
    connection_success_rate: float = 100.0  # WebRTC connection success
    total_bytes_sent: int = 0  # Total bytes transmitted
    total_bytes_received: int = 0  # Total bytes received

@dataclass
class DetectionQualityMetrics:
    """Object detection quality metrics"""
    total_detections: int = 0  # Total objects detected
    avg_confidence: float = 0.0  # Average confidence score
    detection_categories: Dict[str, int] = None  # Count per object class
    frames_with_detections: int = 0  # Frames containing objects
    total_frames_processed: int = 0  # Total frames analyzed
    
    def __post_init__(self):
        if self.detection_categories is None:
            self.detection_categories = {}

@dataclass
class DeviceImpactMetrics:
    """Device impact and resource usage"""
    battery_usage: float = 0.0  # Battery drain percentage
    thermal_impact: float = 0.0  # Temperature increase
    background_cpu: float = 0.0  # CPU when idle
    peak_memory: float = 0.0  # Peak memory usage
    average_memory: float = 0.0  # Average memory usage

@dataclass
class ScalabilityMetrics:
    """System scalability metrics"""
    concurrent_users: int = 0  # Active connections
    server_cpu_usage: float = 0.0  # Server CPU utilization
    server_memory_usage: float = 0.0  # Server memory usage
    cost_per_user: float = 0.0  # Estimated cost per user
    throughput: float = 0.0  # Requests per second

@dataclass
class PrivacyMetrics:
    """Privacy and security metrics"""
    data_local_processing: float = 100.0  # % processed locally
    data_transmitted_size: int = 0  # Bytes sent to server
    encryption_status: bool = True  # Data encryption status
    ip_exposure_count: int = 0  # IP address exposures
    privacy_events: List[str] = None  # Privacy-related events
    
    def __post_init__(self):
        if self.privacy_events is None:
            self.privacy_events = []

class MetricsCollector:
    """Comprehensive metrics collection and analysis system"""
    
    def __init__(self, window_size: int = 100):
        self.window_size = window_size
        self.start_time = time.time()
        self.session_id = str(int(time.time()))
        
        # Metrics storage with rolling windows
        self.latency_history = deque(maxlen=window_size)
        self.computational_history = deque(maxlen=window_size)
        self.network_history = deque(maxlen=window_size)
        self.detection_history = deque(maxlen=window_size)
        self.device_history = deque(maxlen=window_size)
        
        # Current metrics
        self.current_latency = LatencyMetrics()
        self.current_computational = ComputationalMetrics()
        self.current_network = NetworkMetrics()
        self.current_detection = DetectionQualityMetrics()
        self.current_device = DeviceImpactMetrics()
        self.current_scalability = ScalabilityMetrics()
        self.current_privacy = PrivacyMetrics()
        
        # Timing trackers
        self.frame_start_times = {}
        self.inference_start_times = {}
        self.connection_start_times = {}
        
        # Performance baselines
        self.baseline_cpu = self._get_cpu_usage()
        self.baseline_memory = self._get_memory_usage()
        
        # Statistics
        self.total_frames = 0
        self.total_detections = 0
        self.connection_attempts = 0
        self.successful_connections = 0
        
        logging.info(f"MetricsCollector initialized - Session: {self.session_id}")
    
    def _get_cpu_usage(self) -> float:
        """Get current CPU usage percentage"""
        try:
            return psutil.cpu_percent(interval=0.1)
        except:
            return 0.0
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except:
            return 0.0
    
    def _get_system_memory(self) -> float:
        """Get system memory usage percentage"""
        try:
            return psutil.virtual_memory().percent
        except:
            return 0.0
    
    def start_frame_processing(self, frame_id: str):
        """Mark the start of frame processing"""
        self.frame_start_times[frame_id] = time.time()
    
    def start_inference(self, frame_id: str):
        """Mark the start of model inference"""
        self.inference_start_times[frame_id] = time.time()
    
    def end_inference(self, frame_id: str):
        """Mark the end of model inference and calculate timing"""
        if frame_id in self.inference_start_times:
            inference_time = time.time() - self.inference_start_times[frame_id]
            self.current_latency.inference_time = inference_time
            del self.inference_start_times[frame_id]
    
    def end_frame_processing(self, frame_id: str, detections: List[Dict]):
        """Mark the end of frame processing and update metrics"""
        if frame_id in self.frame_start_times:
            processing_time = time.time() - self.frame_start_times[frame_id]
            self.current_latency.frame_processing_time = processing_time
            del self.frame_start_times[frame_id]
        
        # Update detection metrics
        self.total_frames += 1
        self.current_detection.total_frames_processed = self.total_frames
        
        if detections:
            self.current_detection.frames_with_detections += 1
            self.total_detections += len(detections)
            self.current_detection.total_detections = self.total_detections
            
            # Calculate average confidence
            confidences = [det.get('confidence', 0) for det in detections]
            if confidences:
                self.current_detection.avg_confidence = sum(confidences) / len(confidences)
            
            # Count detection categories
            for detection in detections:
                class_name = detection.get('class', 'unknown')
                if class_name not in self.current_detection.detection_categories:
                    self.current_detection.detection_categories[class_name] = 0
                self.current_detection.detection_categories[class_name] += 1
        
        # Update computational metrics
        self.current_computational.cpu_usage = self._get_cpu_usage()
        self.current_computational.memory_usage = self._get_memory_usage()
        
        # Calculate FPS
        if len(self.latency_history) > 0:
            recent_times = [m.frame_processing_time for m in list(self.latency_history)[-10:]]
            if recent_times and all(t > 0 for t in recent_times):
                avg_time = sum(recent_times) / len(recent_times)
                self.current_computational.inference_fps = 1.0 / avg_time if avg_time > 0 else 0
        
        # Store metrics in history
        self.latency_history.append(LatencyMetrics(**asdict(self.current_latency)))
        self.computational_history.append(ComputationalMetrics(**asdict(self.current_computational)))
        self.detection_history.append(DetectionQualityMetrics(**asdict(self.current_detection)))
    
    def record_network_metrics(self, bytes_sent: int = 0, bytes_received: int = 0):
        """Record network-related metrics"""
        self.current_network.total_bytes_sent += bytes_sent
        self.current_network.total_bytes_received += bytes_received
        
        # Calculate bandwidth (bytes per second over last second)
        now = time.time()
        if len(self.network_history) > 0:
            time_diff = now - (self.start_time + len(self.network_history))
            if time_diff > 0:
                self.current_network.video_bandwidth = bytes_sent / time_diff
        
        self.network_history.append(NetworkMetrics(**asdict(self.current_network)))
    
    def record_connection_attempt(self):
        """Record a WebRTC connection attempt"""
        self.connection_attempts += 1
        self.connection_start_times[self.connection_attempts] = time.time()
    
    def record_connection_success(self, connection_id: int = None):
        """Record a successful WebRTC connection"""
        self.successful_connections += 1
        
        if connection_id and connection_id in self.connection_start_times:
            connection_time = time.time() - self.connection_start_times[connection_id]
            self.current_latency.webrtc_connection_time = connection_time
            del self.connection_start_times[connection_id]
        
        # Update success rate
        if self.connection_attempts > 0:
            self.current_network.connection_success_rate = (
                self.successful_connections / self.connection_attempts * 100
            )
    
    def record_privacy_event(self, event_type: str, details: str = ""):
        """Record privacy-related events"""
        event = f"{datetime.now().isoformat()}: {event_type} - {details}"
        self.current_privacy.privacy_events.append(event)
        
        if event_type == "data_transmitted":
            self.current_privacy.data_local_processing = max(0, 
                self.current_privacy.data_local_processing - 1)
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get all current metrics as a dictionary"""
        return {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - self.start_time,
            "latency": asdict(self.current_latency),
            "computational": asdict(self.current_computational),
            "network": asdict(self.current_network),
            "detection_quality": asdict(self.current_detection),
            "device_impact": asdict(self.current_device),
            "scalability": asdict(self.current_scalability),
            "privacy": asdict(self.current_privacy)
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistical analysis of collected metrics"""
        stats = {}
        
        # Latency statistics
        if self.latency_history:
            inference_times = [m.inference_time for m in self.latency_history if m.inference_time > 0]
            if inference_times:
                stats["latency"] = {
                    "avg_inference_time": statistics.mean(inference_times),
                    "min_inference_time": min(inference_times),
                    "max_inference_time": max(inference_times),
                    "median_inference_time": statistics.median(inference_times),
                    "std_inference_time": statistics.stdev(inference_times) if len(inference_times) > 1 else 0
                }
        
        # FPS statistics
        if self.computational_history:
            fps_values = [m.inference_fps for m in self.computational_history if m.inference_fps > 0]
            if fps_values:
                stats["performance"] = {
                    "avg_fps": statistics.mean(fps_values),
                    "min_fps": min(fps_values),
                    "max_fps": max(fps_values),
                    "median_fps": statistics.median(fps_values)
                }
        
        # Detection statistics
        stats["detection"] = {
            "detection_rate": (self.current_detection.frames_with_detections / 
                             max(1, self.current_detection.total_frames_processed)) * 100,
            "avg_detections_per_frame": (self.current_detection.total_detections / 
                                       max(1, self.current_detection.total_frames_processed)),
            "most_detected_classes": dict(sorted(
                self.current_detection.detection_categories.items(), 
                key=lambda x: x[1], reverse=True)[:5])
        }
        
        return stats
    
    def export_metrics(self, filepath: Optional[str] = None) -> str:
        """Export all metrics to JSON file"""
        if filepath is None:
            filepath = f"metrics_session_{self.session_id}.json"
        
        export_data = {
            "metadata": {
                "session_id": self.session_id,
                "export_time": datetime.now().isoformat(),
                "total_runtime": time.time() - self.start_time,
                "total_frames": self.total_frames,
                "total_detections": self.total_detections
            },
            "current_metrics": self.get_current_metrics(),
            "statistics": self.get_statistics(),
            "raw_history": {
                "latency": [asdict(m) for m in self.latency_history],
                "computational": [asdict(m) for m in self.computational_history],
                "network": [asdict(m) for m in self.network_history],
                "detection": [asdict(m) for m in self.detection_history]
            }
        }
        
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logging.info(f"Metrics exported to {filepath}")
        return filepath

# Global metrics collector instance
metrics_collector = MetricsCollector()

def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance"""
    return metrics_collector
