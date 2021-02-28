import unittest

from dmgen import pygamegen as pg


class FilegenTest(unittest.TestCase):
    def test_avg_surf(self):
        surf = pg.pygame.Surface((100, 100))
        surf.fill((255, 127, 0))
        self.assertEqual(pg.avg_surf(surf), (255, 127, 0))
        self.assertEqual(pg.avg_surf(surf), pg.avg_surf_less_mem(surf))

    def test_invert(self):
        surf = pg.pygame.Surface((100, 100))
        surf.fill((255, 127, 0))
        self.assertEqual(pg.avg_surf(pg.invert(surf)), (0, 128, 255))


if __name__ == "__main__":
    unittest.main()
