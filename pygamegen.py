import random
import os
import threading
import time
import struct
import array
import contextlib
from io import StringIO

import pygame

from . import webgen

try:
    from . import screen
except ImportError:
    screen = None


try:
    import pygame.surfarray
    import numpy
except ImportError:
    pygame.surfarray = None
    numpy = None


def mk_rect(point1, point2):
    rect = pygame.Rect(point1, (0, 0))
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
    return rect


# def scroll_img(img, maxsize):
#    if not isinstance(img, pygame.SurfaceType):
#        img = pygame.image.load(img)
#    s = pygame.display.set_mode((min(img.get_width(), maxsize[0]),
#                                 min(img.get_height(), maxsize[1])))
#    s.blit(img,img.get_rect())
#    while 1:
#        for e in pygame.event.get():
#            if

def _levels_perc(rgba, perc):
    r, g, b, a = rgba
    return (int(round(r * perc)),
            int(round(g * perc)),
            int(round(b * perc)),
            a)


def _levels_sqrt(rgba, pwr=.5):
    r, g, b, a = rgba
    _, avg = _levels_prep(rgba)
    mod = ((avg ** pwr) / (avg or 1)) or 1
    # if mod != 1:
    #     print(rgba, mod)
    return (int(round(r * mod)),
            int(round(g * mod)),
            int(round(b * mod)),
            a)


def _levels_prep(rgba):
    r, g, b, _ = rgba
    return max(r, g, b), (r + g + b) // 3


# Alter image by some function (see _levels_*() above).
def levels(image, level, *args, **kwargs):
    if isinstance(image, str):
        image = pygame.image.load(image)
    else:
        image = image.copy()
    for i in iter_surf(image):
        rgba = image.get_at(i)
        newrgba = level(rgba, *args, **kwargs)
        # image.fill(newrgba, (i, (1,1)))
        image.set_at(i, newrgba)
        # if image.get_at(i) != rgba:
        #     print i, rgba, image.get_at(i)
    return image


def replace_color(image, color1, color2, empty=False):
    color1 = tuple(color1)
    if empty:
        image2 = pygame.Surface(image.get_size())
    else:
        image2 = image.copy()
    for x, y in iter_surf(image):
        if image.get_at((x, y))[:len(color1)] == color1:
            image2.fill(color2, (x, y, 1, 1))
    return image2


def mk_bw(pic):
    if isinstance(pic, str):
        pic = pygame.image.load(pic)
    new_bytes = bytearray(pic.get_width() * pic.get_height())
    iterpic = iter(pygame.image.tostring(pic, 'RGB'))
    iterpic_next = iterpic.__next__
    for index, p in enumerate(iterpic):
        rgb = p + iterpic_next() + iterpic_next()
        # round() is too slow.
        if rgb % 3 == 2:
            rgb += 1
        new_bytes[index] = rgb // 3
    new = pygame.image.frombuffer(new_bytes, pic.get_size(), 'P')
    try:
        new.set_palette([(i, i, i) for i in range(256)])
    except pygame.error:
        pygame.display.set_mode((1, 1))
        try:
            new.set_palette([(i, i, i) for i in range(256)])
        finally:
            pygame.display.quit()
    return new


def fit_to(image, dims=(1920, 1080)):
    width, height = image.get_size()
    mod_width = dims[0] / width
    mod_height = dims[1] / height
    if mod_width < mod_height:
        if mod_width > 1:
            return image
        final_width = dims[0]
        final_height = height * mod_width
    else:
        if mod_height > 1:
            return image
        final_width = width * mod_height
        final_height = dims[1]
    return pygame.transform.smoothscale(image, (int(final_width), int(final_height)))


def get_at_mouse():
    pygame.event.pump()
    return pygame.display.get_surface().get_at(pygame.mouse.get_pos())


def get_at_mouse_until_click():
    while 1:
        time.sleep(.05)
        color = get_at_mouse()
        pygame.display.set_caption(f'{pygame.mouse.get_pos()}: {color}')
        if pygame.mouse.get_pressed()[0]:
            break


