import os
import sys
import sqlite3
import argparse
from datetime import datetime, timedelta

def get_db_connection():
    db_path = 'freshmart.db'
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.", file=sys.stderr)
        print("Please run 'python scripts/clean_data.py' first.", file=sys.stderr)
        sys.exit(1)
    try:
        conn = sqlite3.connect(db_path)
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

def print_table(headers, rows):
    if not rows:
        print("No data available for this section.")
        return
    # Convert all cells to strings
    str_rows = [[str(cell) for cell in row] for row in rows]
    # Calculate column widths
    col_widths = []
    for i in range(len(headers)):
        max_len = len(headers[i])
        for row in str_rows:
            if i < len(row):
                max_len = max(max_len, len(row[i]))
        col_widths.append(max_len)
    
    # Render table elements
    border = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    header_row = "|" + "|".join(f" {headers[i]:<{col_widths[i]}} " for i in range(len(headers))) + "|"
    
    print(border)
    print(header_row)
    print(border)
    for row in str_rows:
        row_str = "|" + "|".join(f" {row[i]:<{col_widths[i]}} " for i in range(len(headers))) + "|"
        print(row_str)
    print(border)

def get_metrics_for_period(conn, start_str, end_str):
    # Ensure times are included for dates to cover the entire day
    start_dt = start_str + " 00:00:00"
    end_dt = end_str + " 23:59:59"
    
    cursor = conn.cursor()
    
    # 1. Total Orders
    cursor.execute("SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_date BETWEEN ? AND ?", (start_dt, end_dt))
    total_orders = cursor.fetchone()[0] or 0
    
    # 2. Total Revenue (includes returns/negative quantities)
    cursor.execute("""
        SELECT SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0))
        FROM order_items oi
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.order_date BETWEEN ? AND ? AND o.status != 'CANCELLED'
    """, (start_dt, end_dt))
    revenue = cursor.fetchone()[0]
    revenue = round(revenue, 2) if revenue is not None else 0.0
    
    # 3. Unique Customers
    cursor.execute("SELECT COUNT(DISTINCT customer_id) FROM orders WHERE order_date BETWEEN ? AND ?", (start_dt, end_dt))
    unique_customers = cursor.fetchone()[0] or 0
    
    return total_orders, revenue, unique_customers

