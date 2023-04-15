import unittest

from dmgen import filegen


class FilegenTest(unittest.TestCase):
    def test_extensionis(self):
        self.assertEqual(filegen.extensionis('file.txt', 'txt'), True)
        self.assertEqual(filegen.extensionis('file.txt', '.txt'), True)
        self.assertEqual(filegen.extensionis('file.txt', '.xtx'), False)


if __name__ == "__main__":
    unittest.main()
