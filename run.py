import sys
import os
import traceback

# Add the 'src' directory to the Python path so absolute imports work perfectly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

if __name__ == '__main__':
    try:
        from main import Pyrite
        app = Pyrite()
        app.run()
    except Exception as e:
        with open("crash_log.txt", "w") as f:
            traceback.print_exc(file=f)
        print("\n==================================================")
        print("CRASH DETECTED! Saved to crash_log.txt")
        print("==================================================")
        traceback.print_exc()
        
        try:
            from profiler import global_profiler
            global_profiler.save_report("crash_profiling_results.json")
        except Exception:
            pass

        input("\nPress ENTER to exit...")
