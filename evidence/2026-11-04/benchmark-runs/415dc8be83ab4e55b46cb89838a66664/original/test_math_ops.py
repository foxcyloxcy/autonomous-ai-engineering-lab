import unittest
from math_ops import combine


class TestCombine(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(combine(2, 3), 10)

    def test_zero(self):
        self.assertEqual(combine(8, 0), 16)
