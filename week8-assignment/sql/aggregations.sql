-- Basic SQL Queries - Joins & Aggregations

-- 1. Total revenue per category
-- Formula: revenue = quantity * unit_price * (1 - discount_percent/100)
-- Note: Includes returns (negative quantities) as deduction in revenue
SELECT 
    p.category AS category,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN orders o ON oi.order_id = o.order_id
WHERE o.status != 'CANCELLED' -- Exclude cancelled orders
GROUP BY p.category
ORDER BY total_revenue DESC;

-- 2. Top 10 customers by total order value
SELECT 
    c.customer_id,
    c.customer_name,
    ROUND(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 2) AS total_order_value
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status != 'CANCELLED'
GROUP BY c.customer_id, c.customer_name
ORDER BY total_order_value DESC
LIMIT 10;

-- 3. Month-wise order count for the last 12 months
-- Dynamically calculated relative to the latest order in the database
SELECT 
    STRFTIME('%Y-%m', o.order_date) AS order_month,
    COUNT(DISTINCT o.order_id) AS order_count
FROM orders o
WHERE o.order_date >= DATE((SELECT MAX(order_date) FROM orders), '-12 months')
GROUP BY order_month
ORDER BY order_month DESC;
