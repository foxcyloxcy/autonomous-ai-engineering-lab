import unittest
from math_ops import combine


class TestCombine(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(combine(3, 4), 12)

    def test_zero(self):
        self.assertEqual(combine(0, 0), 0)