def invert(surf):
    if isinstance(surf, str):
        surf = pygame.image.load(surf)
    string = pygame.image.tostring(surf, "RGBA")
    newstring = bytearray(string)
    for index in range(0, len(string), 4):
        # Invert RGB, not A.
        for color_index in range(index, index + 3):
            newstring[color_index] = 255 - string[color_index]
    return pygame.image.frombuffer(bytes(newstring), surf.get_size(), 'RGBA')


def invert_numpy(surf):
    if not numpy or not pygame.surfarray:
        raise Exception('numpy not installed')
    if isinstance(surf, str):
        surf = pygame.image.load(surf)
    else:
        surf = surf.copy()
    array = pygame.surfarray.pixels3d(surf)
    array[:] = 255 - array
    del array
    return surf


def avg_surf(surface):
    img_bytes = pygame.image.tostring(surface, 'RGB')
    size = len(img_bytes) // 3
    return tuple(sum(img_bytes[color::3]) // size for color in range(3))


def iter_surf(surface):
    for x in range(surface.get_width()):
        for y in range(surface.get_height()):
            yield x, y


def iter_surf_pieces(surface, pieces=1):
    for i in range(pieces):
        for x in range(surface.get_width() // pieces * i,
                       surface.get_width() // pieces * (i + 1)):
            for j in range(pieces):
                for y in range(surface.get_height() // pieces * j,
                               surface.get_height() // pieces * (j + 1)):
                    yield x, y, i + j


def resize_image(filename):
    from . import gen
    made_window = False
    try:
        if not pygame.display.get_init():
            pygame.init()
        pygame.display.set_mode((1, 1))
        pic = pygame.image.load(filename).convert_alpha()
        curdims = list(pic.get_size())
        while 1:
            newdims = curdims[:]
            view_pic(pic)
            choice = gen.menu(f'cur dims: {curdims}',
                              'width,, height,, percent', numbers=1)
            val = ''
            while not val:
                val = input('number: ')
            val = float(val)
            if choice in (1, 2):
                val = int(round(val))
                if choice == 1:
                    newdims[0] = val
                    newdims[1] = int(curdims[1] * (val / curdims[0]))
                else:
                    newdims[1] = val
                    newdims[0] = int(curdims[0] * (val / curdims[1]))
            else:  # percent
                newdims[0] = int(newdims[0] * val)
                newdims[1] = int(newdims[1] * val)
            view_pic(pygame.transform.smoothscale(pic, newdims))
            made_window = True
            print(newdims)
            while 1:
                if input('accept? ').lower() in ('y', 'yes'):
                    nfilename = input('filename: ')
                    if nfilename == '':  # overwrite
                        if input('are you sure you want to overwrite? ').lower() not in ('y', 'yes'):
                            continue
                    elif nfilename == '*':  # generate name
                        filename = os.path.splitext(filename)
                        i = 1
                        while 1:
                            _filename = filename[0] + str(i) + filename[1]
                            if not os.path.exists(_filename):
                                filename = _filename
                                break
                            i += 1
                    else:
                        filename = nfilename
                    pygame.image.save(pygame.transform.smoothscale(pic, newdims),
                                      filename)
                    return
                break
    finally:
        if made_window:
            pygame.display.quit()


def set_alpha(image, *colors):
    colors = set(i[:3] for i in colors)
    for i in range(image.get_width()):
        for j in range(image.get_height()):
            c0, c1, c2 = image.get_at((i, j))[:3]
            if (c0, c1, c2) in colors:
                image.set_at((i, j), (c0, c1, c2, 0))


def aacircle(surface, color, pos, radius, width=0, mod=4):
    if surface is None:
        surface = pygame.Surface((radius * 2, radius * 2))
    else:
        surface = surface
    surf = pygame.Surface((surface.get_width() * mod, surface.get_height() * mod))
    pygame.draw.circle(surf, color, (surf.get_width() // 2, surf.get_height() // 2),
                       radius * mod, width * mod)
    surf = pygame.transform.smoothscale(surf, surface.get_size())
    # surf = pygame.transform.rotozoom(surf, 0, 1./mod)
    surface.blit(surf, (pos[0] - radius, pos[1] - radius, radius * 2, radius * 2))
    return surface


def str_getat(string, dims):
    pass


def img_diff(one, two, empty=(0, 130, 0), alpha=False):
    """
    Returns the difference between two images of the same size by covering the parts
    of the images in the color `empty`.
    """
    # Allow strings, expect them to be files
    if isinstance(one, str):
        one = pygame.image.load(one)
    if isinstance(two, str):
        two = pygame.image.load(two)
    size = one.get_size()
    # Make sure they're the same size
    assert size == two.get_size()
    if alpha:
        image_format = 'RGBA'
        bytes_per_pixel = 4
    else:
        image_format = 'RGB'
        bytes_per_pixel = 3
    # Add the alpha color to empty if not provided
    if alpha and len(empty) == 3:
        empty = (*empty, 255)
    pixels = size[0] * size[1]
    # Create an empty bytearray the size of the images
    new_one = bytearray(empty * pixels)
    new_two = new_one[:]
    one_string = pygame.image.tostring(one, image_format)
    two_string = pygame.image.tostring(two, image_format)
    # Check each pixel (RGBA = 4 bytes per pixel)
    for xy in range(0, pixels * bytes_per_pixel, bytes_per_pixel):
        # Get the endpoint of the array slice
        xy_plus = xy + bytes_per_pixel
        first_rgba = one_string[xy:xy_plus]
        second_rgba = two_string[xy:xy_plus]
        # If they're not the same, put the pixel onto the final image
        if first_rgba != second_rgba:
            new_one[xy:xy_plus] = first_rgba
            new_two[xy:xy_plus] = second_rgba
    return (pygame.image.frombuffer(new_one, size, image_format),
            pygame.image.frombuffer(new_two, size, image_format))


def img_diff_numpy(one, two, empty=(0, 130, 0), alpha=False):
    """
    Returns the difference between two images of the same size by covering the parts
    of the images in the color `empty`.
    """
    if not numpy or not pygame.surfarray:
        raise Exception('numpy not installed')
    # Allow strings, expect them to be files.
    if isinstance(one, str):
        one = pygame.image.load(one)
    if isinstance(two, str):
        two = pygame.image.load(two)
    assert one.get_size() == two.get_size()
    if alpha:
        # Convert the packed 32-bit integer into the 4-element array.
        # Can't use pixels2d because *_color.view() throws a non-contiguous axis error.
        one_color = pygame.surfarray.array2d(one)
        one_array = one_color.view(dtype=numpy.uint8).reshape((*one_color.shape[0:2], 4))
        two_color = pygame.surfarray.array2d(two)
        two_array = two_color.view(dtype=numpy.uint8).reshape((*two_color.shape[0:2], 4))
        if len(empty) == 3:
            empty = (*empty, 255)
    else:
        # pixels3d does what we need without the alpha, and edits in-place.
        one_array = pygame.surfarray.pixels3d(one)
        two_array = pygame.surfarray.pixels3d(two)

    # Create the filter based on if the RGB(A) values match completely.
    same_array = numpy.all(one_array == two_array, axis=2)
    one_array[same_array] = empty
    two_array[same_array] = empty

    if alpha:
        # Above, alpha comparisons are done with an array copy, not reference.
        # As such, recreate the surfaces from the modified arrays.
        # Trim it to the first 3 values of each pixel to not pass alpha.
        return (pygame.surfarray.make_surface(one_array[:,:,:3]),
                pygame.surfarray.make_surface(two_array[:,:,:3]))
    return one, two


def _colors_in(pic, includealpha=False):
    if isinstance(pic, str):
        pic = pygame.image.load(pic)
    if includealpha:
        format = 'RGBA'
    else:
        format = 'RGB'
    bytes = len(format)
    data = pygame.image.tostring(pic, format)
    return set(data[i:i + bytes] for i in range(0, len(data), bytes))


def num_colors_in(pic, includealpha=False):
    return len(_colors_in(pic, includealpha))


def colors_in(pic, includealpha=False):
    return [tuple(colors) for colors in _colors_in(pic, includealpha)]


def colors_info(pic, includealpha=False):
    if isinstance(pic, str):
        pic = pygame.image.load(pic)
    if includealpha:
        format = 'RGBA'
    else:
        format = 'RGB'
    mod = len(format)
    data = pygame.image.tostring(pic, format)
    color_lookup = {}
    ret = {}
    for i in range(0, len(data), mod):
        color = data[i:i + mod]
        mapped = color_lookup.get(color)
        if not mapped:
            mapped = tuple(color)
            color_lookup[color] = mapped
        # print color, mapped
        if mapped not in ret:
            ret[mapped] = 1
        else:
            ret[mapped] += 1
    # print color_lookup
    return ret


def remove_whitespace(pic, red=None, green=None, blue=None, defrange=10):
    RANGE = defrange
    topleft = pic.get_at((0, 0))
    if not red:
        red = topleft[0]
    if not green:
        green = topleft[1]
    if not blue:
        blue = topleft[2]
    if hasattr(red, '__len__'):
        red, rr = red
    else:
        rr = RANGE
    if hasattr(green, '__len__'):
        green, gr = green
    else:
        gr = RANGE
    if hasattr(blue, '__len__'):
        blue, br = blue
    else:
        br = RANGE

    def check(r, g, b, a):
        return (r - rr <= red <= r + rr and
                g - gr <= green <= g + gr and
                b - br <= blue <= b + br)

    for x in range(pic.get_width()):
        for y in range(pic.get_height()):
            if not check(*pic.get_at((x, y))):
                break
        else:
            continue
        left = x - 1
        break
    for x in range(pic.get_width() - 1, -1, -1):
        for y in range(pic.get_height()):
            if not check(*pic.get_at((x, y))):
                break
        else:
            continue
        right = x + 1
        break
    for y in range(pic.get_height()):
        for x in range(pic.get_width()):
            if not check(*pic.get_at((x, y))):
                break
        else:
            continue
        bottom = y - 1
    for y in range(pic.get_height() - 1, -1, -1):
        for x in range(pic.get_width()):
            if not check(*pic.get_at((x, y))):
                break
        else:
            continue
        top = y + 1

    rect = left, top, right - left, bottom - top
    new = pygame.Surface((rect[-2], rect[-1]))
    new.blit(pic, new.get_rect(), rect)
    return new


def wait_for_mouse(buttons=[1, 0, 1]):
    return wait_for_input(buttons, [])[1]


def wait_for_key(keys=[pygame.K_ESCAPE]):
    return wait_for_input([], keys)[1]


def wait_for_input(buttons=[1, 0, 1], keys=[pygame.K_ESCAPE], quit=True):
    return wait_for_input2(buttons, keys, False, quit)


def wait_for_input2(buttons=[1, 0, 1], keys=[pygame.K_ESCAPE], move=False, quit=True):
    pygame.event.clear()
    maxbutton = len(buttons)
    if not hasattr(buttons, '__iter__'):
        buttons = (buttons,)
    if not hasattr(keys, '__iter__'):
        keys = (keys,)
    while 1:
        e = pygame.event.wait()
        if e.type == pygame.KEYUP:
            if e.key in keys:
                return e.type, e.key
        elif e.type == pygame.MOUSEBUTTONUP:
            if e.button <= maxbutton and buttons[e.button - 1]:
                return e.type, e.button
        elif quit and e.type == pygame.QUIT:
            return e.type, 1
        elif move and e.type == pygame.MOUSEMOTION:
            return e.type, e


SCREEN = 'GET_SCREEN_DIMS'


def view_pic(pic, title=True, scale=1, back=(255, 125, 255), fitto=None):
    TITLE = None
    size = [0, 0]
    if not isinstance(title, bool):
        TITLE = title
    if not isinstance(pic, str) and hasattr(type(pic), '__iter__'):
        if isinstance(title, str):
            TITLE = title
        else:
            if not isinstance(title, str) and title:
                for i in pic:
                    if not isinstance(i, str):
                        title = False
            if title:
                joined_pic_titles = '", "'.join(pic)
                TITLE = f'"{joined_pic_titles}"'
        pic = [not isinstance(name, pygame.surface.SurfaceType) and
               pygame.image.load(name) or name for name in pic]
        # for i, name in enumerate(pic):
        #     if not isinstance(name, pygame.surface.SurfaceType):
        #         pic[i] = pygame.image.load(name)
        size[0] = sum(i.get_width() for i in pic) + len(pic) - 1
        size[1] = max(i.get_height() for i in pic)
        _surf = pygame.Surface(size)
        _surf.fill(back)
        width = 0
        for i in pic:
            _surf.blit(i, (width, 0, i.get_width(), i.get_height()))
            width += i.get_width() + 1
        image = _surf
    elif isinstance(pic, pygame.surface.SurfaceType):
        # pygame surface
        image = pic
        size = image.get_size()
    elif hasattr(pic, 'image'):
        # pygame sprite object
        image = pic.image
        size = image.get_size()
    else:  # string or fileobj
        if not TITLE and isinstance(pic, str):
            TITLE = pic
        try:
            image = pygame.image.load(pic)
        except:
            if 'http://' == pic[:7]:
                image = load_image_fromweb(pic)
            else:
                raise
        size = image.get_size()
    if (scale == 1 and fitto) or scale != 1:
        if not pygame.display.get_init():
            pygame.init()
        try:
            image = image.convert(32)
        except:
            pass
        if scale == 1 and fitto:
            if fitto is SCREEN:
                fitto = screen.main()
                fitto = (fitto[0], fitto[1] - 30)
            image = fit_to(image, fitto)
            size = image.get_size()
        elif scale != 1:
            size = (int(round(size[0] * scale)), int(round(size[1] * scale)))
            image = pygame.transform.smoothscale(image, size)
    # print pic,size, fitto
    display = pygame.display.set_mode(size)
    pygame.display.update(display.blit(image, image.get_rect()))
    # print title
    if TITLE:
        pygame.display.set_caption(str(TITLE))
    return display


def re_alpha_nemo(image):
    do_s = not pygame.display.get_surface()
    if do_s:
        pygame.display.set_mode((1, 1))
    a = pygame.image.load(image).convert_alpha()
    for x, y in iter_surf(a):
        if a.get_at((x, y))[:3] == (0, 130, 0):
            a.set_at((x, y), (0, 130, 0, 0))
    pygame.image.save(a, image)


class SimplestSprite(pygame.sprite.Sprite):
    _image = pygame.Surface((1, 1))

    def __init__(self, center=(0, 0)):
        pygame.sprite.Sprite.__init__(self)
        self.image = self._image
        self.rect = pygame.Rect(center, (1, 1))

    def __repr__(self):
        return f'<SimplestSprite: {self.rect}>'

    def __call__(self, pos):
        self.rect.center = pos
        return self


def rotate_right(image, times=1):
    return pygame.transform.rotate(image, (-90 * times))


def rotate_left(image, times=1):
    return pygame.transform.rotate(image, (90 * times))


def flip_vert(image):
    return pygame.transform.flip(image, 0, 1)


def flip_hori(image):
    return pygame.transform.flip(image, 1, 0)


def zoomed_of(image, amount, rect=None):
    rect = rect or image.get_rect()
    x, y = int(image.get_width() * amount), int(image.get_height() * amount)
    return pygame.transform.smoothscale(image.subsurface(rect), (x, y))


def _zoom_helper(surf, zoom, rect, zoom_method):
    x, y = int(surf.get_width() * zoom), int(surf.get_height() * zoom)
    s = zoom_method(surf, (x, y))
    # s = pygame.transform.rotozoom(surf, 0, zoom)
    newr = s.get_rect()
    newr.center = rect.center
    return s, newr


def zoom_around(zoom=2, method=pygame.transform.smoothscale):
    s = pygame.display.get_surface()
    rect = s.get_rect()
    pygame.event.clear()
    base_s = s.copy()
    s.fill((0, 0, 0))
    use_s, rect = _zoom_helper(base_s, zoom, rect, method)
    pygame.event.pump()
    rect.center = pygame.mouse.get_pos()
    color = ''
    # print rect
    s.blit(use_s, rect)
    pygame.display.flip()
    clock = pygame.time.Clock()
    try:
        while 1:
            clock.tick(60)
            event = pygame.event.wait()
            f = pygame.event.get()
            events = [event] + f
            zooms = [e for e in events if (e.type == pygame.MOUSEBUTTONDOWN and e.button in (4, 5))]
            if zooms:
                zmod = 0
                for e in zooms:
                    if e.button == 5:
                        zmod -= 1
                    else:
                        zmod += 1
                if zmod:
                    if zmod < 0:
                        for _ in range(-zmod):
                            zoom /= 1.1
                    else:
                        for _ in range(zmod):
                            zoom *= 1.1
                    pygame.display.set_caption(str(zoom) + ' ' + str(color))
                    s.fill((0, 0, 0), rect)
                    del use_s
                    use_s, rect = _zoom_helper(base_s, zoom, rect, method)
                    pygame.event.post(pygame.event.Event(
                        pygame.MOUSEMOTION,
                        {'buttons': [1, 0, 0],
                         'pos': pygame.mouse.get_pos(), 'rel': (0, 0),
                         'refill': False}
                    )
                    )

            for e in events:
                if e.type == pygame.MOUSEMOTION:
                    if 1 in e.buttons:
                        mod = 1
                        if e.buttons[1]:
                            mod = 4
                        elif e.buttons[2]:
                            mod = 2
                        # try:
                        #     e.refill
                        # except:
                        #     if zoom < 2:
                        #         s.fill((0, 0, 0), rect)
                        s.fill((0, 0, 0), rect)
                        # prev = pygame.Rect(rect)
                        rect.x += (e.rel[0] * mod)
                        rect.y += (e.rel[1] * mod)
                        s.blit(use_s, rect)
                        pygame.display.update()  # prev.union(rect))
                    else:
                        color = use_s.get_at((e.pos[0] - rect.x, e.pos[1] - rect.y))
                        pygame.display.set_caption(str(zoom) + ' ' + str(color))
                elif e.type == pygame.QUIT:
                    return
                elif e.type == pygame.KEYDOWN:
                    return
    finally:
        s.blit(base_s, s.get_rect())
        pygame.display.flip()


def fill_rand(s, pos, red=(220, 225), green=(None, None), blue=(None, None),
              hori=9, vert=9):
    randint = random.randint
    x, y = pos
    if green[0] is None:
        green[0] = red[0]
    if blue[0] is None:
        blue[0] = green[0]
    if green[1] is None:
        green[1] = red[1]
    if blue[1] is None:
        blue[1] = green[1]
    for i in range(x - (hori - 2), x + (hori - 1)):
        for j in range(y - (vert - 2), y + (hori - 1)):
            s.fill((randint(red[0], red[1]),
                    randint(green[0], green[1]),
                    randint(blue[0], blue[1])),
                   (i, j, 1, 1))
    pygame.display.update(x - 1, y - 1, hori, vert)


def random_(s, r=(255, 255), g=(0, 0), b=(0, 0)):
    pygame.event.pump()
    while not pygame.mouse.get_pressed()[2]:
        if pygame.mouse.get_pressed()[0]:
            fill_rand(s, pygame.mouse.get_pos(), r, g, b)
        pygame.event.pump()


update = pygame.display.update
flip = pygame.display.flip


def mkscreen(size=(640, 480), flags=0, depth=None, fill=(0, 0, 0),
             dobasichandler=False, waitbetween=0.5):
    return __mkscreen(size, flags, depth, fill, dobasichandler, waitbetween).screen


class __mkscreen:
    def __init__(self, size, flags, depth, fill, dobasichandler=False,
                 waitbetween=0.5):
        try:  # closes previous mkscreen calls, and windows
            pygame.quit()
        except:
            pass
        if dobasichandler:
            self.waitbetween = waitbetween
            self.lock = threading.Lock()
            self.background_basic_handler(size, flags, depth, fill)
        else:
            if depth is None:
                self.screen = pygame.display.set_mode(size, flags)
            else:
                self.screen = pygame.display.set_mode(size, flags, depth)
            self.screen.fill(fill)
            pygame.display.flip()

    def background_basic_handler(self, size, flags, depth, fill):
        try:
            pygame.quitdefault
        except AttributeError:
            pygame.quitdefault = pygame.quit
            pygame.quit = self.pygame_quit2
        self.lock.acquire()
        t = threading.Thread(target=self._gen_handler, args=(size, flags, depth, fill), daemon=True)
        t.start()
        self.lock.acquire()
        self.lock.release()

    def _gen_handler(self, size, flags, depth, fill):
        get = pygame.event.get
        flip = pygame.display.flip
        get_surf = pygame.display.get_surface
        sleep = time.sleep
        waitbetween = self.waitbetween
        self.screen = mkscreen(size, flags, depth, fill, False)
        self.lock.release()
        time.sleep(.001)
        self.lock.acquire()
        try:
            while 1:
                sleep(waitbetween)
                if get(12):
                    return pygame.quitdefault()
                # get()
                if not get_surf():
                    return
                flip()
        except:
            pygame.quitdefault()
        finally:
            self.lock.release()
            pygame.quit = pygame.quitdefault
            del pygame.quitdefault

    def pygame_quit2(self):
        pygame.event.clear()
        pygame.event.post(pygame.event.Event(12))
        self.lock.acquire()
        self.lock.release()


def convert_bmp_to_png(filename, saveas=None):
    new = saveas and saveas or (os.path.splitext(filename)[0] + '.png')
    try:
        pygame.image.save(pygame.image.load(filename), new)
    except:
        try:
            os.remove(new)
        except:
            pass
        raise
    return new


def save_image(surf, name):
    if surf == 'screen':
        surf = pygame.display.get_surface()
    if name.count('.') == 0:
        name = f'{name}.png'
    pygame.image.save(surf, name)


def load_image(name, convert=False):
    surf = pygame.image.load(name)
    return convert and surf.convert() or surf


def load_image_fromweb(url, convert=False):
    return load_image(StringIO(webgen.urlopen(url)), convert)


def draw_to(image, dest, x=None, y=None):
    rect = image.get_rect()
    if x is not None and y is None and hasattr(x, '__iter__') and len(x) == 2:
        x, y = x
    else:
        if y is None:
            y = 0
        if x is None:
            x = 0
    return dest.blit(image, pygame.Rect(x, y, rect.width, rect.height))


def impose_pic(base, ontop):  # optimize this, pygame.display.update(dirty_rects)
    # meh, who cares
    if (pygame.display.get_init() and pygame.display.get_surface() and
            pygame.display.get_surface().get_size() == base.get_size()):
        s = pygame.display.get_surface()
    else:
        s = pygame.display.set_mode((base.get_width(), base.get_height()))
    base = base.copy()
    baserect = base.get_rect()
    r = ontop.get_rect()
    clock = pygame.time.Clock()
    s.blit(base, baserect)
    pygame.display.flip()
    pygame.event.pump()
    prevrect = pygame.Rect(r)
    prevrect.bottomright = (0, 0)
    # st = time.time()
    while [i for i in pygame.mouse.get_pressed() if i]:
        pygame.event.pump()  # if something's already pressed, wait
    while (not [i for i in pygame.mouse.get_pressed() if i] and
           not pygame.key.get_pressed()[pygame.K_ESCAPE]):
        # if not pygame.mouse.get_rel(), should just wait to not burn CPU
        # ct = time.time()
        # if ct - st > 1:
        #     pygame.display.set_caption(str(clock.get_fps()))
        #     st = time.time()
        clock.tick(60)
        pygame.event.pump()
        r.center = pygame.mouse.get_pos()
        if r.center == prevrect.center:
            continue
        s.blit(base, prevrect, prevrect)  # TODO fix this, third argument
        s.blit(ontop, r)
        pygame.display.update([r, prevrect])
        prevrect.center = r.center
    if pygame.mouse.get_pressed()[0]:
        base.blit(ontop, r)
    return base


def compare_surfs_fallback(one, two):
    if not isinstance(one, pygame.Surface):
        one = pygame.image.load(one)
    if not isinstance(two, pygame.Surface):
        two = pygame.image.load(two)
    if one.get_size() != two.get_size():
        return False
    one.lock()
    two.lock()
    try:
        for x in range(one.get_width()):
            for y in range(one.get_height()):
                if one.get_at((x, y)) != two.get_at((x, y)):
                    print(x, y)
                    return False
    finally:
        one.unlock()
        two.unlock()
    return True


def compare_surfs(one, two):
    # TODO use buffers()
    if not isinstance(one, pygame.Surface):
        one = pygame.image.load(one)
    if not isinstance(two, pygame.Surface):
        two = pygame.image.load(two)
    if one.get_size() != two.get_size():
        return False
    try:
        # if one.get_size() == (200,200): #testing purposess
        #     raise MemoryError()
        first = one.get_buffer().raw
        try:
            second = two.get_buffer().raw
        except:
            del one  # save memory, maybe
            second = two.get_buffer().raw
        r = first == second
        del first, second
        return r
    # TODO use buffers of subsurfaces of pieces of the surface to compare in pieces.
    except Exception as a:
        if isinstance(a, MemoryError) or a.message == 'Out of memory':
            # Last piece seems to be wrong at (200, 200).. sometimes.
            if one.get_size() == (100, 100):  # Strange error.
                return compare_surfs_fallback(one, two)
            midx = one.get_width() // 2
            xodd = one.get_width() % 2
            midy = one.get_height() // 2
            yodd = one.get_height() % 2
            # print midx, midy
            return (compare_surfs(one.subsurface((0, 0, midx, midy)),
                                  two.subsurface((0, 0, midx, midy))) and
                    compare_surfs(one.subsurface((0, midy, midx, midy)),
                                  two.subsurface((0, midy, midx, midy))) and
                    compare_surfs(one.subsurface((midx, 0, midx + xodd, midy + yodd)),
                                  two.subsurface((midx, 0, midx + xodd, midy + yodd))) and
                    compare_surfs(one.subsurface((midx, midy, midx + xodd, midy + yodd)),
                                  two.subsurface((midx, midy, midx + xodd, midy + yodd))))
        raise


formatmapping = {'P': chr(1), 'RGB': chr(2), 'RGBA': chr(3), 'ARGB': chr(4),
                 'RGBX': chr(5), 'RGBA_PREMULT': chr(6), 'ARGB_PREMULT': chr(7)}
formatunmapping = dict((item, key) for (key, item) in formatmapping.items())


def tostring(surf, format=None, flipped=False, justdata=False):
    if isinstance(surf, str) or hasattr(surf, 'read'):
        surf = pygame.image.load(surf)
    width, height = surf.get_size()
    width = struct.pack('h', width)
    height = struct.pack('h', height)
    if format is None:
        bits = surf.get_bitsize()
        if bits == 8:
            format = 'P'
        elif bits <= 24:
            format = 'RGB'
        else:
            format = 'RGBA'
    strformat = formatmapping[format]
    data = pygame.image.tostring(surf, format, flipped)
    if format == 'P':
        top = max(data)
        arraypal = array.array('B', (top,))  # code should = 'c'?
        palettedata = surf.get_palette()
        for p in range(top + 1):
            arraypal.extend(palettedata[p])
        palette = arraypal
    else:
        palette = b''
    if justdata:
        return data
    return width + height + bytes(strformat, 'ascii') + palette + data


def loadfromstring(f):
    with (open(f, 'rb') if isinstance(f, str) else contextlib.nullcontext(f)) as file:
        return fromstring(file.read())


def fromstringF(f):
    fread = f.read
    try:
        width = struct.unpack('h', fread(2))[0]
    except:
        print(f.name)
        raise
    height = struct.unpack('h', fread(2))[0]
    format = formatunmapping[chr(fread(1))]
    if format == 'P':
        pallen = fread(1) + 1
        palette = [None] * pallen
        palarray = iter(array.array('B', fread(pallen * 3))).__next__
        for p in range(pallen):
            palette[p] = (palarray(), palarray(), palarray())
    surf = pygame.image.frombuffer(memoryview(fread()), (width, height), format)
    if format == 'P':
        surf.set_palette(palette)
    return surf


def fromstring(f):
    width = struct.unpack('h', f[:2])[0]
    height = struct.unpack('h', f[2:4])[0]
    format = formatunmapping[chr(f[4])]
    if format == 'P':
        pallen = f[5] + 1
        palette = [None] * pallen
        paletteend = 6 + (pallen * 3)
        palarray = iter(array.array('B', f[6:paletteend])).__next__
        for p in range(pallen):
            palette[p] = (palarray(), palarray(), palarray())
    else:
        paletteend = 5
    surf = pygame.image.frombuffer(memoryview(f[paletteend:]), (width, height),
                                   format)
    if format == 'P':
        surf.set_palette(palette)
    return surf


def png_transparency(image, data=(0, 0)):
    if isinstance(image, str):
        filename = image
        image = load_image(image).convert_alpha()
    else:
        filename = None
    if len(data) == 2:
        color = image.get_at(data)
    else:
        color = data
    color = tuple(color[:3])
    for i in iter_surf(image):
        if image.get_at(i)[:3] == color:
            image.set_at(i, color + (0,))
    if filename:
        path, name = os.path.split(filename)
        save_image(image, os.path.join(path, 'alpha_' + name))
    return image
