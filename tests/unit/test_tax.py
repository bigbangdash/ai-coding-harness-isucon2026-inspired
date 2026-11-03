import unittest

from app.invoice.tax import InvoiceTaxError, Line, calculate


class TaxUnit(unittest.TestCase):
    def test_floor_not_round(self):
        # 8% × 1,006 = 80.48、8% × 1,012 = 80.96 → どちらも 80
        self.assertEqual(calculate([Line(1006, 1, 8)]).tax, 80)
        self.assertEqual(calculate([Line(1012, 1, 8)]).tax, 80)

    def test_rates_are_kept_separate(self):
        r = calculate([Line(5, 1, 10), Line(5, 1, 8)])
        self.assertEqual(set(r.by_rate), {10, 8})
        self.assertEqual(r.tax, 0)

    def test_zero_quantity_allowed(self):
        self.assertEqual(calculate([Line(100, 0, 10)]).total, 0)

    def test_negative_price_rejected(self):
        with self.assertRaises(InvoiceTaxError):
            calculate([Line(-1, 1, 10)])


if __name__ == "__main__":
    unittest.main()
