import unittest
from math_ops import combine


class TestCombine(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(combine(2, 3), 5)

    def test_zero(self):
        self.assertEqual(combine(8, 0), 8)

    def test_negative(self):
        self.assertEqual(combine(-4, -2), -6)
