import sys
import os
import pytest
from unittest.mock import patch

# Ensure api module is found
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulator import calculate_amortization_french

def test_french_amortization_logic():
    """
    Verify standard French amortization logic.
    Principal: 100,000
    Rate: 3%
    Years: 10
    """
    # We must mock load_real_mortgage_schedule to ensure we test the formula, 
    # not the real CSV if it exists.
    with patch('simulator.load_real_mortgage_schedule', return_value=[]):
        schedule = calculate_amortization_french(
            principal=100000,
            annual_rate_pct=3.0,
            years=10
        )
    
    # Check basics
    assert len(schedule) == 120 # 10 years * 12 months
    
    first_month = schedule[0]
    # Interest for month 1: 100,000 * 0.03 / 12 = 250
    # The function rounds to 2 decimals
    assert abs(first_month["interest"] - 250.0) < 0.01
    
    # Total principal paid should equal initial principal
    total_principal_paid = sum(item["principal"] for item in schedule)
    # Allow small rounding error
    assert abs(total_principal_paid - 100000) < 1.0

def test_amortization_zero_interest():
    """
    Verify 0% interest logic (simple division).
    """
    with patch('simulator.load_real_mortgage_schedule', return_value=[]):
        schedule = calculate_amortization_french(
            principal=12000,
            annual_rate_pct=0.0,
            years=1
        )
        
    assert len(schedule) == 12 # 1 year
    
    first_month = schedule[0]
    assert first_month["interest"] == 0.0
    assert first_month["principal"] == 1000.0 # 12000 / 12
