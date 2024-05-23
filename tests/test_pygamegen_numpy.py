import unittest

from dmgen import pygamegen as pg
try:
    import numpy
    import pygame.surfarray
except ImportError:
    numpy = None

class PygamegenNumpyTest(unittest.TestCase):
    def test_invert(self):
        if not numpy:
            self.skipTest('numpy not installed')
        surf = pg.pygame.Surface((100, 100))
        surf.fill((255, 127, 0))
        self.assertEqual(pg.avg_surf(pg.invert_numpy(surf)), (0, 128, 255))
        surf.fill((0, 127, 0))
        self.assertEqual(pg.avg_surf(pg.invert_numpy(surf)), (255, 128, 255))