def get_top_products(conn, start_str, end_str):
    start_dt = start_str + " 00:00:00"
    end_dt = end_str + " 23:59:59"
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            p.product_name,
            SUM(oi.quantity) as total_qty,
            ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)), 2) as total_revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        JOIN orders o ON oi.order_id = o.order_id
        WHERE o.order_date BETWEEN ? AND ? AND o.status != 'CANCELLED'
        GROUP BY p.product_id, p.product_name
        ORDER BY total_revenue DESC
        LIMIT 3
    """, (start_dt, end_dt))
    return cursor.fetchall()

def get_breakdown(conn, report_type, start_str, end_str):
    start_dt = start_str + " 00:00:00"
    end_dt = end_str + " 23:59:59"
    cursor = conn.cursor()
    
    if report_type == 'daily':
        group_format = "DATE(o.order_date)"
    elif report_type == 'weekly':
        group_format = "STRFTIME('%Y-W%W', o.order_date)"
    else: # monthly
        group_format = "STRFTIME('%Y-%m', o.order_date)"
        
    query = f"""
        SELECT 
            {group_format} AS period_key,
            COUNT(DISTINCT o.order_id) AS total_orders,
            ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent/100.0)), 2) AS revenue,
            COUNT(DISTINCT o.customer_id) AS unique_customers
        FROM orders o
        JOIN order_items oi ON o.order_id = oi.order_id
        WHERE o.order_date BETWEEN ? AND ? AND o.status != 'CANCELLED'
        GROUP BY period_key
        ORDER BY period_key ASC
    """
    cursor.execute(query, (start_dt, end_dt))
    return cursor.fetchall()

def calculate_pct_change(current, previous):
    if previous == 0:
        return "+100.00%" if current > 0 else "0.00%"
    change = ((current - previous) / previous) * 100.0
    prefix = "+" if change > 0 else ""
    return f"{prefix}{change:.2f}%"

def validate_date(date_text):
    try:
        datetime.strptime(date_text, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def get_interactive_inputs():
    print("\n--- E-Commerce Analytics CLI Report Generator ---")
    
    # 1. Report Type
    while True:
        report_type = input("Enter report type (daily/weekly/monthly): ").strip().lower()
        if report_type in ['daily', 'weekly', 'monthly']:
            break
        print("Invalid type. Please enter 'daily', 'weekly', or 'monthly'.")
        
    # 2. Start Date
    while True:
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        if validate_date(start_date):
            break
        print("Invalid date format. Use YYYY-MM-DD.")
        
    # 3. End Date
    while True:
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()
        if validate_date(end_date):
            # Check if start <= end
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            if start_dt <= end_dt:
                break
            else:
                print("End date must be on or after start date.")
        else:
            print("Invalid date format. Use YYYY-MM-DD.")
            
    return report_type, start_date, end_date

def main():
    parser = argparse.ArgumentParser(description="E-Commerce Order Analytics Reporting Tool")
    parser.add_argument('--type', choices=['daily', 'weekly', 'monthly'], help="Report type aggregation format")
    parser.add_argument('--start', help="Start date in YYYY-MM-DD format")
    parser.add_argument('--end', help="End date in YYYY-MM-DD format")
    
    args = parser.parse_args()
    
    # If any parameter is missing, fallback to interactive input
    if not (args.type and args.start and args.end):
        report_type, start_date, end_date = get_interactive_inputs()
    else:
        report_type = args.type.lower()
        start_date = args.start
        end_date = args.end
        
        # Validate CLI input dates
        if not (validate_date(start_date) and validate_date(end_date)):
            print("Error: Dates must be in YYYY-MM-DD format.", file=sys.stderr)
            sys.exit(1)
        if datetime.strptime(start_date, '%Y-%m-%d') > datetime.strptime(end_date, '%Y-%m-%d'):
            print("Error: Start date cannot be after end date.", file=sys.stderr)
            sys.exit(1)

    # Establish db connection
    conn = get_db_connection()
    
    # Parse dates to calculate the previous period of same duration
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    duration_days = (end_dt - start_dt).days + 1
    
    prev_start_dt = start_dt - timedelta(days=duration_days)
    prev_end_dt = start_dt - timedelta(days=1)
    
    prev_start_date = prev_start_dt.strftime('%Y-%m-%d')
    prev_end_date = prev_end_dt.strftime('%Y-%m-%d')
    
    # Fetch metrics
    curr_orders, curr_revenue, curr_customers = get_metrics_for_period(conn, start_date, end_date)
    prev_orders, prev_revenue, prev_customers = get_metrics_for_period(conn, prev_start_date, prev_end_date)
    
    # Calculate % changes
    orders_change = calculate_pct_change(curr_orders, prev_orders)
    revenue_change = calculate_pct_change(curr_revenue, prev_revenue)
    customers_change = calculate_pct_change(curr_customers, prev_customers)
    
    # Fetch top products
    top_products = get_top_products(conn, start_date, end_date)
    
    # Fetch breakdown
    breakdown_data = get_breakdown(conn, report_type, start_date, end_date)
    
    # Print the report
    print("\n" + "=" * 65)
    print(f"E-COMMERCE BUSINESS PERFORMANCE REPORT ({report_type.upper()})")
    print(f"Active Period:   {start_date} to {end_date} ({duration_days} days)")
    print(f"Previous Period: {prev_start_date} to {prev_end_date} ({duration_days} days)")
    print("=" * 65)
    
    # 1. Summary Metrics Table
    summary_headers = ["Metric", "Current Period", "Previous Period", "% Change"]
    summary_rows = [
        ["Total Orders", curr_orders, prev_orders, orders_change],
        ["Total Revenue ($)", f"{curr_revenue:.2f}", f"{prev_revenue:.2f}", revenue_change],
        ["Unique Customers", curr_customers, prev_customers, customers_change]
    ]
    print("\nSUMMARY METRICS:")
    print_table(summary_headers, summary_rows)
    
    # 2. Top Products Table
    product_headers = ["Product Name", "Quantity Sold", "Revenue ($)"]
    print("\nTOP 3 PRODUCTS BY REVENUE:")
    print_table(product_headers, top_products)
    
    # 3. Period Breakdown Table
    breakdown_headers = ["Period Key", "Orders Count", "Revenue ($)", "Unique Customers"]
    print(f"\nPERIOD BREAKDOWN ({report_type.upper()}):")
    print_table(breakdown_headers, breakdown_data)
    
    conn.close()

if __name__ == '__main__':
    main()
