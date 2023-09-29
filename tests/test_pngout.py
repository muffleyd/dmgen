import unittest

from dmgen import pngout


class PngoutTest(unittest.TestCase):
    def test_pngout_build_command(self):
        PREFIX = pngout.PREFIX
        PNGOUT_EXE_PATH = pngout.PNGOUT_EXE_PATH = 'pngout'
        self.assertEqual(
            f'{PREFIX} {PNGOUT_EXE_PATH}  "filename.png"  /y',
            pngout.pngout_build_command('filename.png', None, ''),
        )

        self.assertEqual(
            f'{PREFIX} {PNGOUT_EXE_PATH}  "filename.png" "outfile.png" /y',
            pngout.pngout_build_command('filename.png', 'outfile.png', ''),
        )

        self.assertEqual(
            f'{PREFIX} {PNGOUT_EXE_PATH} /b512 /f0 "filename.png" "outfile.png" /y',
            pngout.pngout_build_command('filename.png', 'outfile.png', '/b512 /f0'),
        )


if __name__ == "__main__":
    unittest.main()
