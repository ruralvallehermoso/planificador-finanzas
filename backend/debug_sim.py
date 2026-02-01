import sys
from datetime import date, datetime
from simulator import load_real_mortgage_schedule, compare_mortgage_vs_portfolio

def debug():
    print(f"Current System Date: {date.today()}")
    
    # 1. Load Schedule
    try:
        schedule = load_real_mortgage_schedule()
        print(f"Loaded {len(schedule)} schedule items.")
    except Exception as e:
        print(f"Error loading schedule: {e}")
        return

    # 2. Check key dates
    print("\n--- Checking Schedule Dates ---")
    target_dates = ["2025-12-31", "2026-01-31", "2026-02-28"]
    for item in schedule[:5]:
        d = item["date"]
        print(f"Month {item['month']}: Date={d}, Int={item['interest']}, CumInt={item['cumulative_interest']}")
    
    # 3. Run Comparison
    # Dummy portfolio values
    result = compare_mortgage_vs_portfolio(
        portfolio_value=100000,
        portfolio_basis=90000,
        tax_rate_pct=19,
        mortgage_schedule=schedule
    )
    
    print("\n--- Comparison Result ---")
    print(f"Total Interest Paid: {result['total_interest_paid']}")
    
    # Check if 2026-01-31 interest is included
    # Dec 2025 Int: 129.57
    # Jan 2026 Int: 207.43
    # Expected Total: 337.00
    expected = 337.00
    if abs(result['total_interest_paid'] - expected) < 1.0:
        print("SUCCESS: Jan 2026 payment included.")
    else:
        print(f"FAILURE: Expected {expected}, got {result['total_interest_paid']}")

if __name__ == "__main__":
    debug()
