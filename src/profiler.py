import time
import json
import threading
import os
import numpy as np
from contextlib import contextmanager
from functools import wraps


class Profiler:
    """
    Live in-game telemetry tracker. Safely records execution times across multiple 
    threads and dumps a statistical report upon game exit.
    """
    def __init__(self):
        self.records = {}
        self.lock = threading.Lock()
        self.frame_start_time = 0

    def start_frame(self):
        self.frame_start_time = time.perf_counter()

    def end_frame(self):
        self.record("Frame_Total", time.perf_counter() - self.frame_start_time)

    def record(self, category, elapsed_time):
        """Thread-safe recording of execution times."""
        with self.lock:
            if category not in self.records:
                self.records[category] = []
            self.records[category].append(elapsed_time)

    @contextmanager
    def measure(self, category):
        """Context manager for clean, Pythonic block profiling."""
        start_time = time.perf_counter()
        try:
            yield
        finally:
            self.record(category, time.perf_counter() - start_time)

    def profile_func(self, category=None):
        """Decorator to automatically profile a function."""
        def decorator(func):
            cat = category or func.__name__
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.measure(cat):
                    return func(*args, **kwargs)
            return wrapper
        return decorator

    def save_report(self, filename="profiling_results.json"):
        """Calculates Min, Max, Average, and the 99th Percentile (Stutter detection)."""
        report = {}
        for category, times in self.records.items():
            if not times:
                continue
            arr = np.array(times) * 1000  # Convert to milliseconds
            report[category] = {
                "Calls": len(arr),
                "Avg_ms": round(float(np.mean(arr)), 3),
                "Min_ms": round(float(np.min(arr)), 3),
                "Max_ms": round(float(np.max(arr)), 3),
                "P99_ms": round(float(np.percentile(arr, 99)), 3), # The 1% worst frame drops!
                "Total_Time_ms": round(float(np.sum(arr)), 3)
            }
        
        with open(filename, 'w') as f:
            json.dump(report, f, indent=4)
        print(f"\n[TELEMETRY] Profiling report saved to {filename}")

global_profiler = Profiler()
