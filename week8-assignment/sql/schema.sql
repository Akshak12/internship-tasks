-- Schema DDL for FreshMart Retail Analytics System

-- Drop tables if they exist (for easy schema reset)
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- 1. Customers Table
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT, -- PII masked (SHA-256)
    phone TEXT, -- PII masked (SHA-256)
    city TEXT CHECK (city IN ('Delhi', 'Mumbai', 'Bengaluru')),
    registered_on DATE NOT NULL,
    loyalty_points INTEGER CHECK (loyalty_points >= 0)
);

-- 2. Products Table
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    base_price REAL CHECK (base_price >= 0)
);

-- 3. Orders Table
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TIMESTAMP NOT NULL,
    city TEXT CHECK (city IN ('Delhi', 'Mumbai', 'Bengaluru')),
    payment_mode TEXT CHECK (payment_mode IN ('UPI', 'COD', 'Card')),
    status TEXT CHECK (status IN ('delivered', 'cancelled', 'returned')),
    order_total REAL, -- Computed as SUM(net_price) of items in clean step
    total_discount REAL, -- Computed as SUM(discount_amount) of items in clean step
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT
);

-- 4. Order Items Table
CREATE TABLE order_items (
    item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    qty INTEGER CHECK (qty > 0),
    unit_price REAL CHECK (unit_price >= 0),
    discount REAL CHECK (discount >= 0 AND discount <= 100),
    net_price REAL, -- Computed in clean step as qty * unit_price * (1 - discount/100)
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);
