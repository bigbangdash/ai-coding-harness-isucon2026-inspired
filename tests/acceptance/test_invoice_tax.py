"""受入条件 specs/invoice-tax/acceptance.md のテスト。AC の ID をテスト名に入れる。"""
import unittest

from app.invoice.tax import InvoiceTaxError, Line, calculate


class InvoiceTaxAcceptance(unittest.TestCase):
    def test_ac_1_standard_rate_only(self):
        r = calculate([Line(1000, 3, 10), Line(333, 1, 10)])
        self.assertEqual(r.by_rate[10].subtotal, 3333)
        self.assertEqual(r.by_rate[10].tax, 333)
        self.assertEqual(r.total, 3666)

    def test_ac_2_mixed_rates(self):
        r = calculate([Line(1000, 1, 10), Line(1001, 1, 8)])
        self.assertEqual(r.by_rate[10].tax, 100)
        self.assertEqual(r.by_rate[8].tax, 80)
        self.assertEqual((r.subtotal, r.tax, r.total), (2001, 180, 2181))

    def test_ac_3_round_once_per_rate(self):
        r = calculate([Line(15, 1, 10)] * 3)
        self.assertEqual(r.tax, 4)

    def test_ac_4_no_lines(self):
        r = calculate([])
        self.assertEqual((r.subtotal, r.tax, r.total), (0, 0, 0))

    def test_ac_5_negative_quantity(self):
        with self.assertRaises(InvoiceTaxError):
            calculate([Line(100, -1, 10)])

    def test_ac_6_unsupported_rate(self):
        with self.assertRaises(InvoiceTaxError):
            calculate([Line(100, 1, 5)])


if __name__ == "__main__":
    unittest.main()
