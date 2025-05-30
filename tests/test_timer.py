import unittest

from dmgen.timer import Timer


class TimerTest(unittest.TestCase):
    def test_timer(self):
        timer = Timer(False, 2, True, 'before: ', ': after')
        # Test runtime string rounding down.
        timer.runtime = 1.23456
        self.assertEqual(timer.build_print_string(), 'before: 1.23: after')


if __name__ == "__main__":
    unittest.main()
