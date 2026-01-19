from datetime import datetime, date
from typing import List, Dict, Any
import math

def load_real_mortgage_schedule() -> List[Dict[str, Any]]:
    """Loads the real mortgage schedule from Embedded Data."""
    import csv
    import io
    from mortgage_data import MORTGAGE_CSV_DATA

    schedule = []
    try:
        f = io.StringIO(MORTGAGE_CSV_DATA)
        reader = csv.DictReader(f)
        
        # First pass: Load rows and sum total interest
        loaded_rows = []
        total_projected_interest = 0.0
        
        for row in reader:
            loaded_rows.append(row)
            total_projected_interest += float(row["Intereses"])
        
        # Second pass: Build schedule
        schedule = []
        prev_cum_int = 0.0
        prev_cum_princip = 0.0
        
        for i, row in enumerate(loaded_rows, 1):
            intereses = float(row["Intereses"])
            amort = float(row["Amortizacion"])
            
            cum_int = prev_cum_int + intereses
            cum_princip = prev_cum_princip + amort
            
            pending_int = total_projected_interest - cum_int
            # Fix precision issues
            if pending_int < 0.01: pending_int = 0.0
            
            # Normalize date to YYYY-MM-DD
            date_str = row["Fecha"]
            try:
                if "/" in date_str:
                    from datetime import datetime
                    dt = datetime.strptime(date_str, "%d/%m/%Y")
                    date_iso = dt.strftime("%Y-%m-%d")
                else:
                    date_iso = date_str
            except:
                date_iso = date_str

            schedule.append({
                "month": i,
                "date": date_iso,
                "payment": round(float(row["Total_Pago"]), 2),
                "interest": round(intereses, 2),
                "principal": round(amort, 2),
                "remaining_balance": round(float(row["Saldo_Pendiente"]), 2),
                "cumulative_interest": round(cum_int, 2),
                "cumulative_principal": round(cum_princip, 2),
                "pending_interest": round(pending_int, 2)
            })
            
            prev_cum_int = cum_int
            prev_cum_princip = cum_princip
            
    except Exception as e:
        print(f"⚠️ Error loading mortgage CSV: {e}")
        import traceback
        traceback.print_exc()
        raise e
    return schedule

def calculate_amortization_french(principal: float, annual_rate_pct: float, years: int) -> List[Dict[str, Any]]:
    """
    Calculates the amortization schedule. Prioritizes the real CSV if it exists.
    """
    real_schedule = load_real_mortgage_schedule()
    if real_schedule:
        return real_schedule

    monthly_rate = (annual_rate_pct / 100) / 12
    num_payments = years * 12
    
    if monthly_rate == 0:
        monthly_payment = principal / num_payments
    else:
        monthly_payment = (monthly_rate * principal) / (1 - (1 + monthly_rate)**(-num_payments))
    
    schedule = []
    remaining_balance = principal
    cumulative_interest = 0.0
    cumulative_principal = 0.0
    
    for i in range(1, num_payments + 1):
        interest_payment = remaining_balance * monthly_rate
        principal_payment = monthly_payment - interest_payment
        remaining_balance -= principal_payment
        
        # Ensure precision / handle rounding at the end
        if i == num_payments or remaining_balance < 0:
            remaining_balance = 0.0
            
        cumulative_interest += interest_payment
        cumulative_principal += principal_payment
        
        schedule.append({
            "month": i,
            "payment": round(monthly_payment, 2),
            "interest": round(interest_payment, 2),
            "principal": round(principal_payment, 2),
            "remaining_balance": round(remaining_balance, 2),
            "cumulative_interest": round(cumulative_interest, 2),
            "cumulative_principal": round(cumulative_principal, 2)
        })
        
    return schedule

