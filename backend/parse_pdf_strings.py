
import sys
import re
import csv

def parse_pdf_strings():
    # regex for (Content) Tj
    # Content can contain escaped parens \( or \) but simple regex might suffice if no nesting
    # lines look like: (31/12/2025) Tj
    
    # We want to capture the content inside the outer parens.
    # Pattern: ^\((.*)\) Tj$ 
    # But might have trailing newlines inside the parens in the raw output?
    # valid string command output puts content on one line usually?
    # The output from 'strings' command splits newlines. 
    # Example:
    # (127.000,00
    # ) Tj
    # This implies strings might split the content.
    # Actually, looking at previous output:
    # (127.000,00
    # ) Tj
    # The 'strings' command output separates meaningful chunks.
    # I should consume the raw strings output line by line.
    # Look for lines starting with '('.
    # If a line ends with ') Tj', it's a complete text object.
    # If not, it might be multi-line?
    # But for numbers and dates, they seem to be generally short.
    
    # Actually, looking at the previous output:
    # (31/12/2025) Tj
    # (127.000,00
    # ) Tj
    # The number 127.000,00 is split across lines by 'strings' or the PDF stream itself?
    # Wait, 'strings' just outputs printable chars.
    # The PDF stream likely has (127.000,00\n) Tj
    
    # Let's clean up the input.
    # We are piping `strings` output to this script.
    
    lines = sys.stdin.readlines()
    
    # We look for value-like strings.
    # Values we care about: 
    # Dates: DD/MM/YYYY
    # Numbers: X.XXX,XX or XXX,XX or -
    
    current_row = []
    rows = []
    
    # Columns expected: Date, Basis, Amort, Interest, Payment, Balance (6 columns)
    # But sometimes Basis is skipped? NO, the previous output showed 6 items per group.
    
    # Let's extract all "value-like" tokens
    # Token regex: Date or Number
    
    date_pattern = re.compile(r'\d{2}/\d{2}/\d{4}')
    
    # Helper to clean number
    def clean_num(s):
        s = s.replace('(', '').replace(')', '').replace(' Tj', '').strip()
        if s == '-': return 0.0
        # Remove thousands, replace decimal
        s = s.replace('.', '').replace(',', '.')
        try:
            return float(s)
        except:
            return None

    # Helper to detect type
    def is_date(s):
        return bool(date_pattern.search(s))
        
    def is_number(s):
        s = s.strip()
        # (127.000,00) or similar
        # check if it contains digit
        return any(c.isdigit() for c in s) or '-' in s
    
    # Iterate and build
    # We only care about lines starting with '('
    
    cleaned_tokens = []
    for line in lines:
        line = line.strip()
        if not line.startswith('('): continue
        
        # It might be split like:
        # (127.000,00
        # ) Tj -> The 'strings' command puts ') Tj' on next line if pure strings?
        # Actually 'strings' output:
        # (31/12/2025) Tj
        # (127.000,00
        # ) Tj
        # So we should look for content inside ( ).
        # We can just join all lines starting with ( and capture what's inside.
        
        # Simplified approach: Just strip garbage and look for the content.
        # If line has '(', start capturing.
        # If line has ')', stop.
        
        # Actually, let's just use regex on the line if it looks like a token.
        # We know the order: Date -> Basis -> Amort -> Int -> Payment -> Balance
        
        # Clean the token content
        # Remove ( and ) and Tj and trailing/leading junk
        content = line.replace(') Tj', '').replace(')', '').replace('(', '').strip()
        
        # Skip empty or text labels ("Fecha", "Pagina")
        if not content: continue
        if "FECHA" in content or "GINA" in content or "IBERCAJA" in content: continue
        
        # Check if Date
        if is_date(content):
            # If we have a current row being built, and we hit a new date, it means the prev row is done?
            # Or assume fixed size of 6?
            if current_row:
                # Store previous result if valid
                if len(current_row) >= 5: # Some robustness
                    rows.append(current_row)
                current_row = []
            
            current_row.append(content) # Col 0: Date
        
        elif current_row:
            # We are inside a row, gathering numbers
            # Check if it looks like a number
            if any(c.isdigit() for c in content) or content == '-':
                val = clean_num(content)
                if val is not None:
                     current_row.append(val)
    
    # Add last row
    if current_row and len(current_row) >= 5:
        rows.append(current_row)

    # Now write CSV
    # Columns map: 
    # 0: Fecha
    # 1: Base (Ignore)
    # 2: Amortizacion (Previous dump showed Amort then Int then Payment)
    # Let's verify order from previous dump:
    # 1. Date
    # 2. Base
    # 3. Amort (- or 607,49)
    # 4. Interest (129,57 or 207,43)
    # 5. Payment (129,57 or 814,92)
    # 6. Balance
    
    # We need: Fecha, Total_Pago, Intereses, Amortizacion, Saldo_Pendiente
    # Output CSV cols: Fecha, Total_Pago, Intereses, Amortizacion, Saldo_Pendiente
    
    header = ["Fecha", "Total_Pago", "Intereses", "Amortizacion", "Saldo_Pendiente"]
    final_rows = []
    
    for r in rows:
        # r indices: 0=Date, 1=Base, 2=Amort, 3=Int, 4=Payment, 5=Balance
        if len(r) < 6: continue
        
        date = r[0] # DD/MM/YYYY
        amort = r[2]
        interest = r[3]
        payment = r[4]
        balance = r[5]
        
        final_rows.append({
            "Fecha": date,
            "Total_Pago": payment,
            "Intereses": interest,
            "Amortizacion": amort,
            "Saldo_Pendiente": balance
        })
        
    with open('mortgage_schedule.csv', 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for fr in final_rows:
            writer.writerow(fr)
            
    print(f"Extracted {len(final_rows)} rows.")

if __name__ == "__main__":
    parse_pdf_strings()
