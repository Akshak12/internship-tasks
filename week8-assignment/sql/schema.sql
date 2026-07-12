-- Database Schema for E-Commerce Order Analytics System

-- Drop existing tables to ensure clean initialization
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

-- 1. Customers Table
CREATE TABLE customers (
    customer_id TEXT PRIMARY KEY,
    customer_name TEXT NOT NULL,
    email TEXT,
    registration_date DATE NOT NULL,
    customer_type TEXT CHECK (customer_type IN ('REGULAR', 'PREMIUM', 'VIP'))
);

-- 2. Products Table
CREATE TABLE products (
    product_id TEXT PRIMARY KEY,
    product_name TEXT NOT NULL,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    cost_price REAL CHECK (cost_price >= 0)
);

-- 3. Orders Table
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    customer_id TEXT NOT NULL,
    order_date TIMESTAMP NOT NULL,
    status TEXT CHECK (status IN ('PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED')),
    region_code TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id) ON DELETE RESTRICT
);

-- 4. Order Items Table
CREATE TABLE order_items (
    item_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    quantity INTEGER CHECK (quantity != 0), -- Allow negative values for returns, drop zeros
    unit_price REAL CHECK (unit_price >= 0),
    discount_percent REAL CHECK (discount_percent >= 0 AND discount_percent <= 100),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);