def compare_mortgage_vs_portfolio(
    portfolio_value: float,
    portfolio_basis: float,
    tax_rate_pct: float,
    mortgage_schedule: List[Dict[str, Any]],
    start_date: date = None
) -> Dict[str, Any]:
    """
    Compares the current portfolio gain vs the cumulative mortgage interest paid.
    """
    gross_benefit = portfolio_value - portfolio_basis
    taxes = max(0, gross_benefit * (tax_rate_pct / 100))
    net_benefit = gross_benefit - taxes
    
    # Calculate interest paid UP TO TODAY
    total_interest_paid = 0.0
    if mortgage_schedule:
        today = date.today()
        # Find the last installment that has actually occurred
        for item in mortgage_schedule:
            item_date_str = item.get("date")
            if item_date_str:
                try:
                    # Handle both datetime.date and string in case of mix
                    if isinstance(item_date_str, str):
                        item_date = datetime.strptime(item_date_str[:10], "%Y-%m-%d").date()
                    else:
                        item_date = item_date_str
                        
                    if item_date <= today:
                        total_interest_paid = item["cumulative_interest"]
                    else:
                        break
                except Exception:
                    continue
            else:
                # Fallback for synthetic schedules
                if start_date:
                    months_passed = (today.year - start_date.year) * 12 + (today.month - start_date.month)
                    if months_passed > 0:
                        target_month = min(months_passed, len(mortgage_schedule))
                        total_interest_paid = mortgage_schedule[target_month - 1]["cumulative_interest"]
                    break
    
    balance = net_benefit - total_interest_paid
    is_profitable = balance > 0
    
    return {
        "portfolio_value": round(portfolio_value, 2),
        "portfolio_basis": round(portfolio_basis, 2),
        "net_benefit": round(net_benefit, 2),
        "total_interest_paid": round(total_interest_paid, 2),
        "balance": round(balance, 2),
        "is_profitable": is_profitable,
        "roi_pct": round((balance / portfolio_basis * 100), 2) if portfolio_basis > 0 else 0.0
    }


def calculate_daily_comparison(
    portfolio_history: List[Dict[str, Any]],
    portfolio_basis: float,
    tax_rate_pct: float,
    mortgage_principal: float,
    mortgage_rate_pct: float,
    mortgage_schedule: List[Dict[str, Any]],
    start_date: date
) -> List[Dict[str, Any]]:
    """
    Generates a daily breakdown of portfolio net benefit vs mortgage interest paid.
    Uses discrete installments from the schedule to ensure flat interest between payments.
    """
    daily_history = []
    
    # Sort portfolio history by date
    portfolio_history.sort(key=lambda x: x["date"])
    
    for entry in portfolio_history:
        entry_date = entry["date"]
        
        # Determine interest paid globally up to this specific entry_date
        interest_at_date = 0.0
        if mortgage_schedule:
             for item in mortgage_schedule:
                 item_date_val = item.get("date")
                 if item_date_val:
                     if isinstance(item_date_val, str):
                         item_date = datetime.strptime(item_date_val[:10], "%Y-%m-%d").date()
                     else:
                         item_date = item_date_val
                     
                     if item_date <= entry_date:
                         interest_at_date = item["cumulative_interest"]
                     else:
                         break
                 else:
                     # Fallback to daily logic for synthetic schedules
                     days_passed = (entry_date - start_date).days
                     daily_rate = (mortgage_rate_pct / 100) / 365
                     interest_at_date = mortgage_principal * daily_rate * max(0, days_passed)
                     break
        else:
             # Fallback if no schedule provided at all
             days_passed = (entry_date - start_date).days
             daily_rate = (mortgage_rate_pct / 100) / 365
             interest_at_date = mortgage_principal * daily_rate * max(0, days_passed)

        # Portfolio gain
        gross_benefit = entry["value"] - portfolio_basis
        taxes = max(0, gross_benefit * (tax_rate_pct / 100))
        net_benefit = gross_benefit - taxes
        
        daily_history.append({
            "date": entry_date.isoformat(),
            "net_benefit": round(net_benefit, 2),
            "interest_paid": round(interest_at_date, 2),
            "balance": round(net_benefit - interest_at_date, 2)
        })
        
    return daily_history
