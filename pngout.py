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


def pngout(filename, destfilename=None, options=None):
    """runs pngout on filename to destfilename (if given, else it's smart)
    fill this out with the pngout.exe options and such"""
    # handle options spacing + slashes yourself please
    if not PNGOUT_EXE_PATH:
        raise FileNotFoundError('PNGOUT_EXE_PATH not set')
    command = pngout_build_command(filename, destfilename, options_to_string(options))
    return os.popen(command).read()


def options_to_string(options):
    if isinstance(options, dict):
        # Convert {n: 20, y: True} to '/n20 /y'
        return ' '.join(f'/{key}{value if value is not True else ""}' for key, value in options.items())
    elif isinstance(options, str):
        return options
    elif hasattr(options, '__iter__'):
        # Convert ['/n20', '/y'] to '/n20 /y'
        return ' '.join(options)
    elif not options:
        return ''
    else:
        raise ValueError('Unknown options type.')


def merge_options(one, two):
    merged = one.copy()
    merged.update(two)
    return merged


def pngout_batch(files):  # no destfilename here
    for filename in files:
        # print filename
        print(gen.convert_sr_str(pngout(filename)))


def _colors_in(filename):
    # returns:
    #   {}: let pngout figure it out
    #   {c: '%d', [d: '%d']}: Explicit options values.
    # /c (0=Gray, 2=RGB, 3=Pal, 4=Gray+Alpha, 6=RGB+Alpha) and
    # /d (bitdepth: 0(min),1,2,4,8 (/c0,/c3 modes))
    # grey+alpha bits may not be correct, does it use len(colors), or highest num of colors or num of alphas?
    if not pygamegen:
        return {}
    try:
        c = pygamegen._colors_in(filename, True)
    except Exception:
        # print 'error checking image color data', filename, e
        return {}

    grey = False
    alphas = set()
    colors = set()
    for r, g, b, a in c:
        alphas.add(a)
        colors.add((r, g, b))
    if len(colors) <= 256:
        for r, g, b in colors:
            if not (r == g == b):
                break
        else:
            grey = True
    # If there's more than one alpha, or the one alpha is not 255
    # This modified the grey/rgb /c value.
    # /c0 = grey, /c4 = grey+alpha.
    # /c2 = rgb, /c6 = rgb+alpha.
    alpha_modifier = (len(alphas) > 1 or alphas.pop() != 255) and 4 or 0
    if len(colors) > 256:
        return {'c': 2 + alpha_modifier}
    options = {'d': int(math.ceil(math.log(len(colors), 2)))}
    if grey:
        options['c'] = 0 + alpha_modifier
    else:
        options['c'] = 3
    return options


def _mk_filename(filename, tempf, options):
    basedir = os.path.dirname(filename)
    base = os.path.splitext(os.path.basename(filename))[0]
    return os.path.join(basedir, tempf, f"{base}.{options_to_string(options).replace('/', '_')}.png")


def _run(filename, tempf, options):
    tofilename = _mk_filename(filename, tempf, options)
    pngoutput = pngout(filename, tofilename, '/y /force ' + options_to_string(options))
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
            {'b': num - pow},
            {'b': num + pow},
        ], options, prevsize, prevoptions)
        num = prevoptions['b']
        if verbose:
            print(num, prevsize, options_to_string(prevoptions))
    return prevoptions


def check(worker, filename, tempf, options, andoptions='',
          msize=None, moptions=None):
    """returns the options used to make the smallest file"""
    if moptions is None:
        moptions = andoptions
    for index, option in enumerate(options):
        options[index] = worker.put(filename, tempf, merge_options(andoptions, option))
    if msize:
        options.insert(0, (msize, moptions))  # to be tested in min below
        mod = 1
    else:
        mod = 0
    for index in range(mod, len(options)):
        options[index] = worker.get(options[index])
    winner = min(options, key=operator.itemgetter(0))
    return winner[0], winner[1], options


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
        if 'd' in colors_options and colors_options['d'] != 8:
            if verbose:
                print('checking bitdepth', end=' ')
            message = "Image doesn't fit in selected bitdepth"
            if (gen.convert_sr_str(pngout(filename, options=merge_options(colors_options, {'s': 4})))
                    .strip().rsplit('\n', 1)[-1][:len(message)] == message):
                colors_options['d'] = 8  # make this better
        if verbose:
            print(options_to_string(colors_options))
        size_start, options, _ = check(worker, filename, tempf,
                                       [{'f': 0}, {'f': 1}, {'f': 2}, {'f': 3}, {'f': 4}, {'f': 5}],
                                       # /s3 would be nice but seems to use a different algorithm and leads to
                                       # a bad selection when paired with /s0 later on
                                       merge_options(colors_options, {'s': 2}))
        del options['s']
        if verbose:
            print('prelim', size_start, options_to_string(options))
        if depth < 2 or (hasattr(depth, '__iter__') and 1 not in depth):
            size256, boptions, _ = check(worker, filename, tempf,
                                         [{'b': 256}], options)
            print(size256, options_to_string(options))
            raise NotAnException()
        size_b, boptions, every = check(worker, filename, tempf,
                                        [{'b': 128}, {'b': 256}, {'b': 512}], options)
        size256 = every[1][0]
        if verbose:
            print(size_b, options_to_string(boptions))
        if depth < 3 or (hasattr(depth, '__iter__') and 2 not in depth):
            raise NotAnException()
        num = 128
        log = 6
        up = True
        if size256 < size_b:
            smallestsize = size256
            smallestoptions = merge_options(options, {'b': 256})
            if boptions[-3:] == '512':
                num = 384
                up = False
        else:
            smallestsize = size_b
            smallestoptions = boptions
        if verbose:
            print(smallestsize, options_to_string(smallestoptions), num, log, up, options_to_string(boptions))
        if up and boptions['b'] == 512:  # higher is potentially smaller
            if verbose:
                print('slashbfinder:', smallestsize, options_to_string(smallestoptions))
            while 1:
                smallestsize, prevb, _ = check(worker, filename, tempf, [
                    {'b': smallestoptions['b'] * 2},
                ], options, smallestsize, smallestoptions)
                if verbose:
                    print('slashbfinder:', smallestsize, options_to_string(smallestoptions), options_to_string(prevb))
                if smallestoptions['b'] == prevb['b']:
                    break
                smallestoptions = prevb
            smallestoptions = prevb
            num = smallestoptions['b']
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
                    front = f'{front} {filename} ({options_to_string(options)})'

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
