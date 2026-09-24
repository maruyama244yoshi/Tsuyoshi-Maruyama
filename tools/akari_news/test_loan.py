"""台本に書かれた数値が試算ロジックと一致することを検証する。 python3 -m unittest tools.akari_news.test_loan"""
import unittest
from tools.akari_news.loan import annual_payment, man, monthly_payment


class ScriptNumbers(unittest.TestCase):
    P, Y = 100_000_000, 30

    def test_200(self):
        self.assertEqual(man(annual_payment(self.P, 2.00, self.Y)), 444)  # 「およそ444万円」

    def test_225(self):
        self.assertEqual(man(annual_payment(self.P, 2.25, self.Y)), 459)  # 「およそ459万円」

    def test_diff(self):
        d = annual_payment(self.P, 2.25, self.Y) - annual_payment(self.P, 2.00, self.Y)
        self.assertEqual(man(d), 15)  # 「年間約15万円」

    def test_zero_rate(self):
        self.assertEqual(monthly_payment(1_200_000, 0, 1), 100_000)


if __name__ == "__main__":
    unittest.main()
