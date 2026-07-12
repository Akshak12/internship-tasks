import unittest
import pandas as pd
from datetime import datetime

class TestEdgeCases(unittest.TestCase):

    # 1. What happens when order_items has an order_id not in orders?
    def test_orphan_order_id_in_items(self):
        orders = pd.DataFrame({'order_id': ['ORD-1', 'ORD-2']})
        items = pd.DataFrame({
            'item_id':  ['ITM-1', 'ITM-2', 'ITM-3'],
            'order_id': ['ORD-1', 'ORD-999', 'ORD-2'],  # ORD-999 doesn't exist
            'qty':      [2, 1, 3],
        })
        cleaned = items[items['order_id'].isin(orders['order_id'])]
        self.assertEqual(len(cleaned), 2)
        self.assertNotIn('ORD-999', cleaned['order_id'].values)

    # 2. What happens when discount_percent > 100?
    def test_discount_over_100_clamped_to_zero(self):
        items = pd.DataFrame({
            'item_id':  ['ITM-1', 'ITM-2', 'ITM-3'],
            'discount': [10, 150, -5],  # 150 and -5 are invalid
        })
        items['discount'] = items['discount'].apply(lambda x: x if 0 <= x <= 100 else 0)
        self.assertEqual(items.loc[0, 'discount'], 10)   # valid, unchanged
        self.assertEqual(items.loc[1, 'discount'], 0)    # 150 → clamped to 0
        self.assertEqual(items.loc[2, 'discount'], 0)    # -5  → clamped to 0

    # 3. What happens when quantity is 0?
    def test_zero_quantity_dropped(self):
        items = pd.DataFrame({
            'item_id': ['ITM-1', 'ITM-2', 'ITM-3'],
            'qty':     [0, -2, 3],  # 0 and negative are invalid
        })
        cleaned = items[items['qty'] > 0]
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned['item_id'].values[0], 'ITM-3')

    # 4. What happens when order_date is in the future?
    def test_future_order_date_dropped(self):
        orders = pd.DataFrame({
            'order_id':   ['ORD-1', 'ORD-2'],
            'order_date': ['2028-12-01 10:00:00', '2024-05-15 09:00:00'],
        })
        orders['order_date'] = pd.to_datetime(orders['order_date'], errors='coerce')
        cleaned = orders[orders['order_date'] <= pd.Timestamp.now()]
        self.assertEqual(len(cleaned), 1)
        self.assertEqual(cleaned['order_id'].values[0], 'ORD-2')


if __name__ == '__main__':
    unittest.main(verbosity=2)
