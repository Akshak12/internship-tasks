import unittest
import pandas as pd
from datetime import datetime, timedelta

# Import functions from the scripts.clean_data module
from scripts.clean_data import clean_orders, check_referential_integrity

class TestEdgeCases(unittest.TestCase):

    # 1. What happens when order_items has an order_id not in orders?
    def test_orphan_order_id_in_items(self):
        orders = pd.DataFrame({
            'order_id': ['ORD-000001', 'ORD-000002'],
            'customer_id': ['CUST-1001', 'CUST-1002'],
            'order_date': ['2025-06-01 10:00:00', '2025-06-02 12:00:00'],
            'status': ['DELIVERED', 'SHIPPED'],
            'region_code': ['REG_NORTH', 'REG_SOUTH']
        })
        items = pd.DataFrame({
            'item_id':  ['ITM-000001', 'ITM-000002', 'ITM-000003'],
            'order_id': ['ORD-000001', 'ORD-999999', 'ORD-000002'],  # ORD-999999 doesn't exist
            'quantity': [2, 1, 3],
        })
        # check_referential_integrity finds orphans
        orphans = check_referential_integrity(orders, items)
        self.assertIn('ITM-000002', orphans)
        
        # Filter orphans out
        cleaned_items = items[~items['item_id'].isin(orphans)]
        self.assertEqual(len(cleaned_items), 2)
        self.assertNotIn('ORD-999999', cleaned_items['order_id'].values)

    # 2. What happens when discount_percent > 100?
    def test_discount_over_100_reset_to_zero(self):
        items = pd.DataFrame({
            'item_id':  ['ITM-000001', 'ITM-000002', 'ITM-000003'],
            'discount_percent': [10.0, 150.0, -5.0],  # 150 and -5 are invalid
        })
        # Reset invalid discounts to 0.0 (simulating clean_data.py logic)
        invalid_discount_mask = (items['discount_percent'] < 0) | (items['discount_percent'] > 100)
        items.loc[invalid_discount_mask, 'discount_percent'] = 0.0
        
        self.assertEqual(items.loc[0, 'discount_percent'], 10.0)   # valid, unchanged
        self.assertEqual(items.loc[1, 'discount_percent'], 0.0)    # 150.0 → reset to 0.0
        self.assertEqual(items.loc[2, 'discount_percent'], 0.0)    # -5.0  → reset to 0.0

    # 3. What happens when quantity is 0?
    def test_zero_quantity_dropped(self):
        items = pd.DataFrame({
            'item_id': ['ITM-000001', 'ITM-000002', 'ITM-000003'],
            'quantity': [0, -2, 3],  # 0 is invalid, -2 is a return (valid)
        })
        # Drop quantity == 0
        cleaned_items = items[items['quantity'] != 0]
        self.assertEqual(len(cleaned_items), 2)
        self.assertNotIn('ITM-000001', cleaned_items['item_id'].values)
        self.assertIn('ITM-000002', cleaned_items['item_id'].values) # Returns preserved

    # 4. What happens when order_date is in the future?
    def test_future_order_date_dropped(self):
        now = datetime.now()
        future_date = (now + timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
        past_date = (now - timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
        
        orders = pd.DataFrame({
            'order_id': ['ORD-000001', 'ORD-000002'],
            'customer_id': ['CUST-1001', 'CUST-1002'],
            'order_date': [future_date, past_date],
            'status': ['PLACED', 'DELIVERED'],
            'region_code': ['REG_NORTH', 'REG_SOUTH']
        })
        
        cleaned_orders, report = clean_orders(orders)
        self.assertEqual(len(cleaned_orders), 1)
        self.assertEqual(cleaned_orders['order_id'].values[0], 'ORD-000002')
        self.assertEqual(report['future_dates_dropped'], 1)

if __name__ == '__main__':
    unittest.main(verbosity=2)
