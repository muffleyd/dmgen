import unittest

from dmgen import maths


class MathsTest(unittest.TestCase):
    def test_primerange(self):
        self.assertEqual(
            maths.primerange(100),
            [False, False, True, True, False, True, False, True, False, False, False, True, False,
             True, False, False, False, True, False, True, False, False, False, True, False,
             False, False, False, False, True, False, True, False, False, False, False, False,
             True, False, False, False, True, False, True, False, False, False, True, False,
             False, False, False, False, True, False, False, False, False, False, True, False,
             True, False, False, False, False, False, True, False, False, False, True, False,
             True, False, False, False, False, False, True, False, False, False, True, False,
             False, False, False, False, True, False, False, False, False, False, False, False,
             True, False, False])
        self.assertEqual(
            maths.primerange(101),
            [False, False, True, True, False, True, False, True, False, False, False, True, False,
             True, False, False, False, True, False, True, False, False, False, True, False,
             False, False, False, False, True, False, True, False, False, False, False, False,
             True, False, False, False, True, False, True, False, False, False, True, False,
             False, False, False, False, True, False, False, False, False, False, True, False,
             True, False, False, False, False, False, True, False, False, False, True, False,
             True, False, False, False, False, False, True, False, False, False, True, False,
             False, False, False, False, True, False, False, False, False, False, False, False,
             True, False, False, False])

    def test_fibonacci(self):
        self.assertEqual(maths.fibonacci(99), 218922995834555169026)
        self.assertEqual(maths._fibonacci_known[98], 135301852344706746049)


if __name__ == "__main__":
    unittest.main()
