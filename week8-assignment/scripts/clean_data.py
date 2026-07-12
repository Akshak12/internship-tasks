import os
import hashlib
import json
import sqlite3
import pandas as pd
import numpy as np

def hash_pii(val):
    if pd.isna(val) or str(val).strip() == '':
        return None
    return hashlib.sha256(str(val).strip().encode('utf-8')).hexdigest()

def clean_datasets():
    print("Starting data cleaning pipeline...")
    
    # 1. Load raw datasets
    df_customers = pd.read_csv('data/raw/customers.csv')
    df_products = pd.read_csv('data/raw/products.csv')
    df_orders = pd.read_csv('data/raw/orders.csv')
    df_order_items = pd.read_csv('data/raw/order_items.csv')

    print(f"Loaded raw row counts:")
    print(f"  Customers: {len(df_customers)}")
    print(f"  Products: {len(df_products)}")
    print(f"  Orders: {len(df_orders)}")
    print(f"  Order Items: {len(df_order_items)}")

    # --- 2. Clean Customers ---
    print("\nCleaning Customers...")
    # Deduplicate on primary key
    df_customers = df_customers.drop_duplicates(subset=['customer_id'], keep='first')
    
    # Mask PII
    df_customers['email'] = df_customers['email'].apply(hash_pii)
    df_customers['phone'] = df_customers['phone'].apply(hash_pii)
    
    # Clean and validate registration dates
    df_customers['registered_on'] = pd.to_datetime(df_customers['registered_on'], errors='coerce')
    # Drop future dates
    current_time = pd.Timestamp.now()
    df_customers = df_customers[df_customers['registered_on'] <= current_time]
    # Drop rows with null registration dates
    df_customers = df_customers.dropna(subset=['registered_on'])
    # Convert date back to string format
    df_customers['registered_on'] = df_customers['registered_on'].dt.strftime('%Y-%m-%d')
    
    # Clean loyalty points: cap negative values to 0, fill nulls with 0
    df_customers['loyalty_points'] = df_customers['loyalty_points'].apply(lambda x: max(0, x) if not pd.isna(x) else 0)
    df_customers['loyalty_points'] = df_customers['loyalty_points'].astype(int)

    # --- 3. Clean Products ---
    print("Cleaning Products...")
    # Deduplicate on primary key
    df_products = df_products.drop_duplicates(subset=['product_id'], keep='first')
    # Filter out products with negative price
    df_products = df_products[df_products['base_price'] >= 0]

    # --- 4. Clean Orders ---
    print("Cleaning Orders...")
    # Deduplicate on primary key
    df_orders = df_orders.drop_duplicates(subset=['order_id'], keep='first')
    
    # Parse dates
    df_orders['order_date'] = pd.to_datetime(df_orders['order_date'], errors='coerce')
    # Drop future or invalid dates
    df_orders = df_orders[(df_orders['order_date'] <= current_time) & (df_orders['order_date'].notna())]
    
    # Validate and clean city
    valid_cities = ['Delhi', 'Mumbai', 'Bengaluru']
    # If city is missing/invalid, try to resolve using customer info
    # To do this, merge with customers
    df_orders = df_orders.merge(df_customers[['customer_id', 'city']], on='customer_id', suffixes=('', '_cust'), how='left')
    df_orders['city'] = df_orders['city'].fillna(df_orders['city_cust'])
    df_orders = df_orders[df_orders['city'].isin(valid_cities)]
    df_orders = df_orders.drop(columns=['city_cust'])

    # Validate customer_id exists in customers (referential integrity)
    df_orders = df_orders[df_orders['customer_id'].isin(df_customers['customer_id'])]
    
    # Convert dates back to string format
    df_orders['order_date'] = df_orders['order_date'].dt.strftime('%Y-%m-%d %H:%M:%S')

    # --- 5. Clean Order Items ---
    print("Cleaning Order Items...")
    # Deduplicate on primary key
    df_order_items = df_order_items.drop_duplicates(subset=['item_id'], keep='first')
    
    # Validate referential integrity (order_id and product_id must exist in cleaned tables)
    df_order_items = df_order_items[df_order_items['order_id'].isin(df_orders['order_id'])]
    df_order_items = df_order_items[df_order_items['product_id'].isin(df_products['product_id'])]
    
    # Filter out negative quantities or prices
    df_order_items = df_order_items[(df_order_items['qty'] > 0) & (df_order_items['unit_price'] >= 0)]
    
    # Clean discount: cap at [0, 100]
    df_order_items['discount'] = df_order_items['discount'].apply(lambda x: x if 0 <= x <= 100 else 0)
    
    # Compute derived column net_price
    df_order_items['net_price'] = df_order_items['qty'] * df_order_items['unit_price'] * (1 - df_order_items['discount'] / 100.0)
    df_order_items['net_price'] = df_order_items['net_price'].round(2)
    
    # Compute discount amount
    df_order_items['discount_amount'] = (df_order_items['qty'] * df_order_items['unit_price'] * (df_order_items['discount'] / 100.0)).round(2)

    # --- 6. Recalculate Order Totals ---
    print("Recalculating Order Totals...")
    order_totals = df_order_items.groupby('order_id').agg(
        order_total=('net_price', 'sum'),
        total_discount=('discount_amount', 'sum')
    ).reset_index()
    
    # Drop temporary discount_amount from order_items
    df_order_items = df_order_items.drop(columns=['discount_amount'])
    
    # Update orders table with calculated totals
    df_orders = df_orders.merge(order_totals, on='order_id', how='left')
    df_orders['order_total'] = df_orders['order_total'].fillna(0.0).round(2)
    df_orders['total_discount'] = df_orders['total_discount'].fillna(0.0).round(2)

    # --- 7. Save Cleaned CSVs ---
    print("\nExporting cleaned datasets to data/cleaned/...")
    os.makedirs('data/cleaned', exist_ok=True)
    
    df_customers.to_csv('data/cleaned/customers_clean.csv', index=False)
    df_products.to_csv('data/cleaned/products_clean.csv', index=False)
    df_orders.to_csv('data/cleaned/orders_clean.csv', index=False)
    df_order_items.to_csv('data/cleaned/order_items_clean.csv', index=False)
    
    print("Cleaned CSV exports complete.")
    print(f"Cleaned row counts:")
    print(f"  Customers: {len(df_customers)}")
    print(f"  Products: {len(df_products)}")
    print(f"  Orders: {len(df_orders)}")
    print(f"  Order Items: {len(df_order_items)}")

    # --- 8. Load into SQLite Database ---
    print("\nLoading cleaned data into SQLite database (freshmart.db)...")
    db_path = 'freshmart.db'
    
    # Remove existing database if it exists to ensure a clean load
    if os.path.exists(db_path):
        os.remove(db_path)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute schema.sql DDL
    with open('sql/schema.sql', 'r') as f:
        schema_ddl = f.read()
    cursor.executescript(schema_ddl)
    conn.commit()
    
    # Load pandas DataFrames into SQLite tables
    df_customers.to_sql('customers', conn, if_exists='append', index=False)
    df_products.to_sql('products', conn, if_exists='append', index=False)
    df_orders.to_sql('orders', conn, if_exists='append', index=False)
    df_order_items.to_sql('order_items', conn, if_exists='append', index=False)
    
    # Verify row counts in SQL
    print("\nVerifying database row counts:")
    tables = ['customers', 'products', 'orders', 'order_items']
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"  Table '{table}' has {count} rows.")
        
    # Verify referential integrity constraints
    cursor.execute("PRAGMA foreign_key_check")
    violations = cursor.fetchall()
    if violations:
        print("WARNING: Foreign key violations detected!")
        for violation in violations:
            print(violation)
    else:
        print("Foreign key check passed! Referential integrity is fully validated.")
        
    conn.close()
    print("Database loading complete. freshmart.db is ready.")

if __name__ == '__main__':
    clean_datasets()
