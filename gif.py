import os
import sys
from .gen import stritem_replace
VERBOSE = True

# between 0 and 65535


def chr16(num):
    return bytes((num % 256, num // 256))


def ord16(letters):
    return letters[0] + (letters[1] * 256)


def check_fpsval(value):
    return value
    # print value
    # if value < 1 or value > 65535 or not isinstance(value, int):
    #     raise ValueError('value must be int from 1 to 100')


def check_delayval(value):
    if value > 65535:
        return 65535
    return value
    # if value < 1 or value > 65535 or not isinstance(value, int):
    # raise ValueError('value must be int from 1 to 65535')


class Gif(object):
    """class to alter gif frame timing"""

    def __init__(self, filename):
        if VERBOSE:
            print('loading', os.path.relpath(filename))
        self.filename = filename
        self.data = data = open(filename, 'rb').read()
        # assert self.data[:6] == 'GIF89a'
        self.dims = (ord16(data[6:8]), ord16(data[8:10]))
        self.frame_delays()

    def __repr__(self):
        return '<Gif: "%s" %s>' % (self.filename, self.dims)

    def get_delays(self):
        for i in self.frames:
            print(ord16(self.data[i:i+2]), end=' ')

    def frame_delays(self):
        data = self.data
        self.frames = []
        self.framevals = []
        for i in range(len(data)):
            # 0, \x00: end previous block
            # 1-3, \x21\xf9\x04: Graphic Control Extension
            # 4, next is transparency data
            # 5-6, next 2 are frame timing data
            # 7, next is something
            # 8, next is \x00: end block
            # 9, start of next block
            # now once every 2**47 bits this will be a false positive.
            # what to do about it
            if (data[i:i+4] == b'\x00\x21\xf9\x04' and data[i+8] == 0
                    and data[i+9] in (33, 44)):
                # print(data[i+9], end=' ')
                # assert data[i+9] == '\x2c' #new image block after descriptor!
                self.frames.append(i+5)
                self.framevals.append(ord16(data[i+5:i+7]))

    def set_fps(self, value):
        if VERBOSE:
            print('setting FPS to', value)
        value = check_fpsval(value)
        values = {}
        last = 0
        for ind, i in enumerate(self.frames):
            frame = round((ind+1) / value * 100) - last
            last += frame
            values.setdefault(frame, [])
            values[frame].append(i)
        for i in values:
            self.set_delays(i, values[i], False)
        print('fps set to %d' % value)
        self.save()

    def set_delays(self, value, indexs=None, save=True):
        if VERBOSE:
            print('setting delay to', value)
        value = check_delayval(value)
        if indexs is None:
            if VERBOSE:
                print('for all indexs')
            indexs = self.frames
        elif not hasattr(indexs, '__iter__'):
            if VERBOSE:
                print('for index(s)', indexs)
            indexs = [indexs]
        else:
            if VERBOSE:
                print('for indexs', indexs)
        for i in indexs:
            self.data = stritem_replace(self.data, i, chr16(value), 2)
        if save:
            self.save()

    def save(self):
        if VERBOSE:
            print('saving', self)
        open(self.filename, 'wb').write(self.data)


def main():
    if len(sys.argv) > 1:
        g = Gif(sys.argv[1])
    try:
        ind = sys.argv.index('-f')
    except ValueError:
        try:
            ind = sys.argv.index('-d')
        except ValueError:
            pass
        else:
            if sys.argv[ind+1] == '?':
                delay = input('delay (3): ') or 3
                delay = int(delay)
            else:
                delay = int(sys.argv[ind+1])
            g.set_delays(delay)
    else:
        doFPS = True
        if sys.argv[ind+1] == '?':
            print('current fps: ', (100 * len(g.framevals) / sum(g.framevals)))
            fps = float(input('fps (30): ') or 30)
            if fps < 0:
                doFPS = False
                fps = -fps
        else:
            fps = float(sys.argv[ind+1])
        if doFPS:
            g.set_fps(fps)
        else:
            g.set_delays(fps)
    for i in sys.argv[2:]:
        if '-O=' in i:  # force best, it's 2:25am fu
            import opt_gif
            if VERBOSE:
                print('optimizing . . .')
            opt_gif.main(sys.argv[1])
            break


if __name__ == '__main__':
    main()
