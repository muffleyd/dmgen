import os, sys
import pygame
from dmgen import filegen

def main(filenames):
    exitcode = 0
    for filename in filenames:
        if filename[-4:].lower() == '.png': #try recompress
            PNG = True
        else:
            PNG = False
        if PNG:
            tofilename = filegen.unused_filename('.png', folder=filegen.TEMPfolder)
        else:
            tofilename = os.path.splitext(filename)[0]+'.png'
        try:
            l = pygame.image.load(filename)
        except pygame.error:
            return 2
        pygame.image.save(l, tofilename)
        if PNG:
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
