-- Cohort Analysis, Retention, Churn & RFM Segmentation

-- 1. Cohort Analysis and Retention Rate (by first purchase month)
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
    cr.retained_customers,
    ROUND((cr.retained_customers * 100.0) / cs.cohort_size, 2) AS retention_rate_pct
FROM cohort_retention cr
JOIN cohort_sizes cs ON cr.cohort_month = cs.cohort_month
ORDER BY cr.cohort_month, cr.month_number;

-- 2. Identify Repeat vs One-time Customers and Active vs Churned
-- We define Churned as: last purchase was > 30 days from the maximum order date in the dataset
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
        c.name,
        COALESCE(s.total_orders, 0) AS total_orders,
        s.last_order_date,
        CASE 
            WHEN COALESCE(s.total_orders, 0) >= 2 THEN 'Repeat'
            WHEN COALESCE(s.total_orders, 0) = 1 THEN 'One-time'
            ELSE 'No-purchase'
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
    purchase_frequency,
    activity_status,
    COUNT(*) AS customer_count,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM customers), 2) AS percentage
FROM customer_activity
GROUP BY purchase_frequency, activity_status
ORDER BY customer_count DESC;

-- 3. RFM Analysis (Recency, Frequency, Monetary)
-- Scores from 1 to 3 (3 = Best, 1 = Worst)
WITH customer_rfm_raw AS (
    SELECT 
        customer_id,
        -- Days since last order compared to the latest order in database
        CAST(julianday((SELECT MAX(order_date) FROM orders WHERE status != 'cancelled')) - julianday(MAX(order_date)) AS INTEGER) AS recency,
        COUNT(order_id) AS frequency,
        SUM(order_total) AS monetary
    FROM orders
    WHERE status != 'cancelled'
    GROUP BY customer_id
),
rfm_tiles AS (
    SELECT 
        customer_id,
        recency,
        frequency,
        monetary,
        -- Recency: lower is better (ordered recently) -> order by recency desc for tiles (1 is highest days, 3 is lowest days)
        NTILE(3) OVER (ORDER BY recency DESC) AS r_score,
        -- Frequency: higher is better -> order by frequency asc (1 is lowest frequency, 3 is highest)
        NTILE(3) OVER (ORDER BY frequency ASC) AS f_score,
        -- Monetary: higher is better -> order by monetary asc (1 is lowest spend, 3 is highest)
        NTILE(3) OVER (ORDER BY monetary ASC) AS m_score
    FROM customer_rfm_raw
)
SELECT 
    r.customer_id,
    c.name AS customer_name,
    r.recency AS recency_days,
    r.frequency AS order_count,
    ROUND(r.monetary, 2) AS total_spend,
    (r.r_score || r.f_score || r.m_score) AS rfm_cell,
    CASE 
        WHEN r.r_score = 3 AND r.f_score = 3 AND r.m_score = 3 THEN 'Best Customers'
        WHEN r.f_score = 3 THEN 'Loyal Customers'
        WHEN r.m_score = 3 THEN 'Big Spenders'
        WHEN r.r_score = 1 AND r.f_score = 1 THEN 'Lost Customers'
        ELSE 'Normal Customers'
    END AS rfm_segment
FROM rfm_tiles r
JOIN customers c ON r.customer_id = c.customer_id
ORDER BY total_spend DESC
LIMIT 20;
