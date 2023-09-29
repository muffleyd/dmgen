import os
import sys
import pygame
from . import filegen
from . import jpegtran
from . import pygamegen as pg
from . import threaded_worker
from .cores import CORES


def relpath(filename):
    try:
        return os.path.relpath(filename)
    except ValueError:  # other drive
        return os.path.abspath(filename)


def mod_image(image, rect, mod):
    image = pygame.transform.smoothscale(image, (
        int(image.get_width() * mod),
        int(image.get_height() * mod))
    )
    if rect is None:
        rect = image.get_rect()
    else:
        rect = mod_rect(rect, mod)
    return image, rect


def mod_rect(rect, mod):
    return pygame.Rect(round(rect.x * mod),
                       round(rect.y * mod),
                       round(rect.width * mod),
                       round(rect.height * mod))


def unmod_rect(rect, mod):
    return pygame.Rect(round(rect.x / mod),
                       round(rect.y / mod),
                       round(rect.width / mod),
                       round(rect.height / mod))


class jpeg:
    def __init__(self, filename, action=None, targetname=None, *attrs):
        self.filename = filename
        self.relname = relpath(filename)
        self.image = pygame.image.load(filename)
        self.drawrect = self.image.get_rect()
        self.mod = 0

        self.targetname = targetname
        if action:
            getattr(self, action)(*attrs)

    def set_mod(self, mod):
        if mod != self.mod:
            self.mod = mod
            self.modimage, self.moddrawrect = mod_image(self.image, self.drawrect, mod)

    def redraw(self, flip=True):
        self.screen.fill((0, 0, 0))
        self.screen.blit(self.modimage, self.moddrawrect)
        if flip:
            pygame.display.flip()

    def checkpoint(self, point):
        point0, point1 = point
        if point[0] > self.modimage.get_width():
            point0 = self.modimage.get_width()
        if point[1] > self.modimage.get_height():
            point1 = self.modimage.get_height()
        return point0, point1

    def crop(self):
        if not self.mod:
            self.set_mod(1)
        self.screen = screen = pg.view_pic(self.image)  # , fitto=(1280, 1000))
        try:
            self.black = pygame.Surface(screen.get_size()).convert_alpha()
            self.black.fill((0, 0, 0, 177))
            while 1:
                pygame.display.set_caption(self.relname)
                self.redraw()
                point1 = point2 = None
                while 1:
                    thing = None
                    click = pg.wait_for_input([1, 0, 1, 1, 1],
                                              [pygame.K_UP,
                                               pygame.K_DOWN,
                                               pygame.K_LEFT,
                                               pygame.K_RIGHT,
                                               pygame.K_ESCAPE])
                    if click[0] == pygame.QUIT or click[1] == pygame.K_ESCAPE:
                        return pygame.QUIT
                    click = click[1]
                    pygame.event.pump()
                    if pygame.key.get_pressed()[pygame.K_LSHIFT]:
                        modchange = 1.18
                    elif pygame.key.get_pressed()[pygame.K_LCTRL]:
                        modchange = 1.01
                    else:
                        modchange = 1.03
                    if click == 5:
                        # zoom out
                        self.set_mod(self.mod / modchange)
                        self.redraw()
                    elif click == 4:
                        # zoom in
                        if self.mod < 1:
                            mod = self.mod * modchange
                            if mod > 1:
                                mod = 1
                            self.set_mod(mod)
                            self.redraw()
                    elif click == 3:
                        if point2 is not None:
                            point2 = None
                        elif point1 is not None:
                            point1 = None
                        else:
                            return
                    elif click == 1:
                        if point1 is None:
                            point1 = self.checkpoint(pygame.mouse.get_pos())
                        elif point2 is None:
                            point2 = self.checkpoint(pygame.mouse.get_pos())
                        else:
                            # move on to the next part
                            break
                    elif click == pygame.K_UP:
                        thing = (0, 0)
                    elif click == pygame.K_LEFT:
                        thing = (0, self.modimage.get_height())
                    elif click == pygame.K_DOWN:
                        thing = (self.modimage.get_width(),
                                 self.modimage.get_height())
                    elif click == pygame.K_RIGHT:
                        thing = (self.modimage.get_width(), 0)
                    if thing is not None:
                        if point1 is None:
                            point1 = thing
                        elif point2 is None:
                            point2 = thing

                    pygame.display.set_caption('%s  %s  %s' % (self.relname, str(point1), str(point2)))
                # modify points based on zoom
                self.rect = rect = pygame.Rect(point1, (0, 0))
                if point1[0] < point2[0]:
                    rect.width = point2[0] - point1[0]
                else:
                    rect.left = point2[0]
                    rect.width = point1[0] - point2[0]
                if point1[1] < point2[1]:
                    rect.height = point2[1] - point1[1]
                else:
                    rect.top = point2[1]
                    rect.height = point1[1] - point2[1]
                self.check()
                while 1:
                    do = False
                    press = pg.wait_for_input([1, 0, 1],
                                              [pygame.K_UP,
                                               pygame.K_DOWN,
                                               pygame.K_LEFT,
                                               pygame.K_RIGHT,
                                               pygame.K_RETURN])
                    if press[0] in (pygame.KEYDOWN, pygame.KEYUP):
                        key = press[1]
                        if key == pygame.K_RETURN:
                            print('saving to', self.targetname or self.filename)
                            jpegtran.do2(self.filename, self.targetname, crop_option(unmod_rect(self.rect, self.mod)))
                            r = unmod_rect(self.rect, self.mod)
                            return (r.x, r.y, r.right - self.image.get_width(), r.bottom - self.image.get_height())
                        elif key == pygame.K_UP:
                            if self.rect.y > 0:
                                self.rect.y -= 1
                                do = True
                        elif key == pygame.K_DOWN:
                            if self.rect.bottom < self.modimage.get_height():
                                self.rect.y += 1
                                do = True
                        elif key == pygame.K_LEFT:
                            if self.rect.x > 0:
                                self.rect.x -= 1
                                do = True
                        elif key == pygame.K_RIGHT:
                            if self.rect.right < self.modimage.get_width():
                                self.rect.x += 1
                                do = True
                        # screen.blit(self.image, self.image.get_rect())
                        if do:
                            self.redraw(False)
                            self.check()
                    else:
                        break
        finally:
            pygame.quit()

    def check(self):
        pygame.display.set_caption('%s  %s' % (self.relname, str(self.rect)))
        self.modrect = unmod_rect(self.rect, self.mod)
        tempfilename = filegen.unused_filename(os.path.split(self.filename)[1],
                                               folder=filegen.TEMPfolder)
        print(tempfilename, end=' ')
        print(jpegtran.jpeg(self.filename, tempfilename, crop_option(self.modrect), False)[1])
        try:
            tempjpeg = pg.load_image(tempfilename)
        finally:
            if os.path.exists(tempfilename):
                os.remove(tempfilename)
        # bottomright is always correct, use it as the anchor
        modtempjpeg, rect = mod_image(tempjpeg, None, self.mod)
        rect.bottomright = self.rect.bottomright
        # make cropped bit stand out
        self.screen.blit(self.black, self.black.get_rect())
        self.screen.blit(modtempjpeg, rect)
        pygame.display.flip()

    def crop_auto(self, x1=None, y1=None, x2=None, y2=None, jpgtw=None):
        if x1 is None and y1 is None and x2 is None and y2 is None:
            # click it in once, then use those values
            return self.crop()
        elif x1 is None or y1 is None or x2 is None or y2 is None:
            raise ValueError('Either enter all 4 values, or 0')
        else:
            # if tw:
            # return (tw, tw.put(x1, y1, x2, y2, jpgtw, func=self._crop_auto))
            # else:
            return self._crop_auto(x1, y1, x2, y2, jpgtw)

    def _crop_auto(self, x1, y1, x2, y2, tw=None):
        _x2 = x2
        _y2 = y2
        if x2 <= 0:
            _x2 = self.drawrect.width + x2 - x1
        if y2 <= 0:
            _y2 = self.drawrect.height + y2 - y1
        r = pygame.Rect(x1, y1, _x2, _y2)
        jpegtran.do2(self.filename, self.targetname, crop_option(r), tw)
        return x1, y1, x2, y2


