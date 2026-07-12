-- Basic SQL Analytics - Joins & Aggregations

-- 1. Total revenue per customer, per product category, per month
SELECT 
    c.customer_id,
    c.name AS customer_name,
    oi.category AS product_category,
    strftime('%Y-%m', o.order_date) AS order_month,
    ROUND(SUM(oi.net_price), 2) AS total_revenue,
    SUM(oi.qty) AS total_quantity
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status != 'cancelled'
GROUP BY c.customer_id, c.name, oi.category, order_month
ORDER BY total_revenue DESC
LIMIT 20;

-- 2. Top products by quantity sold and revenue
SELECT 
    product_id,
    product_name,
    category,
    SUM(qty) AS total_qty_sold,
    ROUND(SUM(net_price), 2) AS total_revenue
FROM order_items oi
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status != 'cancelled'
GROUP BY product_id, product_name, category
ORDER BY total_revenue DESC, total_qty_sold DESC
LIMIT 10;

-- 3. Average Order Value (AOV) by customer frequency segment
-- Segments defined by order count: Loyal (>=5), Occasional (2-4), One-time (1)
WITH customer_order_metrics AS (
    SELECT 
        customer_id,
        COUNT(DISTINCT order_id) AS total_orders_placed
    FROM orders
    WHERE status != 'cancelled'
    GROUP BY customer_id
),
customer_segments AS (
    SELECT 
        c.customer_id,
        CASE 
            WHEN COALESCE(m.total_orders_placed, 0) >= 5 THEN 'Loyal'
            WHEN COALESCE(m.total_orders_placed, 0) BETWEEN 2 AND 4 THEN 'Occasional'
            ELSE 'One-time'
        END AS frequency_segment
    FROM customers c
    LEFT JOIN customer_order_metrics m ON c.customer_id = m.customer_id
)
SELECT 
    cs.frequency_segment,
    ROUND(AVG(o.order_total), 2) AS average_order_value,
    COUNT(DISTINCT o.order_id) AS order_count
FROM orders o
JOIN customer_segments cs ON o.customer_id = cs.customer_id
WHERE o.status != 'cancelled'
GROUP BY cs.frequency_segment
ORDER BY average_order_value DESC;
