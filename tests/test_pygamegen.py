import unittest

from dmgen import pygamegen as pg


class FilegenTest(unittest.TestCase):
    def test_avg_surf(self):
        surf = pg.pygame.Surface((100, 100))
        surf.fill((255, 127, 0))
        self.assertEqual(pg.avg_surf(surf), (255, 127, 0))

    def test_invert(self):
        surf = pg.pygame.Surface((100, 100))
        surf.fill((255, 127, 0))
        self.assertEqual(pg.avg_surf(pg.invert(surf)), (0, 128, 255))

    def test_mk_bw(self):
        surf = pg.pygame.Surface((100, 100))
        surf.fill((255, 127, 0))
        self.assertEqual(pg.mk_bw(surf).get_at((0, 0))[:3], (127, 127, 127))
        surf.fill((128, 0, 255))
        self.assertEqual(pg.mk_bw(surf).get_at((0, 0))[:3], (128, 128, 128))


if __name__ == "__main__":
    unittest.main()
