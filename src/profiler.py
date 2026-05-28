import time
import json
import threading
import numpy as np
from collections import deque
from contextlib import contextmanager
from functools import wraps

class ThreadSampleBuffer:
    """Isolated, memory-bounded buffer dedicated to a specific thread's metrics."""
    def __init__(self, max_samples):
        self.max_samples = max_samples
        self.categories = {}
        # Simple lock used *only* when adding a new category to prevent iteration crashes
        self.lock = threading.Lock()

    def record(self, category, elapsed_time):
        if category not in self.categories:
            with self.lock:
                if category not in self.categories:
                    self.categories[category] = deque(maxlen=self.max_samples)
        # deque.append is thread-safe in CPython, so we don't need a lock here!
        self.categories[category].append(elapsed_time)


class Profiler:
    """
    Production-grade game telemetry system.
    - Zero lock-contention during chunk generation/rendering.
    - No memory leaks (Bounded memory footprints).
    - Perfect multi-thread data aggregation (No data loss on thread exit).
    - Safe, synchronous, non-corrupting shutdown reports.
    """
    def __init__(self, max_samples_per_category=10000):
        self.max_samples = max_samples_per_category
        self.registry_lock = threading.Lock()
        
        # Maps Thread ID -> ThreadSampleBuffer
        self.thread_buffers = {}
        
        # Main-thread specific tracking for frame times
        self.frame_start_time = 0

    def _get_buffer(self):
        """Retrieves or registers a dedicated data buffer for the calling thread."""
        thread_id = threading.get_ident()
        # Fast look-up without locking if already registered
        if thread_id in self.thread_buffers:
            return self.thread_buffers[thread_id]
            
        with self.registry_lock:
            # Double-checked locking pattern
            if thread_id not in self.thread_buffers:
                self.thread_buffers[thread_id] = ThreadSampleBuffer(self.max_samples)
            return self.thread_buffers[thread_id]

    def start_frame(self):
        """Called exclusively on the main game loop thread."""
        self.frame_start_time = time.perf_counter()

    def end_frame(self):
        """Called exclusively on the main game loop thread."""
        if self.frame_start_time > 0:
            self.record("Frame_Total", time.perf_counter() - self.frame_start_time)

    def record(self, category, elapsed_time):
        """Records metrics completely lock-free relative to other concurrent threads."""
        buf = self._get_buffer()
        buf.record(category, elapsed_time)

    @contextmanager
    def measure(self, category):
        """Context manager for clean block profiling."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            self.record(category, time.perf_counter() - start_time)

    def profile_func(self, category=None):
        """Decorator to profile entire methods."""
        def decorator(func):
            cat = category or func.__name__
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.measure(cat):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def save_report(self, filename="profiling_results.json"):
        """
        Consolidates metrics across ALL active and dead background worker loops,
        and saves synchronously to prevent file corruption on application exit.
        """
        print(f"\n[TELEMETRY] Compiling engine metrics from all threads...")
        
        # Aggregated storage: Category -> Combined List of samples
        master_records = {}

        # Safely extract data from all registered thread buffers
        with self.registry_lock:
            for thread_id, buf in self.thread_buffers.items():
                with buf.lock: # Ensures a thread doesn't add a new category while we iterate
                    for category, samples in buf.categories.items():
                        if category not in master_records:
                            master_records[category] = []
                        # Copy out the data samples safely
                        master_records[category].extend(list(samples))

        # Calculate metrics
        report = {}
        for category, times in master_records.items():
            if not times:
                continue
                
            arr = np.array(times) * 1000  # Convert to milliseconds
            report[category] = {
                "Calls": len(arr),
                "Avg_ms": round(float(np.mean(arr)), 3),
                "Min_ms": round(float(np.min(arr)), 3),
                "Max_ms": round(float(np.max(arr)), 3),
                "P99_ms": round(float(np.percentile(arr, 99)), 3),
                "Total_Time_ms": round(float(np.sum(arr)), 3)
            }

        # Write synchronously. Because this is executed on exit, blocking the main thread
        # for a few milliseconds is completely acceptable and prevents file corruption.
        try:
            with open(filename, 'w') as f:
                json.dump(report, f, indent=4)
            print(f"[TELEMETRY] Report successfully saved to {filename}")
        except Exception as e:
            print(f"[TELEMETRY] ERROR: Failed to write report file: {e}")

global_profiler = Profiler()