def crop_option(rect):
    f = '-crop %dx%d+%d+%d' % (rect.width, rect.height, rect.x, rect.y)
    # print f
    return f


def crop_many(targets, x1=None, y1=None, x2=None, y2=None, recurse=False):
    if not hasattr(targets, '__iter__'):
        targets = [targets]
    print(targets)
    more = []
    for target in targets:
        if os.path.isfile(target):
            iterover = [target]
        else:
            if recurse:
                iterover = (os.path.join(i[0], j) for i in os.walk(target) for j in i[2]
                            if os.path.splitext(j)[1].lower() in ('.jpg', '.jpeg') or
                            open(os.path.join(i[0], j), 'rb').read(2) == '\xff\xd8')
            else:
                iterover = (
                    os.path.join(target, i)
                    for i in os.listdir(target)
                    if os.path.isfile(os.path.join(target, i)) and (
                        os.path.splitext(i)[1].lower() in ('.jpg', '.jpeg') or
                        open(os.path.join(target, i), 'rb').read(2) == '\xff\xd8'
                    )
                )
        with threaded_worker.threaded_worker(None, 1) as tw:
            with threaded_worker.threaded_worker(None, CORES) as jpgtw:
                ran = []
                while 1:
                    for filename in iterover:
                        # print filename,
                        ret = tw.put(func=lambda: jpeg(filename).crop_auto(x1, y1, x2, y2, jpgtw))
                        # ret = jpeg(filename).crop_auto(x1, y1, x2, y2, jpgtw)
                        # print tw,jpgtw
                        if x1 is None:
                            ret = tw.get(ret)
                            if ret is pygame.QUIT:
                                more[:] = []
                                break
                            elif ret is None:
                                more.append(filename)
                                continue
                            elif hasattr(ret, '__iter__'):
                                x1, y1, x2, y2 = ret
                        else:
                            ran.append((filename, ret))

                    if more:
                        iterover = more[:]
                        more[:] = []
                    else:
                        break
                # print 'out'
                for filename, i in ran:
                    print(filename)
                    _ = tw.get(i)  # confirm no errors


if __name__ == '__main__':
    wait = True
    try:
        if not os.path.isfile(sys.argv[1]) and os.path.exists(sys.argv[1]):
            recurse = '-r' in sys.argv
            if recurse:
                sys.argv.remove('-r')
            vals = []
            if '--dims' in sys.argv:
                vals[:] = sys.argv[sys.argv.index('--dims') + 1:]
                sys.argv = sys.argv[:sys.argv.index('--dims')]
            while len(vals) < 4:
                vals.append(None)
            x1, y1, x2, y2 = vals
            crop_many(sys.argv[1:], x2, y1, x2, y2, recurse)
        else:
            jpeg(sys.argv[1], 'crop', len(sys.argv) > 2 and sys.argv[2] or None)
    except Exception:
        if wait:
            import traceback

            traceback.print_exc()
            input('error')
        raise
