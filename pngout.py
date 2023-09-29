import os
import sys
import time
import shutil
import math
import operator
from .cores import CORES
from . import filegen
from . import gen
from . import threaded_worker

try:
    from . import pygamegen
except ImportError as e:
    import warnings

    w = Warning(f'bitdepth finding may not be optimal: {e}')
    warnings.warn(w)
    del e, w
    pygamegen = None

# process priority (windows and linux):
if os.name == 'nt':
    PREFIX = 'start /LOW /B /WAIT'
elif os.name == 'posix':
    PREFIX = 'nice -n 19'
else:
    PREFIX = ''

PNGOUT_EXE_PATH = ''
if os.name == 'nt':
    myhome = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    PNGOUT_EXE_PATH = os.path.join(myhome, 'Desktop', 'pngout.exe')
if not os.path.exists(PNGOUT_EXE_PATH):
    PNGOUT_EXE_PATH = shutil.which('pngout') or ''


def pngout_build_command(filename, destination_filename, options):
    destination_string = destination_filename and f'"{destination_filename}"' or ''
    return f'{PREFIX} {PNGOUT_EXE_PATH} {options} "{filename}" {destination_string} /y'


def pngout(filename, destfilename=None, options=''):
    # process priority (windows only, even):
    # only works on windows
    """runs pngout on filename to destfilename (if given, else it's smart)
    fill this out with the pngout.exe options and such"""
    # handle options spacing + slashes yourself please
    if not PNGOUT_EXE_PATH:
        raise FileNotFoundError('PNGOUT_EXE_PATH not set')
    command = pngout_build_command(filename, destfilename, options)
    return os.popen(command).read()


def pngout_batch(files):  # no destfilename here
    for filename in files:
        # print filename
        print(gen.convert_sr_str(pngout(filename)))


def keeprunning(files=[]):
    import re
    FILENAME = 'pngout log.txt'
    # if os.path.exists(FILENAME):
    #     existingstr = open(FILENAME).read()
    # else:
    #     existingstr = ''
    existing = set()
    # for i in existingstr.split('\n'):
    #     found = re.search('In:[ ]*[0-9]+ bytes[ ]*(.*?) /c[0-9]', i)
    #     if found:
    #         existing.add(found.groups()[0])
    #     else:
    #         found = re.search('(.*?) not found',i)
    #         if found:
    #             existing.add(found.groups()[0])
    re_size = re.compile('Out:[ ]+([0-9]*) bytes')
    with open(FILENAME, 'a') as outputlog:
        for i in files:
            if i[-4:].lower() == '.png' and i not in existing:
                print(i)
                open('cur.txt', 'w').write(i)
                slashb = gen.changebase(32, 2)
                lastsize = 9999999999999999999999999999999  # a big file!
                times = 2
                while 1:
                    p = gen.convert_sr_str(
                        pngout(i, options='/b' + int(slashb, 2)))
                    print(int(slashb, 2))
                    print(slashb, file=outputlog)
                    print(p)
                    print(p, file=outputlog)
                    outputlog.flush()
                    thissize = re_size.search(p)
                    if not thissize:
                        print('SOMETHING WENT WRONG')
                        print('SOMETHING WENT WRONG', file=outputlog)
                        break
                    thissize = thissize.groups()[0]
                    if slashb == '1':
                        slashb = '0'
                    elif slashb == '0':
                        break
                    elif slashb[1] == '1':
                        slashb = '1' + ('0' * (len(slashb) - 1))
                    else:
                        slashb = '11' + slashb[3:]
                    if thissize >= lastsize:
                        times -= 1
                        if not times:
                            break
                    else:
                        times = 2
                    lastsize = thissize


def _colors_in(filename):
    # returns:
    # '': let pngout figure it out
    # '/c%d /d%d': /c%d (0=Gray, 2=RGB, 3=Pal, 4=Gray+Alpha, 6=RGB+Alpha) and
    #              /d%d (bitdepth: 0(min),1,2,4,8 (/c0,/c3 modes))
    # grey+alpha bits may not be correct, does it use len(colors), or highest
    # num of colors or num of alphas
    if not pygamegen:
        return ''
    try:
        c = pygamegen._colors_in(filename, True)
    except Exception:
        # print 'error checking image color data', filename, e
        return ''

    grey = len(c) <= 256
    alphas = set()
    colors = set()
    for r, g, b, a in c:
        alphas.add(a)
        if grey and not (r == g == b):
            grey = False
        colors.add((r, g, b))
    # if there's more than one alpha, or the one alpha is not 255
    alpha = (len(alphas) > 1 or alphas.pop() != 255) and 4 or 0
    # print 'alpha:',bool(alpha)
    # print 'grey: ',grey
    target = '/c%d'
    if len(c) > 256:
        return target % (2 + alpha)
    target2 = '/d%d'
    bits = int(math.ceil(math.log(len(colors), 2)))
    target += (' ' + (target2 % bits))
    if grey:
        return target % alpha
    return target % 3


