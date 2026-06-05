"""
Entry point for the Pyrite game engine.

This script bootstraps the application by configuring the Python module search path,
instantiating the main game loop, and catching fatal execution errors.
Upon a hard crash, it safely dumps stack traces and triggers the asynchronous
profiler to save its telemetry data to disk for deep debugging.
"""

import os
import sys
import traceback
from typing import Any

# Add the 'src' directory to the Python path so absolute imports work perfectly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

if __name__ == '__main__':
    try:
        from main import Pyrite

        app: Any = Pyrite()
        app.run()
    except Exception:
        with open('crash_log.txt', 'w', encoding='utf-8') as f:
            traceback.print_exc(file=f)
        print('\n==================================================')
        print('CRASH DETECTED! Saved to crash_log.txt')
        print('==================================================')
        traceback.print_exc()

        try:
            from profiler import global_profiler

            global_profiler.save_report('crash_profiling_results.json')
        except Exception:
            pass

        input('\nPress ENTER to exit...')
