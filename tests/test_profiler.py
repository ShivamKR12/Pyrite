"""
Unit tests for the thread-safe telemetry and profiling engine.
"""

import json
import threading
import time
from typing import Any

from profiler import Profiler, ThreadSampleBuffer


def test_thread_sample_buffer() -> None:
    """Tests isolation and memory limits of thread-specific sample buffers."""
    buf = ThreadSampleBuffer(10)
    assert buf.max_samples == 10

    assert not buf.categories

    buf.record('test_cat', 0.5)
    assert 'test_cat' in buf.categories
    assert len(buf.categories['test_cat']) == 1
    assert buf.categories['test_cat'][0] == 0.5

    # Test max_samples behavior
    for i in range(15):
        buf.record('test_cat', float(i))

    assert len(buf.categories['test_cat']) == 10
    # Should contain 5.0 to 14.0 (the last 10 elements)
    assert buf.categories['test_cat'][0] == 5.0
    assert buf.categories['test_cat'][-1] == 14.0


def test_profiler_init() -> None:
    """Tests proper initialization of the root telemetry Profiler."""
    p = Profiler(max_samples_per_category=50)
    assert p.max_samples == 50
    assert p.frame_start_time == 0.0
    assert p.thread_buffers == {}

    # Test default arguments
    p_default = Profiler()
    assert p_default.max_samples == 10000


def test_profiler_get_buffer() -> None:
    """Verifies that each thread receives its own isolated buffer without locks."""
    p = Profiler(max_samples_per_category=5)
    buf = p._get_buffer()
    assert isinstance(buf, ThreadSampleBuffer)
    assert buf.max_samples == 5

    # Same thread should get the exact same buffer
    buf2 = p._get_buffer()
    assert buf is buf2

    # Different thread should get a different buffer
    buf3 = None

    def get_buf_thread() -> None:
        nonlocal buf3
        buf3 = p._get_buffer()

    t = threading.Thread(target=get_buf_thread)
    t.start()
    t.join()

    assert buf3 is not None
    assert buf is not buf3


def test_profiler_record_and_frame() -> None:
    """Verifies frame timing mechanisms and direct sample recording."""
    p = Profiler(max_samples_per_category=5)

    # Test end_frame protection against uninitialized start_frame
    p.end_frame()
    assert 'Frame_Total' not in p._get_buffer().categories

    p.start_frame()
    assert p.frame_start_time > 0.0

    # Busy loop to guarantee a measurable minimum elapsed time across all OSs
    start_time = time.perf_counter()
    while time.perf_counter() - start_time < 0.005:
        pass
    p.end_frame()

    buf = p._get_buffer()
    assert 'Frame_Total' in buf.categories
    assert len(buf.categories['Frame_Total']) == 1
    assert 0.004 < buf.categories['Frame_Total'][0] < 0.5

    p.record('Custom_Cat', 1.23)
    assert 'Custom_Cat' in buf.categories
    assert buf.categories['Custom_Cat'][-1] == 1.23


def test_profiler_decorators() -> None:
    """Tests Context Managers and Function Decorators for automated profiling."""
    p = Profiler(max_samples_per_category=5)

    # Context Manager test
    with p.measure('Context_Cat'):
        pass

    buf = p._get_buffer()
    assert 'Context_Cat' in buf.categories
    assert len(buf.categories['Context_Cat']) == 1

    # Decorator test
    @p.profile_func('Decorated_Cat')
    def dummy_func() -> int:
        return 42

    assert dummy_func() == 42
    assert 'Decorated_Cat' in buf.categories
    assert len(buf.categories['Decorated_Cat']) == 1

    @p.profile_func()
    def dummy_func2() -> int:
        return 43

    assert dummy_func2() == 43
    assert 'dummy_func2' in buf.categories
    assert len(buf.categories['dummy_func2']) == 1


def test_profiler_save_report(tmp_path: Any, capsys: Any, monkeypatch: Any) -> None:
    """Tests compiling isolated multi-thread metrics into a JSON aggregate report."""
    p = Profiler(max_samples_per_category=5)

    # Use highly specific decimals to strictly enforce the round(..., 3) logic
    p.record('Report_Cat', 0.100123)
    p.record('Report_Cat', 0.300345)

    filepath = tmp_path / 'profiling_results.json'
    p.save_report(filename=str(filepath))

    assert filepath.exists()

    # Catch string formatting and print mutations
    captured = capsys.readouterr()
    assert '\n[TELEMETRY] Compiling engine metrics from all threads...\n' in captured.out
    assert f'[TELEMETRY] Report successfully saved to {filepath}\n' in captured.out

    with open(filepath, 'r', encoding='utf-8') as f:
        raw_text = f.read()
        data = json.loads(raw_text)

    # Enforce indent=4 mutation kill
    assert '{\n    "Report_Cat": {' in raw_text
    assert 'Report_Cat' in data
    cat_data = data['Report_Cat']
    assert cat_data['Calls'] == 2
    assert cat_data['Avg_ms'] == 200.234
    assert cat_data['Min_ms'] == 100.123
    assert cat_data['Max_ms'] == 300.345
    assert cat_data['P99_ms'] == 298.343
    assert cat_data['Total_Time_ms'] == 400.468

    # Test empty save
    p2 = Profiler()
    filepath_empty = tmp_path / 'empty_report.json'
    p2.save_report(filename=str(filepath_empty))
    assert filepath_empty.exists()

    with open(filepath_empty, 'r', encoding='utf-8') as f:
        data2 = json.load(f)
    assert data2 == {}

    # Test default filename argument mutation
    monkeypatch.chdir(tmp_path)
    p3 = Profiler()
    p3.record('Default_File_Cat', 1.0)
    p3.save_report()
    assert (tmp_path / 'profiling_results.json').exists()

    # Test Error Handling
    p.save_report(filename='/invalid/path/that/doesnt/exist.json')
    captured = capsys.readouterr()
    assert '[TELEMETRY] ERROR: Failed to write report file:' in captured.out
