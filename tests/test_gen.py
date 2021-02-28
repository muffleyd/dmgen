import unittest

from dmgen import gen


class GenTest(unittest.TestCase):
    def test_timer(self):
        timer = gen.timer(False, 2, True, 'before: ', ': after')
        timer.runtime = 1.23456
        self.assertEqual(timer.build_print_string(), 'before: 1.23: after')


if __name__ == "__main__":
    unittest.main()
