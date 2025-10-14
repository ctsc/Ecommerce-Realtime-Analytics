"""
Metrics collection and monitoring for the pipeline.
Tracks performance, throughput, and system health.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from collections import defaultdict, deque
import threading


@dataclass
class PipelineMetrics:
    """Container for pipeline performance metrics."""
    
    # Throughput metrics
    transactions_processed: int = 0
    transactions_per_second: float = 0.0
    
    # Latency metrics (in seconds)
    avg_latency: float = 0.0
    p95_latency: float = 0.0
    p99_latency: float = 0.0
    
    # Fraud detection metrics
    fraud_detected: int = 0
    fraud_rate: float = 0.0
    false_positives: int = 0
    false_negatives: int = 0
    
    # Data quality metrics
    quality_score: float = 100.0
    null_records: int = 0
    duplicate_records: int = 0
    invalid_records: int = 0
    
    # System metrics
    uptime_seconds: float = 0.0
    error_count: int = 0
    
    # Timestamps
    last_updated: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "throughput": {
                "total_processed": self.transactions_processed,
                "per_second": self.transactions_per_second
            },
            "latency": {
                "average": self.avg_latency,
                "p95": self.p95_latency,
                "p99": self.p99_latency
            },
            "fraud_detection": {
                "detected": self.fraud_detected,
                "rate": self.fraud_rate
            },
            "data_quality": {
                "score": self.quality_score,
                "null_records": self.null_records,
                "duplicates": self.duplicate_records,
                "invalid": self.invalid_records
            },
            "system": {
                "uptime_hours": self.uptime_seconds / 3600,
                "error_count": self.error_count
            },
            "last_updated": self.last_updated.isoformat()
        }


class MetricsCollector:
    """
    Collects and aggregates metrics from the pipeline.
    Thread-safe implementation for concurrent access.
    """
    
    def __init__(self, window_size: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            window_size: Number of recent samples to keep for calculations
        """
        self.window_size = window_size
        self.start_time = time.time()
        
        # Thread-safe counters
        self._lock = threading.Lock()
        
        # Metric storage
        self.transaction_count = 0
        self.fraud_count = 0
        self.error_count = 0
        self.null_count = 0
        self.duplicate_count = 0
        self.invalid_count = 0
        
        # Latency tracking (keep recent samples)
        self.latencies: deque = deque(maxlen=window_size)
        
        # Throughput tracking
        self.transaction_timestamps: deque = deque(maxlen=window_size)
        
    def record_transaction(self, latency: float = None):
        """
        Record a processed transaction.
        
        Args:
            latency: Processing latency in seconds
        """
        with self._lock:
            self.transaction_count += 1
            self.transaction_timestamps.append(time.time())
            
            if latency is not None:
                self.latencies.append(latency)
    
    def record_fraud(self):
        """Record a fraud detection."""
        with self._lock:
            self.fraud_count += 1
    
    def record_error(self):
        """Record an error."""
        with self._lock:
            self.error_count += 1
    
    def record_null(self):
        """Record a null value issue."""
        with self._lock:
            self.null_count += 1
    
    def record_duplicate(self):
        """Record a duplicate record."""
        with self._lock:
            self.duplicate_count += 1
    
    def record_invalid(self):
        """Record an invalid record."""
        with self._lock:
            self.invalid_count += 1
    
    def get_metrics(self) -> PipelineMetrics:
        """
        Calculate and return current metrics.
        
        Returns:
            PipelineMetrics object with current values
        """
        with self._lock:
            metrics = PipelineMetrics()
            
            # Basic counts
            metrics.transactions_processed = self.transaction_count
            metrics.fraud_detected = self.fraud_count
            metrics.error_count = self.error_count
            metrics.null_records = self.null_count
            metrics.duplicate_records = self.duplicate_count
            metrics.invalid_records = self.invalid_count
            
            # Uptime
            metrics.uptime_seconds = time.time() - self.start_time
            
            # Throughput (transactions per second)
            if len(self.transaction_timestamps) > 1:
                time_window = self.transaction_timestamps[-1] - self.transaction_timestamps[0]
                if time_window > 0:
                    metrics.transactions_per_second = len(self.transaction_timestamps) / time_window
            
            # Latency percentiles
            if self.latencies:
                sorted_latencies = sorted(self.latencies)
                n = len(sorted_latencies)
                
                metrics.avg_latency = sum(sorted_latencies) / n
                metrics.p95_latency = sorted_latencies[int(n * 0.95)] if n > 0 else 0
                metrics.p99_latency = sorted_latencies[int(n * 0.99)] if n > 0 else 0
            
            # Fraud rate
            if self.transaction_count > 0:
                metrics.fraud_rate = (self.fraud_count / self.transaction_count) * 100
            
            # Data quality score (100 - percentage of bad records)
            if self.transaction_count > 0:
                bad_records = self.null_count + self.duplicate_count + self.invalid_count
                metrics.quality_score = max(0, 100 - (bad_records / self.transaction_count) * 100)
            
            metrics.last_updated = datetime.now()
            
            return metrics
    
    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.transaction_count = 0
            self.fraud_count = 0
            self.error_count = 0
            self.null_count = 0
            self.duplicate_count = 0
            self.invalid_count = 0
            self.latencies.clear()
            self.transaction_timestamps.clear()
            self.start_time = time.time()


# Global metrics collector instance
metrics_collector = MetricsCollector()


