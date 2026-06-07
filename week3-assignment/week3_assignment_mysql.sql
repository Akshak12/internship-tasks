-- STEP 1 - Load Superstore Dataset into a Table

CREATE DATABASE IF NOT EXISTS superstore;
USE superstore;
SELECT DATABASE();
CREATE TABLE superstore_raw (
    row_id INT,
    order_id VARCHAR(50),
    order_date VARCHAR(20),
    ship_date VARCHAR(20),
    ship_mode VARCHAR(50),
    customer_id VARCHAR(50),
    customer_name VARCHAR(100),
    segment VARCHAR(50),
    country VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    region VARCHAR(50),
    product_id VARCHAR(50),
    category VARCHAR(50),
    sub_category VARCHAR(50),
    product_name VARCHAR(500),
    sales DECIMAL(12,4),
    quantity INT,
    discount DECIMAL(5,4),
    profit DECIMAL(12,4)
);

SELECT * FROM superstore_raw;



-- STEP 2 - Create Dimensional Tables

-- 1. Customers Table
CREATE TABLE customers (
    customer_id VARCHAR(20) PRIMARY KEY,
    customer_name VARCHAR(100),
    segment VARCHAR(50),
    country VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    postal_code VARCHAR(20),
    region VARCHAR(50)
);

INSERT INTO customers (
    customer_id, customer_name, segment, country,
    city, state, postal_code, region
)
SELECT DISTINCT
    customer_id, customer_name, segment, country,
    city, state, postal_code, region
FROM superstore_raw
GROUP BY customer_id, customer_name, segment, country,
         city, state, postal_code, region;


-- 2. Products Table
CREATE TABLE products (
    product_id VARCHAR(50) PRIMARY KEY,
    product_name VARCHAR(255),
    category VARCHAR(50),
    sub_category VARCHAR(50)
);

INSERT INTO products (
    product_id, product_name, category, sub_category
)
SELECT DISTINCT
    product_id, product_name, category, sub_category
FROM superstore_raw
GROUP BY product_id, product_name, category, sub_category;


-- 3. Orders Table
CREATE TABLE orders (
    row_id INT PRIMARY KEY,
    order_id VARCHAR(50),
    order_date DATE,
    ship_date DATE,
    ship_mode VARCHAR(50),
    customer_id VARCHAR(20),
    product_id VARCHAR(50),
    sales DECIMAL(10,2),
    quantity INT,
    discount DECIMAL(5,2),
    profit DECIMAL(10,2),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

INSERT INTO orders (
    row_id, order_id, order_date, ship_date, ship_mode,
    customer_id, product_id, sales, quantity, discount, profit
)
SELECT DISTINCT
    row_id,
    order_id,
    STR_TO_DATE(order_date, '%m/%d/%Y'),
    STR_TO_DATE(ship_date, '%m/%d/%Y'),
    ship_mode,
    customer_id,
    product_id,
    sales,
    quantity,
    discount,
    profit
FROM superstore_raw;


-- Display Tables
SELECT * FROM customers LIMIT 10;
SELECT * FROM products LIMIT 10;
SELECT * FROM orders LIMIT 10;

-- Record Counts
SELECT COUNT(*) AS total_customers FROM customers;
SELECT COUNT(*) AS total_products FROM products;
SELECT COUNT(*) AS total_orders FROM orders;



-- STEP 3 - Subqueries

-- 1. Orders with Above Average Sales
SELECT *
FROM orders
WHERE sales > (
    SELECT AVG(sales)
    FROM orders
);

-- 2. Highest Order Per Customer
SELECT customer_id, order_id, sales
FROM orders o
WHERE sales = (
    SELECT MAX(sales)
    FROM orders o2
    WHERE o.customer_id = o2.customer_id
);



-- STEP 4 - CTE (Common Table Expressions)

-- 1. Total Sales Per Customer
WITH customer_sales AS (
    SELECT customer_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
ORDER BY total_sales DESC;

-- 2. Total Profit Per Customer
WITH customer_profit AS (
    SELECT customer_id, SUM(profit) AS total_profit
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_profit
ORDER BY total_profit DESC;



-- STEP 5 - Window Functions

-- 1. ROW_NUMBER()
SELECT
    customer_id,
    sales,
    ROW_NUMBER() OVER (ORDER BY sales DESC) AS row_num
FROM orders;

-- 2. RANK()
SELECT
    customer_id,
    sales,
    RANK() OVER (ORDER BY sales DESC) AS sales_rank
FROM orders;

-- 3. DENSE_RANK()
SELECT
    customer_id,
    sales,
    DENSE_RANK() OVER (ORDER BY sales DESC) AS dense_rank_no
FROM orders;



-- STEP 6 - JOIN + CTE + Window Functions Combined

WITH customer_sales AS (
    SELECT customer_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT
    c.customer_id,
    c.customer_name,
    cs.total_sales,
    RANK() OVER (ORDER BY cs.total_sales DESC) AS customer_rank
FROM customer_sales cs
JOIN customers c ON cs.customer_id = c.customer_id
ORDER BY customer_rank;



-- STEP 7 - Business Queries

-- 1. Top 10 Customers by Total Sales
WITH customer_sales AS (
    SELECT customer_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
ORDER BY total_sales DESC
LIMIT 10;

-- 2. Bottom 10 Customers by Total Sales
WITH customer_sales AS (
    SELECT customer_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
ORDER BY total_sales ASC
LIMIT 10;

-- 3. Single-Order Customers
SELECT
    customer_id,
    COUNT(DISTINCT order_id) AS total_orders
FROM orders
GROUP BY customer_id
HAVING COUNT(DISTINCT order_id) = 1;

-- 4. Customers Above Average Total Sales
WITH customer_sales AS (
    SELECT customer_id, SUM(sales) AS total_sales
    FROM orders
    GROUP BY customer_id
)
SELECT *
FROM customer_sales
WHERE total_sales > (
    SELECT AVG(total_sales)
    FROM customer_sales
);
