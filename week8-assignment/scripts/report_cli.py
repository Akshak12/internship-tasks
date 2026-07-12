import os
import sqlite3
import argparse
import sys
from tabulate import tabulate

def get_db_connection():
    db_path = 'freshmart.db'
    if not os.path.exists(db_path):
        print(f"Error: Database file '{db_path}' not found.", file=sys.stderr)
        print("Please run 'python scripts/clean_data.py' first to populate the database.", file=sys.stderr)
        sys.exit(1)
    try:
        conn = sqlite3.connect(db_path)
        # Enable foreign key support
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        sys.exit(1)

def run_query(conn, query, params=None):
    if params is None:
        params = []
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        rows = cursor.fetchall()
        return columns, rows
    except sqlite3.Error as e:
        print(f"Database query error: {e}", file=sys.stderr)
        return [], []

def report_revenue(conn, plot=False):
    print("\n" + "="*50)
    print("FRESHMART MONTHLY REVENUE & MOM GROWTH REPORT")
    print("="*50)
    
    query = """
    WITH monthly_revenue AS (
        SELECT 
            strftime('%Y-%m', order_date) AS sales_month,
            SUM(order_total) AS current_month_rev,
            COUNT(order_id) AS total_orders,
            AVG(order_total) AS avg_order_val
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY sales_month
    ),
    monthly_lag AS (
        SELECT 
            sales_month,
            ROUND(current_month_rev, 2) AS monthly_revenue,
            total_orders,
            ROUND(avg_order_val, 2) AS average_order_value,
            ROUND(LAG(current_month_rev, 1) OVER (ORDER BY sales_month), 2) AS previous_month_revenue
        FROM monthly_revenue
    )
    SELECT 
        sales_month AS "Month",
        monthly_revenue AS "Revenue (INR)",
        total_orders AS "Completed Orders",
        average_order_value AS "AOV (INR)",
        COALESCE(previous_month_revenue, 0.0) AS "Prev Month Rev",
        CASE 
            WHEN previous_month_revenue IS NULL OR previous_month_revenue = 0 THEN '0.00%'
            ELSE ROUND(((monthly_revenue - previous_month_revenue) / previous_month_revenue) * 100.0, 2) || '%'
        END AS "MoM Growth"
    FROM monthly_lag
    ORDER BY sales_month;
    """
    cols, rows = run_query(conn, query)
    
    if not rows:
        print("No revenue data found.")
    else:
        print(tabulate(rows, headers=cols, tablefmt='grid'))
        
    # Query 2: Daily sales running totals for last 15 days
    print("\nDaily Sales Running Totals (Last 15 Days):")
    daily_query = """
    WITH daily_sales AS (
        SELECT 
            date(order_date) AS order_day,
            SUM(order_total) AS daily_revenue
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY order_day
    )
    SELECT 
        order_day AS "Day",
        ROUND(daily_revenue, 2) AS "Daily Revenue",
        ROUND(SUM(daily_revenue) OVER (ORDER BY order_day), 2) AS "Running Total",
        ROUND(AVG(daily_revenue) OVER (ORDER BY order_day ROWS BETWEEN 6 PRECEDING AND CURRENT ROW), 2) AS "7-Day Moving Avg"
    FROM daily_sales
    ORDER BY order_day DESC
    LIMIT 15;
    """
    cols_daily, rows_daily = run_query(conn, daily_query)
    if rows_daily:
        print(tabulate(rows_daily, headers=cols_daily, tablefmt='simple'))

    if plot:
        generate_revenue_plots(conn)

def report_top_products(conn, plot=False):
    print("\n" + "="*50)
    print("FRESHMART TOP PRODUCTS BY QUANTITY & REVENUE")
    print("="*50)
    
    query = """
    SELECT 
        product_id AS "Product ID",
        product_name AS "Product Name",
        category AS "Category",
        SUM(qty) AS "Total Qty Sold",
        ROUND(SUM(net_price), 2) AS "Total Revenue (INR)"
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status != 'cancelled'
    GROUP BY product_id, product_name, category
    ORDER BY "Total Revenue (INR)" DESC, "Total Qty Sold" DESC
    LIMIT 15;
    """
    cols, rows = run_query(conn, query)
    
    if not rows:
        print("No product data found.")
    else:
        print(tabulate(rows, headers=cols, tablefmt='grid'))
        
    if plot:
        generate_product_plots(conn)

