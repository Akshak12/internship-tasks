import os
import json
import csv
import random
from datetime import datetime, timedelta
from faker import Faker

def generate_datasets():
    fake = Faker('en_IN')
    random.seed(42)
    Faker.seed(42)

    # Base configuration
    num_customers = 200
    num_products = 30
    num_orders = 1000
    
    cities = ['Delhi', 'Mumbai', 'Bengaluru']
    zones = {
        'Delhi': ['South Delhi', 'Karol Bagh', 'Dwarka', 'Rohini', 'Connaught Place'],
        'Mumbai': ['Andheri West', 'Bandra', 'Colaba', 'Juhu', 'Thane'],
        'Bengaluru': ['Indiranagar', 'Koramangala', 'Whitefield', 'Jayanagar', 'Yelahanka']
    }
    payment_modes = ['UPI', 'COD', 'Card']
    statuses = ['delivered', 'cancelled', 'returned']

    # --- 1. Products Generation ---
    products_raw = []
    product_categories = {
        'Dairy': [('Amul Butter 500g', 55.00), ('Mother Dairy Milk 1L', 66.00), ('Paneer 200g', 85.00), ('Greek Yogurt 150g', 50.00), ('Amul Cheese Slices 200g', 120.00)],
        'Bakery': [('Whole Wheat Bread', 45.00), ('White Bread', 35.00), ('Croissant', 60.00), ('Chocolate Muffin', 40.00), ('Garlic Bread', 80.00)],
        'Beverages': [('Coca Cola 2L', 99.00), ('Tropicana Orange 1L', 99.00), ('Nescafé Classic 100g', 299.00), ('Red Label Tea 250g', 140.00), ('Pepsi 750ml', 45.00)],
        'Produce': [('Organic Bananas 1kg', 60.00), ('Washington Apples 1kg', 220.00), ('Onions 5kg', 180.00), ('Potatoes 5kg', 150.00), ('Tomatoes 1kg', 40.00)],
        'Snacks': [('Lays Potato Chips', 20.00), ('Oreo Biscuits', 30.00), ('Kurkure Masala Munch', 20.00), ('Haldiram Bhujia 150g', 55.00), ('Cadbury Dairy Milk 100g', 100.00)]
    }

    prod_id_counter = 101
    for category, items in product_categories.items():
        for name, price in items:
            products_raw.append({
                'product_id': f"PRD-{prod_id_counter}",
                'product_name': name,
                'category': category,
                'base_price': price
            })
            prod_id_counter += 1

    # Add invalid negative price products to raw data
    products_raw.append({
        'product_id': 'PRD-999',
        'product_name': 'Expired Milk (Promo)',
        'category': 'Dairy',
        'base_price': -20.00
    })
    products_raw.append({
        'product_id': 'PRD-998',
        'product_name': 'Damaged Muffin',
        'category': 'Bakery',
        'base_price': -5.00
    })

    # --- 2. Customers Generation ---
    customers_raw = []
    cust_id_counter = 1001
    for _ in range(num_customers):
        city = random.choice(cities)
        name = fake.name()
        email = f"{name.lower().replace(' ', '.')}@example.com"
        phone = f"+91-{random.randint(7000000000, 9999999999)}"
        reg_date = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 450))).strftime("%Y-%m-%d")
        
        customers_raw.append({
            'customer_id': f"CUST-{cust_id_counter}",
            'name': name,
            'email': email,
            'phone': phone,
            'city': city,
            'registered_on': reg_date,
            'loyalty_points': random.randint(0, 500)
        })
        cust_id_counter += 1

    # Add duplicates & inconsistencies to customers
    # Duplicate records
    for i in range(5):
        customers_raw.append(customers_raw[i].copy())
    # Null values (missing phone or email)
    for i in range(10, 20):
        customers_raw[i]['email'] = ''
    for i in range(20, 30):
        customers_raw[i]['phone'] = ''
    # Invalid loyalty points
    for i in range(30, 35):
        customers_raw[i]['loyalty_points'] = -100
    # Invalid registration dates (future/incorrect format)
    customers_raw[40]['registered_on'] = '2028-12-15' # Future date
    customers_raw[41]['registered_on'] = '15/08/2023' # Bad format

    # --- 3. Orders Generation ---
    orders_raw = []
    order_id_counter = 100001
    start_date = datetime(2024, 4, 1)
    
    # We will track generated order IDs to reference in order_items
    for _ in range(num_orders):
        cust = random.choice(customers_raw)
        cust_id = cust['customer_id']
        city = cust['city']
        order_date = start_date + timedelta(days=random.randint(0, 89), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        status = random.choices(statuses, weights=[0.75, 0.10, 0.15])[0]
        
        orders_raw.append({
            'order_id': f"ORD-{order_id_counter}",
            'customer_id': cust_id,
            'order_date': order_date.strftime("%Y-%m-%d %H:%M:%S"),
            'city': city,
            'payment_mode': random.choice(payment_modes),
            'status': status
        })
        order_id_counter += 1

    # Add inconsistencies to orders
    # Duplicate orders
    for i in range(10):
        orders_raw.append(orders_raw[i].copy())
    # Order for non-existent customer (Mismatched IDs)
    for i in range(10):
        orders_raw[i+10]['customer_id'] = 'CUST-9999'
    # Order with null customer_id
    for i in range(10):
        orders_raw[i+20]['customer_id'] = ''
    # Orders with mismatched city (Order city != Customer city)
    for i in range(10):
        orders_raw[i+30]['city'] = 'Kolkata' # Invalid city not in the Delhi, Mumbai, Bengaluru
    # Order with future date
    orders_raw[40]['order_date'] = '2028-05-10 12:00:00'
    orders_raw[41]['order_date'] = 'invalid-date-format'

    # --- 4. Order Items Generation ---
    order_items_raw = []
    item_id_counter = 100001
    
    for order in orders_raw:
        # Skip duplicates or invalid orders for clean structure, but let them run for raw
        num_items = random.randint(1, 4)
        for _ in range(num_items):
            prod = random.choice(products_raw)
            # Introduce discount (mostly valid, some 0)
            discount = random.choice([0, 5, 10, 15, 20])
            qty = random.randint(1, 5)
            
            order_items_raw.append({
                'item_id': f"ITM-{item_id_counter:06d}",
                'order_id': order['order_id'],
                'product_id': prod['product_id'],
                'product_name': prod['product_name'],
                'category': prod['category'],
                'qty': qty,
                'unit_price': prod['base_price'],
                'discount': discount
            })
            item_id_counter += 1

    # Add inconsistencies to order items
    # Duplicate order items
    for i in range(15):
        order_items_raw.append(order_items_raw[i].copy())
    # Order items for non-existent order
    for i in range(10):
        order_items_raw[i+15]['order_id'] = 'ORD-999999'
    # Negative qty
    for i in range(10):
        order_items_raw[i+30]['qty'] = -2
    # Negative unit_price
    for i in range(5):
        order_items_raw[i+45]['unit_price'] = -15.00
    # Invalid discount (e.g. > 100 or negative)
    order_items_raw[60]['discount'] = 150
    order_items_raw[61]['discount'] = -10

    # --- Write Files ---
    os.makedirs('data/raw', exist_ok=True)
    
    # 1. Customers CSV
    with open('data/raw/customers.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=customers_raw[0].keys())
        writer.writeheader()
        writer.writerows(customers_raw)

    # 2. Products CSV
    with open('data/raw/products.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=products_raw[0].keys())
        writer.writeheader()
        writer.writerows(products_raw)

    # 3. Orders CSV
    with open('data/raw/orders.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=orders_raw[0].keys())
        writer.writeheader()
        writer.writerows(orders_raw)

    # 4. Order Items CSV
    with open('data/raw/order_items.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=order_items_raw[0].keys())
        writer.writeheader()
        writer.writerows(order_items_raw)

    print("Raw datasets generated successfully!")
    print(f"Generated {len(customers_raw)} customer records (with duplicates).")
    print(f"Generated {len(products_raw)} product records.")
    print(f"Generated {len(orders_raw)} orders.")
    print(f"Generated {len(order_items_raw)} order items.")

if __name__ == '__main__':
    generate_datasets()