def _mk_filename(filename, tempf, options):
    basedir = os.path.dirname(filename)
    base = os.path.splitext(os.path.basename(filename))[0]
    return os.path.join(basedir, tempf, f"{base}.{options.replace('/', '_')}.png")


def _run(filename, tempf, options):
    tofilename = _mk_filename(filename, tempf, options)
    pngoutput = pngout(filename, tofilename, '/y /force ' + options)
    try:
        size = os.stat(tofilename)[6]
    except OSError:  # usually file not made due to pngout error
        raise Exception(pngoutput)
    # os.remove(tofilename)
    return size, options


def slashb_down(worker, filename, tempf, options, prevsize, prevoptions,
                num=128, log=None, downby=3, verbose=True):
    # print 'options:',options
    if not log:
        log = int(math.ceil(math.log(num, 2))) - 1
    # print 'num:',num,' log:',log
    for x in range(log, max(log - downby, -1), -1):
        pow = 2 ** x
        if verbose:
            print(num, '->', (num - pow, num + pow), '->', end=' ')
        prevsize, prevoptions, _ = check(worker, filename, tempf, [
            f'/b{num - pow}',
            f'/b{num + pow}',
        ], options, prevsize, prevoptions)
        num = get_slashb(prevoptions)
        if verbose:
            print(num, prevsize, prevoptions)
    return prevoptions


def strip_option(options, char):
    char = '/' + char
    if char in options:
        ind = options.index(char)
        try:
            end = options.index(' ', ind) + 1
        except ValueError:
            end = len(options)
        return options[:ind] + options[end:]
    return options


def check(worker, filename, tempf, options, andoptions='',
          msize=None, moptions=None):
    """returns the options used to make the smallest file"""
    if moptions is None:
        moptions = andoptions
    for index, option in enumerate(options):
        options[index] = worker.put(filename, tempf, andoptions + ' ' + option)
    if msize:
        options.insert(0, (msize, moptions))  # to be tested in min below
        mod = 1
    else:
        mod = 0
    for index in range(mod, len(options)):
        options[index] = worker.get(options[index])
    winner = min(options, key=operator.itemgetter(0))
    return winner[0], winner[1], options


def get_slashb(options):  # /b is always last, make sure of that!
    return int(options[options.rindex('/b') + 2:])


class NotAnException(Exception):
    # yea, I'm using Exceptions as flow control, I feel dirty about it too
    def __init__(self):
        Exception.__init__(self)


TEMPprefix = 'pngout_TEMP_'