def report_retention(conn, plot=False):
    print("\n" + "="*50)
    print("COHORT MONTHLY RETENTION ANALYSIS")
    print("="*50)
    
    query = """
    WITH customer_first_purchase AS (
        SELECT 
            customer_id,
            strftime('%Y-%m', MIN(order_date)) AS cohort_month
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY customer_id
    ),
    customer_purchase_months AS (
        SELECT DISTINCT
            o.customer_id,
            strftime('%Y-%m', o.order_date) AS purchase_month
        FROM orders o
        WHERE o.status != 'cancelled'
    ),
    cohort_sizes AS (
        SELECT 
            cohort_month,
            COUNT(DISTINCT customer_id) AS cohort_size
        FROM customer_first_purchase
        GROUP BY cohort_month
    ),
    cohort_retention AS (
        SELECT 
            f.cohort_month,
            p.purchase_month,
            (strftime('%Y', p.purchase_month || '-01') - strftime('%Y', f.cohort_month || '-01')) * 12 + 
            (strftime('%m', p.purchase_month || '-01') - strftime('%m', f.cohort_month || '-01')) AS month_number,
            COUNT(DISTINCT f.customer_id) AS retained_customers
        FROM customer_first_purchase f
        JOIN customer_purchase_months p ON f.customer_id = p.customer_id
        GROUP BY f.cohort_month, p.purchase_month
    )
    SELECT 
        cr.cohort_month AS "Cohort Month",
        cs.cohort_size AS "Cohort Size",
        cr.month_number AS "Month N",
        cr.retained_customers AS "Retained Cust",
        ROUND((cr.retained_customers * 100.0) / cs.cohort_size, 2) || '%' AS "Retention Rate"
    FROM cohort_retention cr
    JOIN cohort_sizes cs ON cr.cohort_month = cs.cohort_month
    ORDER BY cr.cohort_month, cr.month_number;
    """
    cols, rows = run_query(conn, query)
    
    if not rows:
        print("No cohort data found.")
    else:
        print(tabulate(rows, headers=cols, tablefmt='grid'))
        
    if plot:
        generate_retention_plots(conn)

def report_customers(conn, plot=False):
    print("\n" + "="*50)
    print("CUSTOMER SEGMENTATION & RFM SUMMARY")
    print("="*50)
    
    # 1. Ranks customers by LTV
    print("\nTop 10 Customers by Lifetime Value (LTV):")
    ltv_query = """
    WITH customer_ltv AS (
        SELECT 
            c.customer_id,
            c.name AS customer_name,
            c.city,
            ROUND(SUM(o.order_total), 2) AS lifetime_value,
            COUNT(o.order_id) AS order_count
        FROM customers c
        JOIN orders o ON c.customer_id = o.customer_id
        WHERE o.status != 'cancelled'
        GROUP BY c.customer_id, c.name, c.city
    )
    SELECT 
        customer_id AS "Cust ID",
        customer_name AS "Name",
        city AS "City",
        order_count AS "Orders Count",
        lifetime_value AS "LTV (INR)",
        DENSE_RANK() OVER (ORDER BY lifetime_value DESC) AS "Rank"
    FROM customer_ltv
    ORDER BY lifetime_value DESC
    LIMIT 10;
    """
    cols_ltv, rows_ltv = run_query(conn, ltv_query)
    if rows_ltv:
        print(tabulate(rows_ltv, headers=cols_ltv, tablefmt='grid'))
        
    # 2. Activity status counts
    print("\nCustomer Activity & Repeat Purchase Status:")
    activity_query = """
    WITH customer_orders_summary AS (
        SELECT 
            customer_id,
            COUNT(order_id) AS total_orders,
            MAX(order_date) AS last_order_date
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY customer_id
    ),
    customer_activity AS (
        SELECT 
            c.customer_id,
            CASE 
                WHEN COALESCE(s.total_orders, 0) >= 2 THEN 'Repeat Customer'
                WHEN COALESCE(s.total_orders, 0) = 1 THEN 'One-time Customer'
                ELSE 'No Purchase'
            END AS purchase_frequency,
            CASE 
                WHEN s.last_order_date IS NULL THEN 'Inactive'
                WHEN CAST(julianday((SELECT MAX(order_date) FROM orders)) - julianday(s.last_order_date) AS INTEGER) > 30 THEN 'Churned'
                ELSE 'Active'
            END AS activity_status
        FROM customers c
        LEFT JOIN customer_orders_summary s ON c.customer_id = s.customer_id
    )
    SELECT 
        purchase_frequency AS "Purchase Frequency",
        activity_status AS "Activity Status",
        COUNT(*) AS "Customer Count",
        ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customers), 2) || '%' AS "Percentage"
    FROM customer_activity
    GROUP BY purchase_frequency, activity_status
    ORDER BY "Customer Count" DESC;
    """
    cols_act, rows_act = run_query(conn, activity_query)
    if rows_act:
        print(tabulate(rows_act, headers=cols_act, tablefmt='simple'))

    if plot:
        generate_customer_plots(conn)


# --- Plot Generation Helpers ---

