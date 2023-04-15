import os
import sys
import pygame
from dmgen import filegen


def main(filenames):
    exitcode = 0
    for filename in filenames:
        is_png = filename[-4:].lower() == '.png'  # try recompress
        if is_png:
            tofilename = filegen.unused_filename('.png', folder=filegen.TEMPfolder)
        else:
            tofilename = os.path.splitext(filename)[0] + '.png'
        try:
            image = pygame.image.load(filename)
        except pygame.error:
            return 2
        pygame.image.save(image, tofilename)
        if is_png:
            if os.stat(tofilename)[6] < os.stat(filename)[6]:
                os.remove(filename)
                os.rename(tofilename, filename)
            else:
                os.remove(tofilename)
                exitcode = 1
        else:
            os.remove(filename)
    return exitcode


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
