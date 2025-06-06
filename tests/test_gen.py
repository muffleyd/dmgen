import unittest

from dmgen import gen


class GenTest(unittest.TestCase):
    def test_default_of(self):
        import sys
        from io import StringIO
        new_stdin = StringIO('1\n1')
        old_stdin, sys.stdin = sys.stdin, new_stdin
        try:
            self.assertEqual(gen.default_of('give me a 1 (int)! ', float, int), 1)
            val = gen.default_of('give me a 1 (float)! ', float, float)
            self.assertEqual(type(val), float)
            self.assertEqual(val, 1.0)
        finally:
            sys.stdin = old_stdin
    
    def test_count(self):
        self.assertEqual(gen.count([1, 4, 2, 3, 3, 1, 2], 1), 2)
        self.assertEqual(gen.count([1, 23, 4, 1, 2, 3, 4, 1], 2), 1)
        self.assertEqual(gen.count((1, 4, 2, 3, 3, 1, 2), 1), 2)
        self.assertEqual(gen.count({1, 23, 4, 1, 2, 3, 4, 1}, 23), 1)
        self.assertEqual(gen.count({1: 2, 2: 1, 3: 4}, 1), 1)
        self.assertEqual(gen.count({5: 2, 2: 1, 3: 4}, 1), 0)

    def test_list_of(self):
        self.assertEqual(gen.list_of([1, 2, 3, 4, 4]), [1, 2, 3, 4, 4])
        self.assertEqual(gen.list_of((1, 2, 3, 4, 4)), (1, 2, 3, 4, 4))
        self.assertEqual(gen.list_of(9999999), [9999999])

    def test_binary_search_insert(self):
        baseli = list(range(10))
        gen.binary_search_insert(baseli, 55)
        self.assertEqual(baseli, [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 55])
        gen.binary_search_insert(baseli, 4.9)
        self.assertEqual(baseli, [0, 1, 2, 3, 4, 4.9, 5, 6, 7, 8, 9, 55])
        gen.binary_search_insert(baseli, -2)
        self.assertEqual(baseli, [-2, 0, 1, 2, 3, 4, 4.9, 5, 6, 7, 8, 9, 55])
    
    def test_array(self):
        # I think I have array backwards right now.
        self.assertEqual(gen.array(2, 3), [[0, 0], [0, 0], [0, 0]])
    
    def test_changebase(self):
        self.assertEqual(gen.changebase(255, 2), '11111111')
        self.assertEqual(gen.changebase(255, 16), 'FF')
        self.assertEqual(gen.changebase(255, 32), '7V')
        self.assertEqual(gen.changebase(65535, 4), '33333333')
        self.assertEqual(gen.changebase(65535, 32), '1VVV')
        self.assertEqual(gen.changebase(65536, 4), '100000000')
    
    def test_binary_byte(self):
        self.assertEqual(gen.binary_byte(255), '11111111')
        self.assertEqual(gen.binary_byte(254), '11111110')
        self.assertEqual(gen.binary_byte(25), '00011001')
        self.assertEqual(gen.binary_byte(-1), '11111111')

    def test_insertevery(self):
        val = '01100110011001100110011001100101'  # A 32-bit number.
        self.assertEqual(gen.insertevery(val, 8), '01100110 01100110 01100110 01100101')

    def test_str_range(self):
        self.assertEqual(list(gen.str_range(10)), ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'])
        self.assertEqual(list(gen.str_range(9, 11)), ['09', '10'])
        self.assertEqual(list(gen.str_range(10, str_len=2)), ['00', '01', '02', '03', '04', '05', '06', '07', '08', '09'])
        self.assertEqual(list(gen.str_range(0, 10, str_len=2)), list(gen.str_range(10, str_len=2)))

    def test_remove_duplicates(self):
        self.assertEqual(gen.remove_duplicates(list(range(10))), list(range(10)))
        self.assertEqual(gen.remove_duplicates([1, 1, 1, 1, 1, 1]), [1])
        self.assertEqual(gen.remove_duplicates((1, 1, 1, 1, 1, 1)), (1,))
        self.assertEqual(gen.remove_duplicates([8, 6, 7, 5, 3, 0, 9, 9, 9, 9, 9, 9, 9]), [8, 6, 7, 5, 3, 0, 9])
        self.assertEqual(gen.remove_duplicates('hello world'), 'helo wrd')

    def test_extras(self):
        self.assertEqual(gen.extras(list(range(10))), (list(range(10)), []))
        self.assertEqual(gen.extras([1, 1, 1, 1, 1, 1]), ([1], [1, 1, 1, 1, 1]))
        self.assertEqual(gen.extras((1, 1, 1, 1, 1, 1)), ((1,), [1, 1, 1, 1, 1]))
        self.assertEqual(gen.extras([8, 6, 7, 5, 3, 0, 9, 9, 9, 9, 9, 9, 9]), ([8, 6, 7, 5, 3, 0, 9], [9, 9, 9, 9, 9, 9]))
        self.assertEqual(gen.extras('hello world'), ('helo wrd', ['l', 'o', 'l']))

    def test_test_seconds(self):
        import time
        time_to_run = 0.001
        sleep_time = 0.01

        def func(int1, int2, int3, sleep=True):
            if sleep:
                time.sleep(sleep_time)
            return (int1 + int2) * int3

        real_answer = func(1, 2, 3, False)

        run_per, run_times, answer = gen.test_seconds(func, [1, 2, 3], time_to_run=time_to_run)
        # Verify the answer came out right.
        self.assertEqual(answer, real_answer)
        # Verify each run is >= the time the function sleeps. Subtract a tiny amount to avoid minuscule clock errors.
        self.assertGreaterEqual(run_per, sleep_time - 0.000001)
        # Since the time to run is less than the time to sleep, verify its run_times is less than 1.
        self.assertLess(run_times, 1)

        # Test out mixed *args and **kwargs.
        run_per, run_times, answer = gen.test_seconds(func, [1], {'int2': 2, 'int3': 3}, time_to_run=time_to_run)
        self.assertEqual(answer, real_answer)

        # Test out the loops branch.
        run_per, run_times, answer = gen.test_seconds(func, [1], {'int2': 2, 'int3': 3}, time_to_run=time_to_run,
                                                      loops=10)
        self.assertEqual(answer, real_answer)
        self.assertGreaterEqual(run_per, sleep_time - 0.000001)


if __name__ == "__main__":
    unittest.main()
