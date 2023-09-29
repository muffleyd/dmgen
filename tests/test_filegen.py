import unittest
from unittest.mock import patch
from mock_scandir import DirEntry
import os

from dmgen import filegen


class FilegenTest(unittest.TestCase):
    def test_extensionis(self):
        self.assertEqual(filegen.extensionis('file.txt', 'txt'), True)
        self.assertEqual(filegen.extensionis('file.txt', '.txt'), True)
        self.assertEqual(filegen.extensionis('file.txt', '.xtx'), False)

    def test__files_in_scandir(self):
        structure = [
            DirEntry(os.path.join('.', 'file1.jpg')),
            DirEntry(os.path.join('.', 'file2.jpg')),
            DirEntry(os.path.join('.', 'file3.png')),
        ]
        with patch('os.scandir', lambda _: structure):
            self.assertEqual(
                structure,
                list(filegen._files_in_scandir('.', '', set(), set())),
            )
        with patch('os.scandir', lambda _: structure):
            self.assertEqual(
                structure[0:2],
                list(filegen._files_in_scandir('.', '', set(['.jpg']), set())),
            )


if __name__ == "__main__":
    unittest.main()
