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
            yield desired_options

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
            for c in (0, 3):
                with self.mock_pygamegen__colors_in({'c': c, 'd': d}) as result:
                    self.assertEqual(
                        result,
                        pngout.get_colors_options(filename),
                    )
        for c in (2, 4, 6):
            with self.mock_pygamegen__colors_in({'c': c}) as result:
                self.assertEqual(
                    result,
                    pngout.get_colors_options(filename),
                )

        # Test grey+alpha with more than 256 rgba values.
        colors = set((i, i, i, 100) for i in range(256))
        colors.update(set((i, i, i, 200) for i in range(256)))
        with patch(
            'dmgen.pngout.pygamegen._colors_in',
            lambda x, y=False: colors
        ):
            self.assertEqual(
                {'c': 4},
                pngout.get_colors_options(filename)
            )

        # Test fewer than 256 rgb values but more than 256 rgba values.
        colors = generate_colors(100, False, True)
        with patch(
            'dmgen.pngout.pygamegen._colors_in',
            lambda x, y=False: colors
        ):
            self.assertEqual(
                {'c': 3, 'd': 8},
                pngout.get_colors_options(filename)
            )
        # Add additional alpha values but reuse rgb values.
        original_colors = list(colors)
        for index, result in enumerate((
            {'c': 3, 'd': 8},
            {'c': 6},
        )):
            for r, g, b, a in original_colors:
                colors.add((r, g, b, (a + 1 + index) % 256))
            with patch(
                'dmgen.pngout.pygamegen._colors_in',
                lambda x, y=False: colors
            ):
                self.assertEqual(pngout.pygamegen._colors_in(filename), colors)
                self.assertEqual(
                    result,
                    pngout.get_colors_options(filename)
                )

    def test_round_up_slash_d(self):
        for value, result in (
            (0, 0),
            (1, 1),
            (2, 2),
            (3, 4),
            (4, 4),
            (5, 8),
            (6, 8),
            (7, 8),
            (8, 8),
        ):
            self.assertEqual(result, pngout.round_up_slash_d(value))

def mock_pygamegen__colors_in(desired_options):
    if not desired_options:
        return {}
    if 'c' not in desired_options:
        raise ValueError(desired_options)
    c_option = desired_options['c']
    if c_option not in (0, 2, 3, 4, 6):
        raise ValueError(desired_options)
    if 'd' in desired_options:
        if c_option not in (0, 3):
            raise ValueError(desired_options)
        if desired_options['d'] not in (0, 1, 2, 4, 8):
            raise ValueError(desired_options)
        bits = desired_options['d']
        min_bits = bits // 2
    elif c_option == 4:
        min_bits = 0
        bits = 8
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
            (r, g, b, int(random.random() * 256)) for r, g, b, _ in colors
        )
    return colors


def add_color(colors, grey):
    result = None
    while result in colors or not result:
        r = g = b = int(random.random() * 256)
        if not grey:
            while r == g == b:
                g = int(random.random() * 256)
                b = int(random.random() * 256)
        # Alpha is handled elsewhere so /c4 doesn't get the wrong number of unique grey rgb combinations.
        a = 255
        result = (r, g, b, a)
    colors.add(result)
    return colors


if __name__ == "__main__":
    unittest.main(buffer=True)
