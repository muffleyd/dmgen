import unittest
from unittest.mock import patch, Mock

import random
from contextlib import contextmanager

from dmgen import pngout


class PngoutTest(unittest.TestCase):
    def test_pngout_build_command(self):
        PREFIX = pngout.PREFIX
        PNGOUT_EXE_PATH = pngout.PNGOUT_EXE_PATH = 'pngout'
        self.assertEqual(
            f'{PREFIX} {PNGOUT_EXE_PATH}  "filename.png"  /y /v',
            pngout.pngout_build_command('filename.png', None, ''),
        )

        self.assertEqual(
            f'{PREFIX} {PNGOUT_EXE_PATH}  "filename.png" "outfile.png" /y /v',
            pngout.pngout_build_command('filename.png', 'outfile.png', ''),
        )

        self.assertEqual(
            f'{PREFIX} {PNGOUT_EXE_PATH} /b512 /f0 "filename.png" "outfile.png" /y /v',
            pngout.pngout_build_command('filename.png', 'outfile.png', '/b512 /f0'),
        )

    @contextmanager
    def mock_pygamegen__colors_in(self, desired_options):
        with patch(
            'dmgen.pngout.pygamegen._colors_in',
            lambda x, y: mock_pygamegen__colors_in(desired_options)
        ):
            yield None

    def test_get_colors_options(self):
        filename = 'filename.png'

        with patch('dmgen.pngout.pygamegen', None):
            self.assertEqual(
                {},
                pngout.get_colors_options(filename),
            )
        with patch('dmgen.pngout.pygamegen._colors_in', Mock(side_effect=Exception('Expected mock Exception.'))):
            self.assertEqual(
                {},
                pngout.get_colors_options(filename),
            )

        for d in (0, 1, 2, 4, 8):
            # TODO help text says /d may only values for /c0 or /c3, not /c4.
            for c in (0, 3, 4):
                result = {'c': c, 'd': d}
                with self.mock_pygamegen__colors_in(result):
                    self.assertEqual(
                        result,
                        pngout.get_colors_options(filename),
                    )
        for c in (2, 6):
            result = {'c': c}
            with self.mock_pygamegen__colors_in(result):
                self.assertEqual(
                    result,
                    pngout.get_colors_options(filename),
                )


def mock_pygamegen__colors_in(desired_options):
    if not desired_options:
        return {}
    if 'c' not in desired_options:
        raise ValueError(desired_options)
    c_option = desired_options['c']
    if c_option not in (0, 2, 3, 4, 6):
        raise ValueError(desired_options)
    if 'd' in desired_options:
        if c_option not in (0, 3, 4):
            raise ValueError(desired_options)
        if desired_options['d'] not in (0, 1, 2, 4, 8):
            raise ValueError(desired_options)
        bits = desired_options['d']
        # TODO Minimum possible should be (bits // 2 + 1).
        min_bits = max(1, bits) - 1
    # elif c_option == 4:
    #     bits = 8
    elif c_option in (2, 6):
        min_bits = 8
        bits = 17  # TODO up to 24.
    grey = c_option % 4 == 0
    alpha = c_option & 4
    max_color_count = 2**bits
    min_color_count = (max_color_count == 1 and 1 or (2**min_bits + 1))
    color_count = random.randrange(min_color_count, max_color_count + 1)
    return generate_colors(color_count, grey, alpha)


def generate_colors(color_count, grey, alpha):
    colors = set()
    for _ in range(color_count):
        add_color(colors, grey)
    if alpha:
        colors = set(
            (r, g, b, random.randrange(256)) for r, g, b, _ in colors
        )
    return colors


def add_color(colors, grey):
    result = None
    while result in colors or not result:
        r = random.randrange(256)
        if grey:
            g = b = r
        else:
            g = random.randrange(256)
            b = random.randrange(256)
        # Alpha is handled elsewhere so /c4 doesn't get the wrong number of unique grey rgb combinations.
        a = 255
        result = (r, g, b, a)
    colors.add(result)
    return colors


if __name__ == "__main__":
    unittest.main()
