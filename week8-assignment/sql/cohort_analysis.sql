-- Advanced SQL Analytics - Cohort, Segmentation & Complex CTEs

-- 10. CTE with Multiple Levels
-- Level 1: Calculate monthly revenue per customer
-- Level 2: Categorize customers: 'High' (>10000), 'Medium' (5000-10000), 'Low' (<5000)
-- Level 3: Show count of customers in each category per month
WITH monthly_customer_revenue AS (
    SELECT 
        o.customer_id,
        STRFTIME('%Y-%m', o.order_date) AS order_month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS monthly_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status != 'CANCELLED'
    GROUP BY o.customer_id, STRFTIME('%Y-%m', o.order_date)
),
customer_categories AS (
    SELECT 
        customer_id,
        order_month,
        monthly_revenue,
        CASE 
            WHEN monthly_revenue > 10000 THEN 'High'
            WHEN monthly_revenue BETWEEN 5000 AND 10000 THEN 'Medium'
            ELSE 'Low'
        END AS category
    FROM monthly_customer_revenue
)
SELECT 
    order_month,
    category,
    COUNT(customer_id) AS customer_count
FROM customer_categories
GROUP BY order_month, category
ORDER BY order_month, category;

-- 11. NTILE for Segmentation
-- Divide customers into 4 quartiles based on total lifetime value (LTV)
-- Shows: customer_id, total_value, quartile, quartile_label (Platinum/Gold/Silver/Bronze)
WITH customer_ltv AS (
    SELECT 
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS total_value
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status != 'CANCELLED'
    GROUP BY o.customer_id
),
customer_tiles AS (
    SELECT 
        customer_id,
        total_value,
        NTILE(4) OVER (ORDER BY total_value DESC) AS quartile
    FROM customer_ltv
)
SELECT 
    customer_id,
    ROUND(total_value, 2) AS total_value,
    quartile,
    CASE 
        WHEN quartile = 1 THEN 'Platinum'
        WHEN quartile = 2 THEN 'Gold'
        WHEN quartile = 3 THEN 'Silver'
        ELSE 'Bronze'
    END AS quartile_label
FROM customer_tiles
ORDER BY total_value DESC;

-- 12. Year-over-Year Comparison
-- Compare each month's revenue with the same month in the previous year
-- Shows: year, month, revenue, prev_year_revenue, yoy_growth_percent
WITH monthly_revenue AS (
    SELECT 
        CAST(STRFTIME('%Y', o.order_date) AS INTEGER) AS sales_year,
        CAST(STRFTIME('%m', o.order_date) AS INTEGER) AS sales_month,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status != 'CANCELLED'
    GROUP BY sales_year, sales_month
)
SELECT 
    m1.sales_year AS year,
    m1.sales_month AS month,
    ROUND(m1.revenue, 2) AS revenue,
    ROUND(m2.revenue, 2) AS prev_year_revenue,
    CASE 
        WHEN m2.revenue IS NULL OR m2.revenue = 0 THEN 'N/A'
        ELSE ROUND(((m1.revenue - m2.revenue) * 100.0) / m2.revenue, 2) || '%'
    END AS yoy_growth_percent
FROM monthly_revenue m1
LEFT JOIN monthly_revenue m2 
    ON m1.sales_year = m2.sales_year + 1 
   AND m1.sales_month = m2.sales_month
ORDER BY year DESC, month DESC;

-- 13. First/Last Value Analysis
-- For each customer, show first purchased category and most recent purchased category
-- Flag if they are different (category_shift = 'Yes'/'No')
WITH customer_items_ordered AS (
    SELECT 
        o.customer_id,
        p.category,
        o.order_date,
        ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date ASC, oi.item_id ASC) AS rn_first,
        ROW_NUMBER() OVER (PARTITION BY o.customer_id ORDER BY o.order_date DESC, oi.item_id DESC) AS rn_last
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    JOIN products p ON oi.product_id = p.product_id
    WHERE o.status != 'CANCELLED'
),
first_categories AS (
    SELECT customer_id, category AS first_category
    FROM customer_items_ordered
    WHERE rn_first = 1
),
last_categories AS (
    SELECT customer_id, category AS last_category
    FROM customer_items_ordered
    WHERE rn_last = 1
)
SELECT 
    f.customer_id,
    f.first_category,
    l.last_category,
    CASE 
        WHEN f.first_category = l.last_category THEN 'No'
        ELSE 'Yes'
    END AS category_shift