def find_best_compression(filename, threads=3, depth=5,
                          remove_not_png=True, verbose=True):
    assert os.path.exists(filename)
    pathjoin = os.path.join
    initsize = int(os.stat(filename)[6])
    # destination = os.path.dirname(filename)
    tempffilename = os.path.basename(os.path.splitext(filename)[0])
    maxlen = len(TEMPprefix) + len(tempffilename) + 10
    tempf = filegen.unused_filename(maxlen=maxlen, start=TEMPprefix,
                                    ending='_' + tempffilename, folder=filegen.TEMPfolder)  # , folder=destination)
    # print TEMPprefix, tempffilename,len(TEMPprefix)+len(tempffilename)+1
    # print tempf, len(tempf)
    os.mkdir(tempf)
    if isinstance(threads, threaded_worker.threaded_worker):
        worker = threads
    else:
        worker = threaded_worker.threaded_worker(_run, threads)
    if verbose:
        timer = gen.timer().__enter__()
    try:
        if verbose:
            print(filename, tempf, initsize, depth, end=' ')
        colors_options = _colors_in(filename)
        # if the color options chosen end up wrong,
        if colors_options and '/d' in colors_options and colors_options[-1] != '8':
            if verbose:
                print('checking bitdepth', end=' ')
            message = "Image doesn't fit in selected bitdepth"
            if (gen.convert_sr_str(pngout(filename, options=colors_options + ' /s4'))
                    .strip().rsplit('\n', 1)[-1][:len(message)] == message):
                colors_options = colors_options[:-1] + '8'  # make this better
        if verbose:
            print(colors_options)
        size_start, options, _ = check(worker, filename, tempf,
                                       ['/f0', '/f1', '/f2', '/f3', '/f4', '/f5'],
                                       # /s3 would be nice but seems to use a different algorithm and leads to
                                       # a bad selection when paired with /s0 later on
                                       colors_options + ' /s2')
        options = strip_option(options, 's')
        if verbose:
            print('prelim', size_start, options)
        if depth < 2 or (hasattr(depth, '__iter__') and 1 not in depth):
            size256, boptions, _ = check(worker, filename, tempf,
                                         ['/b256'], options)
            print(size256, options)
            raise NotAnException()
        size_b, boptions, every = check(worker, filename, tempf,
                                        ['/b128', '/b256', '/b512'], options)
        size256 = every[1][0]
        if verbose:
            print(size_b, boptions)
        if depth < 3 or (hasattr(depth, '__iter__') and 2 not in depth):
            raise NotAnException()
        num = 128
        log = 6
        up = True
        if size256 < size_b:
            smallestsize = size256
            smallestoptions = options + ' /b256'
            if boptions[-3:] == '512':
                num = 384
                up = False
        else:
            smallestsize = size_b
            smallestoptions = boptions
        if verbose:
            print(smallestsize, smallestoptions, num, log, up, boptions)
        if up and boptions[-3:] == '512':  # higher is potentially smaller
            if verbose:
                print('slashbfinder:', smallestsize, smallestoptions)
            while 1:
                smallestsize, prevb, _ = check(worker, filename, tempf, [
                    f'/b{get_slashb(smallestoptions) * 2}',
                ], options, smallestsize, smallestoptions)
                if verbose:
                    print('slashbfinder:', smallestsize, smallestoptions, prevb)
                if get_slashb(smallestoptions) == get_slashb(prevb):
                    break
                smallestoptions = prevb
            smallestoptions = prevb
            num = get_slashb(smallestoptions)
            log = int(math.log(num / 4, 2))
            # print 'starting point:',smallestsize,smallestoptions
        # else lower is potentially smaller, no changes needed
        # uses depth as how many checks it should do in this slashb_down
        if hasattr(depth, '__iter__'):
            depth = max(depth)
        options = slashb_down(worker, filename, tempf, options,
                              smallestsize, smallestoptions, num, log, depth - 2,
                              verbose=verbose)
    except NotAnException:
        pass
    finally:
        if verbose:
            timer.__exit__()
        if worker is not threads:
            worker.close(wait=1)
        try:
            low = os.stat(filename)[6]
            tocopy = ''
            for file in os.listdir(tempf):
                if file[-4:].lower() != '.png':
                    continue  # no thumbs.db here!
                name = pathjoin(tempf, file)
                size = os.stat(name)[6]
                if size < low:
                    tocopy = name
                    low = size
            if tocopy:
                base, ext = os.path.splitext(filename)
                shutil.move(tocopy, base + '.png')
                if verbose:
                    file_size_percent = 100 * os.stat(filename).st_size / initsize
                    print(f'{file_size_percent:.2f}%')
                if remove_not_png and ext.lower() != '.png':
                    os.remove(filename)
        finally:
            try:
                shutil.rmtree(tempf)
            except IOError:
                # sometimes... probably windows file indexing
                time.sleep(.4)
                shutil.rmtree(tempf)
    return options


def do_many(files, depth=5, threads=CORES):
    failed = []
    # pstdout, out = sys.stdout, open('output.txt','w')
    fdata = []
    start_size = end_size = 0
    with threaded_worker.threaded_worker(find_best_compression, threads, wait_at_end=True) as worker:
        with threaded_worker.threaded_worker(_run, threads) as inworker:
            for index, filename in enumerate(files):
                fdata.append((filename, os.stat(filename)[6]))
                worker.put(filename, inworker, depth, verbose=False, alsoreturn=index)
            total = len(fdata)
            print(f'0/{total}')
            for x in range(total):
                try:
                    filename = ''
                    front = f'{x + 1}/{total}'
                    options, alsoreturn = worker.get()

                    index = alsoreturn[0]
                    filename, size = fdata[index]
                    front = f'{front} {filename} ({options})'

                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    # filename isn't correct here, TODO find how to make it correct.
                    failed.append((filename, e))
                    print(f'{front}: error {str(e)}')
                    continue
                new_size = os.stat(filename)[6]
                if new_size < size:
                    end_size += new_size
                    start_size += size
                if new_size < size:
                    s = f'{front}: {new_size - size} {100 * new_size / size:.1f}%'
                elif new_size == size:
                    s = f'{front}: no diff'
                else:
                    s = f'{front}: worse'
                print(s)
    if start_size:
        print(f'{start_size} -> {end_size} ({100 * end_size / start_size:.1f}%)')
    return failed


def is_png(filename):
    # TODO actually check the file header
    return filename.lower()[-4:] == '.png'


def main(filename, threads=0, depth=5):
    threads = int(threads)
    if not threads:
        threads = CORES
    if not os.path.exists(filename):
        raise ValueError(f'File not found {filename}')
    if os.path.isfile(filename):
        find_best_compression(os.path.abspath(filename), threads, int(depth))
        if filename[-4:].lower() != '.png':
            os.remove(filename)
    else:
        do_many([i for i in filegen.files_in(filename) if is_png(i)], int(depth), threads)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.argv.extend(input('input: ').split(' '))
    try:
        r = main(*sys.argv[1:])
    except:
        import traceback

        # open('pngout error log.txt','a').write(traceback.format_exc())
        print('EXCEPTION STARTED:')
        print(sys.argv[1:])
        input(traceback.format_exc())
        r = 1
    sys.exit(0)