def generate_revenue_plots(conn):
    import matplotlib.pyplot as plt
    print("Generating revenue plots...")
    
    # 1. Monthly revenue by city
    query = """
    SELECT 
        strftime('%Y-%m', order_date) as sales_month,
        city,
        SUM(order_total) as monthly_revenue
    FROM orders
    WHERE status != 'cancelled'
    GROUP BY sales_month, city
    ORDER BY sales_month, city;
    """
    _, rows = run_query(conn, query)
    if not rows:
        return
        
    data = {}
    months = sorted(list(set(r[0] for r in rows)))
    for r in rows:
        month, city, rev = r
        if city not in data:
            data[city] = [0] * len(months)
        idx = months.index(month)
        data[city][idx] = rev
        
    plt.figure(figsize=(10, 6))
    bottom = [0] * len(months)
    for city, revs in data.items():
        plt.bar(months, revs, bottom=bottom, label=city)
        bottom = [bottom[i] + revs[i] for i in range(len(months))]
        
    plt.title('Monthly Revenue Breakdown by City')
    plt.xlabel('Month')
    plt.ylabel('Revenue (INR)')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    os.makedirs('output/sample_reports', exist_ok=True)
    plt.savefig('output/sample_reports/monthly_revenue_city.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # 2. Daily revenue running totals
    query_daily = """
    WITH daily_sales AS (
        SELECT 
            date(order_date) AS order_day,
            SUM(order_total) AS daily_revenue
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY order_day
    )
    SELECT 
        order_day,
        daily_revenue,
        SUM(daily_revenue) OVER (ORDER BY order_day) AS running_total
    FROM daily_sales
    ORDER BY order_day;
    """
    _, rows_daily = run_query(conn, query_daily)
    if rows_daily:
        days = [r[0] for r in rows_daily]
        daily_rev = [r[1] for r in rows_daily]
        running_tot = [r[2] for r in rows_daily]
        
        fig, ax1 = plt.subplots(figsize=(12, 6))
        
        color = 'tab:blue'
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Daily Revenue (INR)', color=color)
        ax1.bar(days, daily_rev, color=color, alpha=0.5, label='Daily Revenue')
        ax1.tick_params(axis='y', labelcolor=color)
        plt.xticks(rotation=45)
        
        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Running Total (INR)', color=color)
        ax2.plot(days, running_tot, color=color, linewidth=2.5, label='Running Total')
        ax2.tick_params(axis='y', labelcolor=color)
        
        plt.title('Daily Revenue & Cumulative Running Total')
        fig.tight_layout()
        plt.savefig('output/sample_reports/daily_revenue_trend.png', dpi=300, bbox_inches='tight')
        plt.close()
        
    print("Revenue plots saved successfully to 'output/sample_reports/'.")

def generate_product_plots(conn):
    import matplotlib.pyplot as plt
    print("Generating product plots...")
    
    query = """
    SELECT 
        product_name,
        SUM(qty) as total_qty,
        SUM(net_price) as total_revenue
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status != 'cancelled'
    GROUP BY product_name
    ORDER BY total_revenue DESC
    LIMIT 10;
    """
    _, rows = run_query(conn, query)
    if not rows:
        return
        
    products = [r[0] for r in rows][::-1] # Reverse for horizontal bar chart
    revenue = [r[2] for r in rows][::-1]
    
    plt.figure(figsize=(10, 6))
    plt.barh(products, revenue, color='teal')
    plt.title('Top 10 Products by Revenue')
    plt.xlabel('Revenue (INR)')
    plt.ylabel('Product Name')
    plt.grid(axis='x', linestyle='--', alpha=0.7)
    
    plt.savefig('output/sample_reports/top_products_revenue.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Product plots saved successfully to 'output/sample_reports/'.")

def generate_retention_plots(conn):
    import matplotlib.pyplot as plt
    import numpy as np
    print("Generating retention heatmap...")
    
    # We will build a cohort retention grid from the cohort data
    query = """
    WITH customer_first_purchase AS (
        SELECT 
            customer_id,
            strftime('%Y-%m', MIN(order_date)) AS cohort_month
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY customer_id
    ),
    customer_purchase_months AS (
        SELECT DISTINCT
            o.customer_id,
            strftime('%Y-%m', o.order_date) AS purchase_month
        FROM orders o
        WHERE o.status != 'cancelled'
    ),
    cohort_sizes AS (
        SELECT 
            cohort_month,
            COUNT(DISTINCT customer_id) AS cohort_size
        FROM customer_first_purchase
        GROUP BY cohort_month
    ),
    cohort_retention AS (
        SELECT 
            f.cohort_month,
            p.purchase_month,
            (strftime('%Y', p.purchase_month || '-01') - strftime('%Y', f.cohort_month || '-01')) * 12 + 
            (strftime('%m', p.purchase_month || '-01') - strftime('%m', f.cohort_month || '-01')) AS month_number,
            COUNT(DISTINCT f.customer_id) AS retained_customers
        FROM customer_first_purchase f
        JOIN customer_purchase_months p ON f.customer_id = p.customer_id
        GROUP BY f.cohort_month, p.purchase_month
    )
    SELECT 
        cr.cohort_month,
        cs.cohort_size,
        cr.month_number,
        ROUND((cr.retained_customers * 100.0) / cs.cohort_size, 2) AS retention_rate
    FROM cohort_retention cr
    JOIN cohort_sizes cs ON cr.cohort_month = cs.cohort_month
    ORDER BY cr.cohort_month, cr.month_number;
    """
    _, rows = run_query(conn, query)
    if not rows:
        return
        
    cohorts = sorted(list(set(r[0] for r in rows)))
    max_months = max(r[2] for r in rows) + 1
    
    # Create retention matrix
    retention_matrix = np.full((len(cohorts), max_months), np.nan)
    cohort_sizes_arr = []
    
    for r in rows:
        cohort_month, size, month_num, rate = r
        cohort_idx = cohorts.index(cohort_month)
        retention_matrix[cohort_idx, month_num] = rate
        if cohort_idx >= len(cohort_sizes_arr):
            cohort_sizes_arr.append(size)
            
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(retention_matrix, cmap='Blues', vmin=0, vmax=100)
    
    # Grid labels
    ax.set_xticks(np.arange(max_months))
    ax.set_yticks(np.arange(len(cohorts)))
    
    # Format labels
    ax.set_xticklabels([f"Month {i}" for i in range(max_months)])
    ax.set_yticklabels([f"{c} ({cohort_sizes_arr[idx]})" for idx, c in enumerate(cohorts)])
    
    ax.set_title('Cohort Retention Matrix (%)')
    ax.set_xlabel('Months Since First Purchase')
    ax.set_ylabel('Cohort Month (Size)')
    
    # Add numbers inside heatmap
    for i in range(len(cohorts)):
        for j in range(max_months):
            val = retention_matrix[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.1f}%", ha="center", va="center", 
                        color="white" if val > 50 else "black", fontweight='bold')
                        
    plt.colorbar(im, ax=ax, label='Retention %')
    plt.tight_layout()
    plt.savefig('output/sample_reports/cohort_retention_heatmap.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Cohort heatmap saved successfully to 'output/sample_reports/'.")

def generate_customer_plots(conn):
    import matplotlib.pyplot as plt
    print("Generating customer segment plots...")
    
    query = """
    WITH customer_orders_summary AS (
        SELECT 
            customer_id,
            COUNT(order_id) AS total_orders,
            MAX(order_date) AS last_order_date
        FROM orders
        WHERE status != 'cancelled'
        GROUP BY customer_id
    ),
    customer_activity AS (
        SELECT 
            c.customer_id,
            CASE 
                WHEN COALESCE(s.total_orders, 0) >= 2 THEN 'Repeat Customer'
                WHEN COALESCE(s.total_orders, 0) = 1 THEN 'One-time Customer'
                ELSE 'No Purchase'
            END AS purchase_frequency
        FROM customers c
        LEFT JOIN customer_orders_summary s ON c.customer_id = s.customer_id
    )
    SELECT purchase_frequency, COUNT(*) 
    FROM customer_activity
    GROUP BY purchase_frequency;
    """
    _, rows = run_query(conn, query)
    if not rows:
        return
        
    labels = [r[0] for r in rows]
    counts = [r[1] for r in rows]
    
    plt.figure(figsize=(8, 8))
    plt.pie(counts, labels=labels, autopct='%1.1f%%', colors=['#ff9999','#66b3ff','#99ff99'], startangle=90)
    plt.title('Customer Segments by Purchase Frequency')
    plt.savefig('output/sample_reports/customer_segmentation_pie.png', dpi=300, bbox_inches='tight')
    plt.close()
    print("Customer segment plots saved successfully to 'output/sample_reports/'.")


# --- Main Entry Point ---

def main():
    parser = argparse.ArgumentParser(description="FreshMart Retail Analytics Command-Line Reporting Tool")
    parser.add_argument(
        '--report', 
        choices=['revenue', 'top_products', 'retention', 'customers'],
        required=True,
        help="Specify the business report to generate"
    )
    parser.add_argument(
        '--plot',
        action='store_true',
        help="Generate and save visualization plots (charts) as PNGs"
    )
    
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    if args.report == 'revenue':
        report_revenue(conn, args.plot)
    elif args.report == 'top_products':
        report_top_products(conn, args.plot)
    elif args.report == 'retention':
        report_retention(conn, args.plot)
    elif args.report == 'customers':
        report_customers(conn, args.plot)
        
    conn.close()

if __name__ == '__main__':
    main()
