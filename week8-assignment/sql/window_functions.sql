-- Intermediate & Advanced SQL Analytics - Window Functions & CTEs

-- 4. Find customers who placed orders but never had any item delivered
SELECT 
    c.customer_id, 
    c.customer_name
FROM customers c
WHERE c.customer_id IN (SELECT DISTINCT customer_id FROM orders) -- Placed at least one order
  AND c.customer_id NOT IN (SELECT DISTINCT customer_id FROM orders WHERE status = 'DELIVERED');

-- 5. Products that were ordered but had more returns than purchases
-- Returns are negative quantities, purchases are positive quantities
WITH product_qtys AS (
    SELECT 
        p.product_id, 
        p.product_name,
        SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS total_purchased,
        SUM(CASE WHEN oi.quantity < 0 THEN ABS(oi.quantity) ELSE 0 END) AS total_returned
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    GROUP BY p.product_id, p.product_name
)
SELECT 
    product_id, 
    product_name, 
    total_purchased, 
    total_returned
FROM product_qtys
WHERE total_returned > total_purchased;

-- 6. Calculate the return rate (returned items / total items) per category
SELECT 
    p.category,
    SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END) AS total_purchased,
    SUM(CASE WHEN oi.quantity < 0 THEN ABS(oi.quantity) ELSE 0 END) AS total_returned,
    ROUND(
        SUM(CASE WHEN oi.quantity < 0 THEN ABS(oi.quantity) ELSE 0 END) * 100.0 / 
        NULLIF(SUM(CASE WHEN oi.quantity > 0 THEN oi.quantity ELSE 0 END), 0), 
        2
    ) || '%' AS return_rate
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.category;

-- 7. Running Totals with Window Functions: Calculate running total of revenue per region, ordered by date
-- Shows: region_code, order_date, daily_revenue, running_total
WITH daily_region_revenue AS (
    SELECT 
        o.region_code,
        DATE(o.order_date) AS order_date,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS daily_revenue
    FROM orders o
    JOIN order_items oi ON o.order_id = oi.order_id
    WHERE o.status != 'CANCELLED'
    GROUP BY o.region_code, DATE(o.order_date)
)
SELECT 
    region_code,
    order_date,
    daily_revenue,
    ROUND(SUM(daily_revenue) OVER (
        PARTITION BY region_code 
        ORDER BY order_date
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS running_total
FROM daily_region_revenue
ORDER BY region_code, order_date;

-- 8. Ranking with DENSE_RANK: For each category, rank products by total revenue
-- Shows: category, product_name, total_revenue, rank_in_category
WITH product_revenue AS (
    SELECT 
        p.category,
        p.product_name,
        ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_revenue
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.status != 'CANCELLED'
    GROUP BY p.category, p.product_name
)
SELECT 
    category,
    product_name,
    total_revenue,
    DENSE_RANK() OVER (PARTITION BY category ORDER BY total_revenue DESC) AS rank_in_category
FROM product_revenue
ORDER BY category, rank_in_category;

-- 9. LAG/LEAD Analysis: For each customer, calculate days between consecutive orders
-- Shows: customer_id, order_date, previous_order_date, days_gap
-- Flags customers with average gap > 30 days as "At Risk"
WITH customer_order_dates AS (
    SELECT 
        customer_id,
        order_date,
        LAG(order_date, 1) OVER (PARTITION BY customer_id ORDER BY order_date) AS previous_order_date
    FROM orders
    WHERE status != 'CANCELLED'
),
gaps AS (
    SELECT 
        customer_id,
        order_date,
        previous_order_date,
        CASE 
            WHEN previous_order_date IS NULL THEN NULL
            ELSE ROUND(JULIANDAY(order_date) - JULIANDAY(previous_order_date), 2)
        END AS days_gap
    FROM customer_order_dates
),
customer_average_gap AS (
    SELECT 
        customer_id,
        AVG(days_gap) AS avg_days_gap
    FROM gaps
    GROUP BY customer_id
)
SELECT 
    g.customer_id,
    g.order_date,
    g.previous_order_date,
    g.days_gap,
    CASE 
        WHEN cag.avg_days_gap > 30 THEN 'At Risk'
        ELSE 'Normal'
    END AS risk_flag
FROM gaps g
JOIN customer_average_gap cag ON g.customer_id = cag.customer_id
ORDER BY g.customer_id, g.order_date;
