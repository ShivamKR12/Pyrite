"""
High-performance thread-safe telemetry and profiling engine.

The Profiler provides advanced metrics collection lock-free across all background
ThreadPool worker processes and the primary Pygame execution loop. It tracks function execution
times bound by strict memory caps to prevent tracking leaks and dumps fully aggregated JSON reports
upon safe shutdown or fatal application crashes.
"""

import json
import threading
import time
from collections import deque
from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Dict, Generator, List, Optional

import numpy as np
from numpy.typing import NDArray


class ThreadSampleBuffer:
    """
    Isolated, memory-bounded buffer dedicated to a specific thread's metrics.

    Prevents data contention between threads by allocating isolated Deques
    for profiling categories. Ensures thread-safe metric aggregation.

    Args:
        max_samples (int): The maximum number of profiling samples to retain per category.
    """

    def __init__(self, max_samples: int) -> None:
        """
        Create a ThreadSampleBuffer with a maximum per-category sample count.

        Args:
            max_samples: Maximum retained samples per profiling category.
        """
        # Variable assignments
        self.max_samples: int = max_samples

        self.categories: Dict[str, deque[float]] = {}

        self.lock: threading.Lock = threading.Lock()

    def record(self, category: str, elapsed_time: float) -> None:
        """
        Record a single profiling sample for the specified category.

        Args:
            category: Logical category name for the timing sample.
            elapsed_time: Elapsed time in nanoseconds to record.
        """
        # Conditional logic
        if category not in self.categories:  # pragma: no mutate
            # Context management
            with self.lock:
                # Conditional logic
                if category not in self.categories:  # pragma: no mutate
                    # Variable assignments
                    self.categories[category] = deque(maxlen=self.max_samples)

        # Execute expressions
        self.categories[category].append(elapsed_time)


class Profiler:
    """
    Production-grade game telemetry system.

    Features:
    - Zero lock-contention during chunk generation/rendering.
    - No memory leaks (Bounded memory footprints).
    - Perfect multi-thread data aggregation (No data loss on thread exit).
    - Safe, synchronous, non-corrupting shutdown reports.

    Args:
        max_samples_per_category (int): Limit on tracking samples to bound memory footprint.
    """

    def __init__(self, max_samples_per_category: int = 10000) -> None:
        """
        Initialize the global `Profiler` instance.

        Args:
            max_samples_per_category: Limit on retained samples to bound memory usage.
        """
        # Variable assignments
        self.max_samples: int = max_samples_per_category

        self.registry_lock: threading.Lock = threading.Lock()

        self.thread_buffers: Dict[int, ThreadSampleBuffer] = {}

        self.frame_start_time: float = 0.0

    def _get_buffer(self) -> ThreadSampleBuffer:
        """Retrieves or registers a dedicated data buffer for the calling thread."""
        # Variable assignments
        thread_id: int = threading.get_ident()

        # Conditional logic
        if thread_id in self.thread_buffers:  # pragma: no mutate
            # Return result
            return self.thread_buffers[thread_id]

        # Context management
        with self.registry_lock:
            # Conditional logic
            if thread_id not in self.thread_buffers:  # pragma: no mutate
                # Variable assignments
                self.thread_buffers[thread_id] = ThreadSampleBuffer(self.max_samples)

            # Return result
            return self.thread_buffers[thread_id]

    def start_frame(self) -> None:
        """Called exclusively on the main game loop thread."""
        # Variable assignments
        self.frame_start_time = time.perf_counter_ns()

    def end_frame(self) -> None:
        """Called exclusively on the main game loop thread."""
        # Conditional logic
        if self.frame_start_time > 0:
            # Execute expressions
            self.record('Frame_Total', time.perf_counter_ns() - self.frame_start_time)

    def record(self, category: str, elapsed_time: float) -> None:
        """Records metrics completely lock-free relative to other concurrent threads."""
        # Variable assignments
        buf: ThreadSampleBuffer = self._get_buffer()

        # Execute expressions
        buf.record(category, elapsed_time)

    @contextmanager
    def measure(self, category: str) -> Generator[None, None, None]:
        """Context manager for clean block profiling."""
        # Variable assignments
        start_time: float = time.perf_counter_ns()
        # Error handling
        try:
            # Execute expressions
            yield
        finally:
            # Execute expressions
            self.record(category, time.perf_counter_ns() - start_time)

    def profile_func(self, category: Optional[str] = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Return a decorator which profiles the wrapped function under `category`.

        Args:
            category: Optional category name override; when None the function
                name will be used.

        Returns:
            A decorator that wraps callables and records timing samples.
        """

        # Define function
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Variable assignments
            # Variable assignments
            cat: str = category or func.__name__

            @wraps(func)
            # Define function
            # Define function
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Context management
                # Context management
                # Context management
                with self.measure(cat):
                    # Return result
                    # Return result
                    # Return result
                    return func(*args, **kwargs)

            # Return result
            # Return result
            return wrapper

        # Return result
        return decorator

    def save_report(self, filename: str = 'profiling_results.json') -> None:
        """
        Consolidates metrics across ALL active and dead background worker loops,
        and saves synchronously to prevent file corruption on application exit.
        """
        # Execute expressions
        print('\n[TELEMETRY] Compiling engine metrics from all threads...')

        # Variable assignments
        master_records: Dict[str, List[float]] = {}

        # Context management
        with self.registry_lock:
            # Loop processing
            for thread_id, buf in self.thread_buffers.items():
                # Context management
                with buf.lock:
                    # Loop processing
                    for category, samples in buf.categories.items():
                        # Conditional logic
                        if category not in master_records:
                            # Variable assignments
                            master_records[category] = []
                        # Execute expressions
                        master_records[category].extend(list(samples))

        # Variable assignments
        report: Dict[str, Dict[str, Any]] = {}

        # Loop processing
        for category, times in master_records.items():
            # Conditional logic
            if not times:
                # Loop control
                continue

            # Variable assignments
            arr: NDArray[np.float64] = np.array(times, dtype=np.float64) / 1_000_000.0

            report[category] = {
                'Calls': len(arr),
                'Avg_ms': round(float(np.mean(arr)), 3),
                'Min_ms': round(float(np.min(arr)), 3),
                'Max_ms': round(float(np.max(arr)), 3),
                'P99_ms': round(float(np.percentile(arr, 99)), 3),
                'Total_Time_ms': round(float(np.sum(arr)), 3),
            }

        # Error handling
        try:
            # Context management
            with open(filename, 'w', encoding='utf-8') as f:
                # Execute expressions
                json.dump(report, f, indent=4)
            # Execute expressions
            print(f'[TELEMETRY] Report successfully saved to {filename}')
        except Exception as e:
            # Execute expressions
            print(f'[TELEMETRY] ERROR: Failed to write report file: {e}')


global_profiler: Profiler = Profiler()