FROM first_categories f
JOIN last_categories l ON f.customer_id = l.customer_id;

-- 14. Cumulative Distribution
-- Calculate what percentage of total revenue comes from the top N% of customers
-- Shows: customer_id, revenue, cumulative_revenue, cumulative_percent
WITH customer_revenue AS (
    SELECT 
        o.customer_id,
        SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status != 'CANCELLED'
    GROUP BY o.customer_id
),
total_revenue AS (
    SELECT SUM(revenue) AS grand_total FROM customer_revenue
),
customer_cum_revenue AS (
    SELECT 
        customer_id,
        revenue,
        SUM(revenue) OVER (ORDER BY revenue DESC) AS cumulative_revenue
    FROM customer_revenue
)
SELECT 
    c.customer_id,
    ROUND(c.revenue, 2) AS revenue,
    ROUND(c.cumulative_revenue, 2) AS cumulative_revenue,
    ROUND((c.cumulative_revenue * 100.0) / t.grand_total, 2) || '%' AS cumulative_percent
FROM customer_cum_revenue c
CROSS JOIN total_revenue t
ORDER BY c.revenue DESC;

-- 15. Complex CTE: Cohort Analysis
-- Group customers by registration month (cohort), tracking retention in month 0, 1, 2, 3
WITH customer_cohort AS (
    SELECT 
        customer_id,
        STRFTIME('%Y-%m', registration_date) AS cohort_month
    FROM customers
),
cohort_sizes AS (
    SELECT 
        cohort_month,
        COUNT(customer_id) AS cohort_size
    FROM customer_cohort
    GROUP BY cohort_month
),
customer_orders_months AS (
    SELECT DISTINCT
        o.customer_id,
        STRFTIME('%Y-%m', o.order_date) AS order_month,
        cc.cohort_month,
        (CAST(STRFTIME('%Y', o.order_date) AS INTEGER) - CAST(STRFTIME('%Y', cc.cohort_month || '-01') AS INTEGER)) * 12 +
        (CAST(STRFTIME('%m', o.order_date) AS INTEGER) - CAST(STRFTIME('%m', cc.cohort_month || '-01') AS INTEGER)) AS month_diff
    FROM orders o
    JOIN customer_cohort cc ON o.customer_id = cc.customer_id
    WHERE o.status != 'CANCELLED'
),
cohort_retention AS (
    SELECT 
        cohort_month,
        month_diff,
        COUNT(DISTINCT customer_id) AS retained_customers
    FROM customer_orders_months
    WHERE month_diff >= 0
    GROUP BY cohort_month, month_diff
)
SELECT 
    r.cohort_month,
    s.cohort_size,
    r.month_diff AS month_number,
    r.retained_customers,
    ROUND((r.retained_customers * 100.0) / s.cohort_size, 2) || '%' AS retention_rate
FROM cohort_retention r
JOIN cohort_sizes s ON r.cohort_month = s.cohort_month
WHERE r.month_diff <= 3
ORDER BY r.cohort_month, r.month_diff;

-- 16. Self-Join with Window Function
-- Find products frequently bought together in the same order
-- Shows: product_a, product_b, times_bought_together (A-B and B-A appear once)
SELECT 
    p1.product_name AS product_a,
    p2.product_name AS product_b,
    COUNT(*) AS times_bought_together
FROM order_items oi1
JOIN order_items oi2 
    ON oi1.order_id = oi2.order_id 
   AND oi1.product_id < oi2.product_id -- Excludes duplicates and matches with self
JOIN products p1 ON oi1.product_id = p1.product_id
JOIN products p2 ON oi2.product_id = p2.product_id
GROUP BY p1.product_name, p2.product_name
ORDER BY times_bought_together DESC, product_a, product_b
LIMIT 20;
