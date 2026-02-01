
import sys
import os

# Add current dir to path
sys.path.append(os.getcwd())

import simulator

try:
    schedule = simulator.load_real_mortgage_schedule()
    print(f"Schedule Loaded: {len(schedule)} rows")
    if schedule:
        print(f"First Row: {schedule[0]}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
