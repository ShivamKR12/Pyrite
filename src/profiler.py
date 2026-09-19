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
        # Store the strict numerical cap for how many samples this buffer will retain per category
        self.max_samples: int = max_samples

        # A dictionary mapping string category names to fixed-length double-ended queues (deques)
        self.categories: Dict[str, deque[float]] = {}

        # A lightweight mutex lock utilized exclusively during the initialization of a new category key
        self.lock: threading.Lock = threading.Lock()

    def record(self, category: str, elapsed_time: float) -> None:
        """
        Record a single profiling sample for the specified category.

        Args:
            category: Logical category name for the timing sample.
            elapsed_time: Elapsed time in nanoseconds to record.
        """
        # Fast-path check: if the category is not yet tracked, we must safely initialize it
        if category not in self.categories:
            # Acquire the thread lock to prevent a race condition where two threads might initialize the same key
            with self.lock:
                # Double-checked locking pattern: verify the category is still absent after acquiring the lock
                if category not in self.categories:
                    # Allocate a new deque with a strict memory bound (maxlen) to automatically eject old samples
                    self.categories[category] = deque(maxlen=self.max_samples)

        # In CPython, appending to a deque is an atomic operation, meaning it is inherently thread-safe
        # We push the new nanosecond timing sample onto the end of the queue without needing a lock
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
        # Define the global threshold for how many samples each thread buffer is permitted to hold
        self.max_samples: int = max_samples_per_category

        # A global mutex lock utilized when a brand new thread needs to register itself with the profiler
        self.registry_lock: threading.Lock = threading.Lock()

        # A mapping of OS-level Thread IDs (integers) to their respective isolated ThreadSampleBuffers
        self.thread_buffers: Dict[int, ThreadSampleBuffer] = {}

        # Main-thread specific tracking variable used to measure the absolute duration of an entire game loop frame
        self.frame_start_time: float = 0.0

    def _get_buffer(self) -> ThreadSampleBuffer:
        """Retrieves or registers a dedicated data buffer for the calling thread."""
        # Query the operating system for the current executing thread's unique integer ID
        thread_id: int = threading.get_ident()

        # Fast-path check: If this thread has already been registered, return its buffer immediately (no lock needed)
        if thread_id in self.thread_buffers:
            return self.thread_buffers[thread_id]

        # If this is the thread's first time profiling, acquire the global registry lock to safely mutate the dictionary
        with self.registry_lock:
            # Double-checked locking pattern: ensure another thread didn't register this ID while we were waiting
            if thread_id not in self.thread_buffers:
                # Instantiate a fresh, memory-bounded ThreadSampleBuffer specifically for this Thread ID
                self.thread_buffers[thread_id] = ThreadSampleBuffer(self.max_samples)

            # Return the newly allocated or verified thread buffer
            return self.thread_buffers[thread_id]

    def start_frame(self) -> None:
        """Called exclusively on the main game loop thread."""
        # Capture the absolute, high-resolution hardware nanosecond timestamp for the start of the frame
        self.frame_start_time = time.perf_counter_ns()

    def end_frame(self) -> None:
        """Called exclusively on the main game loop thread."""
        # Ensure that start_frame was actually called and we have a valid baseline timestamp
        if self.frame_start_time > 0:
            # Calculate the total elapsed nanoseconds and submit it to the 'Frame_Total' category
            self.record('Frame_Total', time.perf_counter_ns() - self.frame_start_time)

    def record(self, category: str, elapsed_time: float) -> None:
        """Records metrics completely lock-free relative to other concurrent threads."""
        # Dynamically fetch the isolated data buffer belonging to the current executing thread
        buf: ThreadSampleBuffer = self._get_buffer()

        # Delegate the actual storage of the timing sample to the thread-local buffer
        buf.record(category, elapsed_time)

    @contextmanager
    def measure(self, category: str) -> Generator[None, None, None]:
        """Context manager for clean block profiling."""
        # Capture the initial high-resolution hardware clock timestamp in nanoseconds
        start_time: float = time.perf_counter_ns()
        try:
            # Yield execution control back to the inner block of code encapsulated by the `with` statement
            yield
        finally:
            # Once the inner block terminates (even if it throws an exception), capture the new timestamp
            # Calculate the delta (elapsed time in nanoseconds) and dispatch it to the profiler registry
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

        # This outer function takes the optional category argument and returns the actual decorator mechanism
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            # Determine the categorization string: use the explicit argument if provided, otherwise default to the function's internal name
            cat: str = category or func.__name__

            # The @wraps decorator preserves the original function's metadata (docstrings, name) through the wrapping process
            @wraps(func)
            def wrapper(*args: Any, **kwargs: Any) -> Any:
                # Intercept the function invocation and wrap it within our custom `measure` context manager
                # This ensures the call stack is tracked and the execution time is automatically logged under the calculated category
                with self.measure(cat):
                    # Forward all positional and keyword arguments to the original function and return its result
                    return func(*args, **kwargs)

            # Return the newly wrapped, telemetry-enabled function
            return wrapper

        # Return the decorator generator
        return decorator

    def save_report(self, filename: str = 'profiling_results.json') -> None:
        """
        Consolidates metrics across ALL active and dead background worker loops,
        and saves synchronously to prevent file corruption on application exit.
        """
        print('\n[TELEMETRY] Compiling engine metrics from all threads...')

        # Initialize a master dictionary to aggregate samples across all distinct ThreadSampleBuffers
        # Structure: Category Name -> Flat List of all recorded nanosecond timings
        master_records: Dict[str, List[float]] = {}

        # Acquire the global registry lock to freeze thread registration while we harvest data
        with self.registry_lock:
            # Iterate over every registered thread ID and its corresponding data buffer
            for thread_id, buf in self.thread_buffers.items():
                # Acquire the specific thread buffer's lock to prevent category mutation during iteration
                with buf.lock:
                    # Iterate over all categories and their respective deques of timing samples
                    for category, samples in buf.categories.items():
                        # If the master record doesn't have this category yet, initialize an empty list
                        if category not in master_records:
                            master_records[category] = []
                        # Safely cast the deque to a list and extend the master record with these thread-specific samples
                        master_records[category].extend(list(samples))

        # Initialize the final dictionary that will be serialized into the JSON report
        report: Dict[str, Dict[str, Any]] = {}

        # Iterate over the fully aggregated master records
        for category, times in master_records.items():
            # If a category was registered but received zero timing samples, skip it to keep the report clean
            if not times:
                continue

            # Convert the raw Python list into a high-performance NumPy array for vectorized mathematics
            # We divide by 1,000,000.0 to convert the raw nanosecond inputs into human-readable milliseconds
            arr: NDArray[np.float64] = np.array(times, dtype=np.float64) / 1_000_000.0

            # Calculate comprehensive statistical metrics for this category using NumPy's built-in C-optimized functions
            report[category] = {
                # The absolute number of times this category was executed and measured
                'Calls': len(arr),
                # The arithmetic mean (average) execution time in milliseconds, rounded to 3 decimal places
                'Avg_ms': round(float(np.mean(arr)), 3),
                # The fastest single execution time recorded in milliseconds
                'Min_ms': round(float(np.min(arr)), 3),
                # The slowest single execution time recorded in milliseconds
                'Max_ms': round(float(np.max(arr)), 3),
                # The 99th percentile execution time (removes the top 1% of outliers/spikes)
                'P99_ms': round(float(np.percentile(arr, 99)), 3),
                # The cumulative time spent inside this category across all threads
                'Total_Time_ms': round(float(np.sum(arr)), 3),
            }

        # Attempt to synchronously write the aggregated dictionary out to a file
        # Synchronous blocking here is acceptable because this function is only invoked during engine teardown
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                # Serialize the dictionary to a nicely formatted JSON string and write it to disk
                json.dump(report, f, indent=4)
            print(f'[TELEMETRY] Report successfully saved to {filename}')
        except Exception as e:
            # Catch any filesystem permissions or IO errors and log them to the console to avoid a silent crash
            print(f'[TELEMETRY] ERROR: Failed to write report file: {e}')


global_profiler: Profiler = Profiler()
