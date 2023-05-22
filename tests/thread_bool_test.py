# -*- coding: utf-8 -*-
import unittest
from ..core.threading import ThreadSafeBool


class ThreadBoolTest(unittest.TestCase):
    def basicTest(self):
        f = ThreadSafeBool(False)
        self.assertEqual(f, False)

        f.set()
        self.assertEqual(f.is_set(), True)

        f.clear()
        self.assertEqual(f.is_set(), False)

        self.assertEqual(f, True)

    def testRisingEdge(self):
        f = ThreadSafeBool(False)
        self.assertEqual(f.is_rising_edge(), False)

        f.set()
        self.assertEqual(f.is_rising_edge(), True)

        f.set()
        self.assertEqual(f.is_rising_edge(), True)

        f.clear()
        self.assertEqual(f.is_rising_edge(), False)
        self.assertEqual(f.is_falling_edge(), True)

    def testFallingEdge(self):
        f = ThreadSafeBool(True)
        self.assertEqual(f.is_falling_edge(), False)

        f.clear()
        self.assertEqual(f.is_falling_edge(), True)

        f.clear()
        self.assertEqual(f.is_falling_edge(), True)

        f.set()
        self.assertEqual(f.is_falling_edge(), False)
        self.assertEqual(f.is_rising_edge(), True)

    def testNegativePulse(self):
        f = ThreadSafeBool(True)
        f.clear()
        f.set()
        self.assertEqual(f.is_n_pulse(), True)

        f.set()
        f.set()
        f.clear()
        f.clear()
        f.set()
        self.assertEqual(f.is_n_pulse(), True)
        f.clear()
        self.assertEqual(f.is_n_pulse(), False)
        self.assertEqual(f.is_p_pulse(), True)

    def testPositivePulse(self):
        f = ThreadSafeBool(False)
        f.set()
        f.clear()
        self.assertEqual(f.is_p_pulse(), True)

        f.set()
        f.set()
        f.clear()
        f.clear()
        f.clear()
        self.assertEqual(f.is_p_pulse(), True)

        f.set()
        self.assertEqual(f.is_p_pulse(), False)
        self.assertEqual(f.is_n_pulse(), True)


if __name__ == "__main__":
    unittest.main()
