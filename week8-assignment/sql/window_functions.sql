-- Advanced SQL Analytics - Window Functions & CTEs

-- 1. Rank customers by lifetime value (LTV) using RANK() and DENSE_RANK()
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
    customer_id,
    customer_name,
    city,
    order_count,
    lifetime_value,
    RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_rank,
    DENSE_RANK() OVER (ORDER BY lifetime_value DESC) AS ltv_dense_rank
FROM customer_ltv
ORDER BY lifetime_value DESC
LIMIT 15;

-- 2. Calculate daily running totals and 7-day moving averages for revenue
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
    ROUND(daily_revenue, 2) AS daily_revenue,
    ROUND(SUM(daily_revenue) OVER (ORDER BY order_day), 2) AS running_total_revenue,
    ROUND(AVG(daily_revenue) OVER (
        ORDER BY order_day 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2) AS seven_day_moving_avg
FROM daily_sales
ORDER BY order_day;

-- 3. Monthly revenue and growth rate comparison using CTEs and LAG()
WITH monthly_revenue AS (
    SELECT 
        strftime('%Y-%m', order_date) AS sales_month,
        SUM(order_total) AS current_month_rev
    FROM orders
    WHERE status != 'cancelled'
    GROUP BY sales_month
),
monthly_lag AS (
    SELECT 
        sales_month,
        ROUND(current_month_rev, 2) AS monthly_revenue,
        ROUND(LAG(current_month_rev, 1) OVER (ORDER BY sales_month), 2) AS previous_month_revenue
    FROM monthly_revenue
)
SELECT 
    sales_month,
    monthly_revenue,
    COALESCE(previous_month_revenue, 0.0) AS previous_month_revenue,
    CASE 
        WHEN previous_month_revenue IS NULL OR previous_month_revenue = 0 THEN 0.0
        ELSE ROUND(((monthly_revenue - previous_month_revenue) / previous_month_revenue) * 100.0, 2)
    END AS MoM_growth_pct
FROM monthly_lag
ORDER BY sales_month;
