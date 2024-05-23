import unittest
from unittest.mock import patch

import os
import shutil
import random
from dmgen import filegen
from dmgen.tests.mock_scandir import DirEntry


class FilegenTest(unittest.TestCase):

    maxDiff = None
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

    def test_get_duplicate_files(self):
        testing_dir = filegen.unused_filename(start='test_directory_', folder=os.path.split(__file__)[0])
        try:
            os.mkdir(testing_dir)
            one_dir = os.path.join(testing_dir, 'one')
            two_dir = os.path.join(testing_dir, 'two')
            os.mkdir(one_dir)
            os.mkdir(two_dir)
            sizes = list(range(2048, 2048 + 1024 + 1))
            random.shuffle(sizes)
            same = []
            # Ten duplicate files.
            for i in range(10):
                size = sizes.pop()
                file_one = os.path.join(one_dir, f'{i}_same.txt')
                file_two = os.path.join(two_dir, f'{i}_same.txt')
                content = 'a' * size
                with open(file_one, 'w') as f:
                    f.write(content)
                with open(file_two, 'w') as f:
                    f.write(content)
                same.append((
                    os.path.abspath(file_one),
                    os.path.abspath(file_two),
                ))
            # Five different files in each directory.
            for i in range(2):
                directory = i and one_dir or two_dir
                for j in range(5):
                    size = sizes.pop()
                    with open(os.path.join(directory, f'{j}_diff.txt'), 'w') as f:
                        f.write('a' * size)
            # A single file's contents appearing in each directory three times.
            size = sizes.pop()
            files_one = []
            files_two = []
            for i in range(3):
                files_one.append(os.path.join(one_dir, f'{i}_triple.txt'))
                files_two.append(os.path.join(two_dir, f'{i}_triple.txt'))
                content = 'a' * size
                with open(files_one[-1], 'w') as f:
                    f.write(content)
                with open(files_two[-1], 'w') as f:
                    f.write(content)
            same.extend(((x, y) for x in files_one for y in files_two))
            same.sort()
            # Assertions.
            self.assertEqual(same, sorted(filegen.get_same_as_many_files(one_dir, two_dir)))
            self.assertEqual(same, sorted(filegen.get_same_as_many_files2(one_dir, two_dir)))
        finally:
            if os.path.exists(testing_dir):
                shutil.rmtree(testing_dir)

if __name__ == "__main__":
    unittest.main()
