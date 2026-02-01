
import csv
from datetime import date
from dateutil.relativedelta import relativedelta

# Params from image
principal = 127000.0
annual_rate = 1.96
years = 15
start_date = date(2025, 12, 31) # First payment
regular_start_date = date(2026, 1, 31)

def calc_payment(p, r, n):
    mr = r / 12 / 100
    if mr == 0: return p / n
    return p * mr / (1 - (1 + mr)**(-n))

monthly_rate = annual_rate / 100 / 12
num_regular_payments = years * 12
regular_payment = calc_payment(principal, annual_rate, num_regular_payments) # Should be ~814.92

print(f"Regular Payment: {regular_payment}")

rows = []

# Row 1: Interest only / Partial
# Image: 129.57 Int, 0 Amort, 127000 Balance.
# This looks like ~16 days of interest? or just a fixed amount.
# I will use exact values from image for Row 1.
row1 = {
    "Fecha": "31/12/2025",
    "Total_Pago": 129.57,
    "Intereses": 129.57,
    "Amortizacion": 0.00,
    "Saldo_Pendiente": 127000.00
}
rows.append(row1)

current_balance = 127000.00
total_interest = 129.57

# Row 2..181
current_date = regular_start_date

for i in range(num_regular_payments):
    interest = current_balance * monthly_rate
    amort = regular_payment - interest
    
    # Adjust last payment
    if i == num_regular_payments - 1:
        amort = current_balance
        regular_payment = interest + amort
        
    current_balance -= amort
    if current_balance < 0: current_balance = 0
    
    rows.append({
        "Fecha": current_date.strftime("%d/%m/%Y"),
        "Total_Pago": round(regular_payment, 2),
        "Intereses": round(interest, 2),
        "Amortizacion": round(amort, 2),
        "Saldo_Pendiente": round(current_balance, 2)
    })
    total_interest += interest
    
    current_date += relativedelta(months=1)
    # Fix end of month logic
    import calendar
    last_day = calendar.monthrange(current_date.year, current_date.month)[1]
    current_date = current_date.replace(day=last_day)

# Write to CSV
with open('mortgage_schedule.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["Fecha", "Total_Pago", "Intereses", "Amortizacion", "Saldo_Pendiente"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print(f"CSV Generated. Total Interest: {total_interest:.2f}")
