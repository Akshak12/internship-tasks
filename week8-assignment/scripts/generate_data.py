import os
import csv
import random
from datetime import datetime, timedelta
from faker import Faker

def generate_datasets():
    # Initialize Faker and seed for reproducibility
    fake = Faker('en_US')
    random.seed(42)
    Faker.seed(42)

    # Base configuration ensuring >500 records per table
    num_customers = 550
    num_products = 520
    num_orders = 1000
    
    region_codes = ['REG_NORTH', 'REG_SOUTH', 'REG_EAST', 'REG_WEST']
    customer_types = ['REGULAR', 'PREMIUM', 'VIP']
    statuses = ['PLACED', 'SHIPPED', 'DELIVERED', 'CANCELLED', 'RETURNED']

    # --- 1. Products Generation ---
    # Products table: product_id, product_name, category, subcategory, cost_price
    categories = {
        'Electronics': ['Phones', 'Laptops', 'Headphones', 'Smartwatches', 'Cameras'],
        'Clothing': ['T-Shirts', 'Jeans', 'Jackets', 'Socks', 'Sneakers'],
        'Home': ['Furniture', 'Cookware', 'Lighting', 'Bedding', 'Decor'],
        'Books': ['Fiction', 'Non-Fiction', 'Sci-Fi', 'Biography', 'Children']
    }

    products_raw = []
    prod_id_counter = 101
    
    while len(products_raw) < num_products:
        category = random.choice(list(categories.keys()))
        subcategory = random.choice(categories[category])
        
        # Simple product name generation using Faker and categories
        if category == 'Electronics':
            brand = fake.company()
            product_name = f"{brand} {subcategory[:-1]} Model {random.randint(1, 9)}"
            cost_price = round(random.uniform(500, 80000), 2)
        elif category == 'Clothing':
            color = fake.color_name()
            product_name = f"{color} {subcategory[:-1]}"
            cost_price = round(random.uniform(200, 5000), 2)
        elif category == 'Home':
            material = random.choice(['Wooden', 'Metal', 'Glass', 'Ceramic'])
            product_name = f"{material} {subcategory}"
            cost_price = round(random.uniform(150, 15000), 2)
        else: # Books
            title = fake.catch_phrase()
            product_name = f"'{title}' Book"
            cost_price = round(random.uniform(100, 1500), 2)

        products_raw.append({
            'product_id': f"PRD-{prod_id_counter:04d}",
            'product_name': product_name,
            'category': category,
            'subcategory': subcategory,
            'cost_price': cost_price
        })
        prod_id_counter += 1

    # Introduce product anomalies: 10% with extra spaces and mixed case
    for i in range(len(products_raw)):
        if random.random() < 0.10:
            name = products_raw[i]['product_name']
            # Introduce random case and extra spacing
            name_chars = [c.upper() if random.random() < 0.3 else c.lower() for c in name]
            mixed_name = "".join(name_chars)
            products_raw[i]['product_name'] = f"   {mixed_name}   "

    # --- 2. Customers Generation ---
    # Customers table: customer_id, customer_name, email, registration_date, customer_type
    customers_raw = []
    cust_id_counter = 1001
    
    for _ in range(num_customers):
        name = fake.name()
        email = f"{name.lower().replace(' ', '.')}@example.com"
        reg_date = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 1000))).strftime("%Y-%m-%d")
        cust_type = random.choice(customer_types)
        
        customers_raw.append({
            'customer_id': f"CUST-{cust_id_counter:04d}",
            'customer_name': name,
            'email': email,
            'registration_date': reg_date,
            'customer_type': cust_type
        })
        cust_id_counter += 1

    # Introduce customer anomalies: 2% invalid emails (missing @ or domain)
    num_invalid_emails = int(num_customers * 0.02)
    invalid_indices = random.sample(range(num_customers), num_invalid_emails)
    for idx in invalid_indices:
        email = customers_raw[idx]['email']
        if random.random() < 0.5:
            # Missing @
            customers_raw[idx]['email'] = email.replace('@', '')
        else:
            # Missing domain
            customers_raw[idx]['email'] = email.split('@')[0] + '@'

    # --- 3. Orders Generation ---
    # Orders table: order_id, customer_id, order_date, status, region_code
    orders_raw = []
    order_id_counter = 100001
    start_date = datetime(2025, 4, 1) # Orders span the last 15 months to support last 12 months query
    
    for _ in range(num_orders):
        cust = random.choice(customers_raw)
        cust_id = cust['customer_id']
        order_date = start_date + timedelta(days=random.randint(0, 450), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        status = random.choices(statuses, weights=[0.60, 0.15, 0.15, 0.05, 0.05])[0]
        region = random.choice(region_codes)
        
        orders_raw.append({
            'order_id': f"ORD-{order_id_counter:06d}",
            'customer_id': cust_id,
            'order_date': order_date.strftime("%Y-%m-%d %H:%M:%S"),
            'status': status,
            'region_code': region
        })
        order_id_counter += 1

    # Introduce order anomalies:
    # 5% of orders should have NULL/empty customer_id
    num_null_cust = int(num_orders * 0.05)
    null_cust_indices = random.sample(range(num_orders), num_null_cust)
    for idx in null_cust_indices:
        orders_raw[idx]['customer_id'] = ''

    # Some orders (about 20) with wrong date format (DD-MM-YYYY)
    wrong_date_indices = random.sample(list(set(range(num_orders)) - set(null_cust_indices)), 20)
    for idx in wrong_date_indices:
        dt_obj = datetime.strptime(orders_raw[idx]['order_date'], "%Y-%m-%d %H:%M:%S")
        orders_raw[idx]['order_date'] = dt_obj.strftime("%d-%m-%Y")

    # Add 1 future date order to check cleaning
    future_idx = random.choice(list(set(range(num_orders)) - set(null_cust_indices) - set(wrong_date_indices)))
    orders_raw[future_idx]['order_date'] = '2028-12-15 10:00:00'

    # --- 4. Order Items Generation ---
    # Order items table: item_id, order_id, product_id, quantity, unit_price, discount_percent
    order_items_raw = []
    item_id_counter = 100001
    
    # We will generate about 2.5 items per order on average to cross 2500 records
    for order in orders_raw:
        # If customer_id is empty, it's an anomaly, but still generate items for it to test cascades
        num_items = random.randint(2, 4)
        for _ in range(num_items):
            prod = random.choice(products_raw)
            unit_price = prod['cost_price'] # Using cost_price as unit_price for raw order
            discount = random.choice([0, 5, 10, 15, 20])
            qty = random.randint(1, 10)
            
            order_items_raw.append({
                'item_id': f"ITM-{item_id_counter:06d}",
                'order_id': order['order_id'],
                'product_id': prod['product_id'],
                'quantity': qty,
                'unit_price': unit_price,
                'discount_percent': discount
            })
            item_id_counter += 1

    # Ensure we have at least 2500 order items
    while len(order_items_raw) < 2500:
        order = random.choice(orders_raw)
        prod = random.choice(products_raw)
        discount = random.choice([0, 5, 10, 15, 20])
        qty = random.randint(1, 10)
        order_items_raw.append({
            'item_id': f"ITM-{item_id_counter:06d}",
            'order_id': order['order_id'],
            'product_id': prod['product_id'],
            'quantity': qty,
            'unit_price': prod['cost_price'],
            'discount_percent': discount
        })
        item_id_counter += 1

    # Introduce order_item anomalies:
    # 3% of order_items with negative quantity (returns)
    num_negative_qty = int(len(order_items_raw) * 0.03)
    negative_indices = random.sample(range(len(order_items_raw)), num_negative_qty)
    for idx in negative_indices:
        order_items_raw[idx]['quantity'] = -random.randint(1, 5)

    # Some invalid discount percent (>100 or negative)
    discount_anom_indices = random.sample(list(set(range(len(order_items_raw))) - set(negative_indices)), 15)
    for idx in discount_anom_indices:
        order_items_raw[idx]['discount_percent'] = random.choice([120, -5])

    # Some zero quantity order items
    zero_qty_indices = random.sample(list(set(range(len(order_items_raw))) - set(negative_indices) - set(discount_anom_indices)), 10)
    for idx in zero_qty_indices:
        order_items_raw[idx]['quantity'] = 0

    # Referential integrity issue: order items with invalid order_id (not in orders)
    orphan_indices = random.sample(list(set(range(len(order_items_raw))) - set(negative_indices) - set(discount_anom_indices) - set(zero_qty_indices)), 10)
    for idx in orphan_indices:
        order_items_raw[idx]['order_id'] = 'ORD-999999'

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
    print(f"Generated {len(customers_raw)} customer records.")
    print(f"Generated {len(products_raw)} product records.")
    print(f"Generated {len(orders_raw)} orders.")
    print(f"Generated {len(order_items_raw)} order items.")

if __name__ == '__main__':
    generate_datasets()
