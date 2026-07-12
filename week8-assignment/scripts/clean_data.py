import os
import sqlite3
import pandas as pd
import numpy as np

def parse_date(val):
    if pd.isna(val) or str(val).strip() == '':
        return pd.NaT
    val_str = str(val).strip()
    # Try multiple formats
    for fmt in ('%d-%m-%Y', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return pd.to_datetime(val_str, format=fmt)
        except ValueError:
            continue
    # Fallback to general parsing
    try:
        return pd.to_datetime(val_str)
    except:
        return pd.NaT

def clean_orders(df_orders):
    report = {}
    total_raw = len(df_orders)
    
    # 1. Handle NULL/empty customer_id
    null_cust_mask = df_orders['customer_id'].isna() | (df_orders['customer_id'].astype(str).str.strip() == '')
    null_cust_count = null_cust_mask.sum()
    df_clean = df_orders[~null_cust_mask].copy()
    
    # 2. Fix date formats
    raw_dates = df_clean['order_date'].copy()
    parsed_dates = df_clean['order_date'].apply(parse_date)
    df_clean['order_date'] = parsed_dates
    
    # Track how many dates were modified from non-standard format
    # Simple check: if date string contains '-' and it's 10 chars (e.g. DD-MM-YYYY)
    date_format_issues = raw_dates.astype(str).str.match(r'^\d{2}-\d{2}-\d{4}$')
    format_issues_count = date_format_issues.sum()
    
    # 3. Handle future dates
    now = pd.Timestamp.now()
    future_date_mask = df_clean['order_date'] > now
    future_date_count = future_date_mask.sum()
    df_clean = df_clean[~future_date_mask & df_clean['order_date'].notna()]
    
    report['null_customer_ids_dropped'] = int(null_cust_count)
    report['wrong_date_formats_fixed'] = int(format_issues_count)
    report['future_dates_dropped'] = int(future_date_count)
    report['total_orders_cleaned'] = len(df_clean)
    
    return df_clean, report

def clean_products(df_products):
    report = {}
    total_raw = len(df_products)
    
    df_clean = df_products.copy()
    # Normalize product names: trim spaces, title case
    # Keep track of how many names were changed
    original_names = df_clean['product_name'].astype(str)
    df_clean['product_name'] = df_clean['product_name'].astype(str).str.strip().str.title()
    changed_count = (original_names != df_clean['product_name']).sum()
    
    report['names_normalized'] = int(changed_count)
    report['total_products_cleaned'] = len(df_clean)
    
    return df_clean, report

def validate_emails(df_customers):
    # Regex to check email validity (basic check for user@domain.extension)
    email_pattern = r'^[^@]+@[^@]+\.[^@]+$'
    invalid_mask = ~df_customers['email'].astype(str).str.match(email_pattern, na=False)
    invalid_cust_ids = df_customers[invalid_mask]['customer_id'].tolist()
    return invalid_cust_ids

def check_referential_integrity(df_orders, df_order_items):
    # Find order_items referencing non-existent orders
    orphan_mask = ~df_order_items['order_id'].isin(df_orders['order_id'])
    orphan_item_ids = df_order_items[orphan_mask]['item_id'].tolist()
    return orphan_item_ids

def clean_datasets():
    print("=" * 60)
    print("STARTING E-COMMERCE ORDER ANALYTICS ETL PIPELINE")
    print("=" * 60)
    
    # Load raw CSVs
    raw_path = 'data/raw'
    df_customers = pd.read_csv(os.path.join(raw_path, 'customers.csv'))
    df_products = pd.read_csv(os.path.join(raw_path, 'products.csv'))
    df_orders = pd.read_csv(os.path.join(raw_path, 'orders.csv'))
    df_order_items = pd.read_csv(os.path.join(raw_path, 'order_items.csv'))
    
    # 1. Clean Products
    print("Cleaning Products...")
    df_products_clean, prod_report = clean_products(df_products)
    
    # 2. Clean Customers
    print("Cleaning Customers...")
    df_customers_clean = df_customers.copy()
    # Find invalid emails before cleaning them, if any
    invalid_emails = validate_emails(df_customers_clean)
    
    # Normalize registration dates
    df_customers_clean['registration_date'] = pd.to_datetime(df_customers_clean['registration_date'], errors='coerce')
    df_customers_clean = df_customers_clean[df_customers_clean['registration_date'].notna()]
    df_customers_clean['registration_date'] = df_customers_clean['registration_date'].dt.strftime('%Y-%m-%d')
    
    # 3. Clean Orders
    print("Cleaning Orders...")
    df_orders_clean, orders_report = clean_orders(df_orders)
    
    # Ensure customer_id exists in customers (Referential Integrity for Orders)
    missing_cust_orders_mask = ~df_orders_clean['customer_id'].isin(df_customers_clean['customer_id'])
    missing_cust_orders_count = missing_cust_orders_mask.sum()
    df_orders_clean = df_orders_clean[~missing_cust_orders_mask]
    
    # Format order_date as string
    df_orders_clean['order_date'] = df_orders_clean['order_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # 4. Clean Order Items
    print("Cleaning Order Items...")
    df_order_items_clean = df_order_items.copy()
    
    # Check referential integrity (orphaned items)
    orphaned_items = check_referential_integrity(df_orders_clean, df_order_items_clean)
    
    # Drop items that fail referential integrity (orders and products)
    df_order_items_clean = df_order_items_clean[df_order_items_clean['order_id'].isin(df_orders_clean['order_id'])]
    df_order_items_clean = df_order_items_clean[df_order_items_clean['product_id'].isin(df_products_clean['product_id'])]
    
    # Handle zero quantity
    zero_qty_mask = df_order_items_clean['quantity'] == 0
    zero_qty_count = zero_qty_mask.sum()
    df_order_items_clean = df_order_items_clean[~zero_qty_mask]
    
    # Handle invalid discounts (cap or reset to 0)
    invalid_discount_mask = (df_order_items_clean['discount_percent'] < 0) | (df_order_items_clean['discount_percent'] > 100)
    invalid_discount_count = invalid_discount_mask.sum()
    df_order_items_clean.loc[invalid_discount_mask, 'discount_percent'] = 0.0
    
    # Save Cleaned CSVs
    clean_path = 'data/cleaned'
    os.makedirs(clean_path, exist_ok=True)
    
    df_customers_clean.to_csv(os.path.join(clean_path, 'customers_clean.csv'), index=False)
    df_products_clean.to_csv(os.path.join(clean_path, 'products_clean.csv'), index=False)
    df_orders_clean.to_csv(os.path.join(clean_path, 'orders_clean.csv'), index=False)
    df_order_items_clean.to_csv(os.path.join(clean_path, 'order_items_clean.csv'), index=False)
    
    # Print Detailed Execution Report
    print("\n" + "=" * 60)
    print("DATA PIPELINE ANOMALIES & CLEANING REPORT")
    print("=" * 60)
    print(f"Products normalization:")
    print(f"  - Names formatted/trimmed: {prod_report['names_normalized']}")
    print(f"  - Total products output:   {prod_report['total_products_cleaned']}")
    print(f"Customers email validation:")
    print(f"  - Customers with invalid emails: {len(invalid_emails)} (IDs: {invalid_emails})")
    print(f"Orders cleaning:")
    print(f"  - Null customer ID orders dropped: {orders_report['null_customer_ids_dropped']}")
    print(f"  - Wrong date formats corrected:    {orders_report['wrong_date_formats_fixed']}")
    print(f"  - Future date orders dropped:      {orders_report['future_dates_dropped']}")
    print(f"  - Orders with missing customer FK dropped: {missing_cust_orders_count}")
    print(f"  - Total orders output:             {orders_report['total_orders_cleaned'] - missing_cust_orders_count}")
    print(f"Order Items referential integrity:")
    print(f"  - Orphaned items (no order ID): {len(orphaned_items)} (dropped)")
    print(f"  - Zero quantity items dropped:  {zero_qty_count}")
    print(f"  - Invalid discounts reset to 0: {invalid_discount_count}")
    print(f"  - Total items output:           {len(df_order_items_clean)}")
    print("=" * 60)
    
    # 5. Load into SQLite database
    db_path = 'freshmart.db'
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Read and run schema DDL
    with open('sql/schema.sql', 'r') as f:
        schema_sql = f.read()
    cursor.executescript(schema_sql)
    conn.commit()
    
    # Load dataframes into sqlite tables
    # Note: SQLite check constraints and FK constraints will be validated on insert
    df_customers_clean.to_sql('customers', conn, if_exists='append', index=False)
    df_products_clean.to_sql('products', conn, if_exists='append', index=False)
    df_orders_clean.to_sql('orders', conn, if_exists='append', index=False)
    df_order_items_clean.to_sql('order_items', conn, if_exists='append', index=False)
    
    print("\nLoading cleaned data into SQLite database complete.")
    
    # Verification in SQL
    print("\nDatabase Table Verification:")
    for tbl in ['customers', 'products', 'orders', 'order_items']:
        cursor.execute(f"SELECT COUNT(*) FROM {tbl}")
        cnt = cursor.fetchone()[0]
        print(f"  - Table '{tbl}' has {cnt} rows.")
        
    cursor.execute("PRAGMA foreign_key_check")
    violations = cursor.fetchall()
    if violations:
        print("WARNING: Foreign key violations detected in database!")
        for v in violations:
            print(f"  Violation: {v}")
    else:
        print("Foreign key check passed! Referential integrity is fully intact.")
        
    conn.close()

if __name__ == '__main__':
    clean_datasets()
