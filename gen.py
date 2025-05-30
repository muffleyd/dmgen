
# TODO Remove the 80% of this I wrote in 2006 and haven't used since.
#  This has started at least.

import os
import sys
import time
import math
import random
import threading
import queue
import functools
from collections import deque
from . import timer
from . import menu
from . import lint

monotonic = time.monotonic

hdrive_lock = threading.Lock()

myhome = os.environ.get('HOME') or os.environ.get('USERPROFILE')
os.desktop = os.path.join(myhome, 'Desktop')


class nested_context:
    def __init__(self, *c):
        self.contexts = c

    def __enter__(self):
        return [i.__enter__() for i in self.contexts]

    def __exit__(self, etype, exc, tb):
        no_raise = False
        for i in reversed(self.contexts):
            try:
                no_raise = i.__exit__(etype, exc, tb)
            except:  # 'i' has raised an exception, bad, but... gotta push it along
                no_raise = False
                etype, exc, tb = sys.exc_info()
            else:
                if no_raise:
                    etype = exc = tb = None
        if exc:
            raise etype(exc).with_traceback(tb)
        return no_raise


class empty_printer:
    def __init__(self, do_stderr=False):
        self.do_stderr = do_stderr

    def realwrite(self, what):
        self.old_stdout.write(what)

    def flush(self):
        pass

    def write(self, *what):
        pass

    def writelines(self, *what):
        pass

    def read(self):
        return ''

    def real_print(self, *args):
        print(*args, file=self.old_stdout)

    def __enter__(self):
        self.old_stdout = sys.stdout
        if self.do_stderr:
            self.old_stderr = sys.stderr
            sys.stderr = self
        sys.stdout = self
        return self

    def __exit__(self, a, b, c):
        sys.stdout = self.old_stdout
        if self.do_stderr:
            sys.stderr = self.old_stderr


class print_capture:
    def __init__(self, print_at_end=True):
        self.data = deque()
        self.print_at_end = print_at_end

    def write(self, s):
        self.data.append(s)

    def __enter__(self):
        self.oldstdout = sys.stdout
        sys.stdout = self
        return self

    def __exit__(self, a, b, c):
        sys.stdout = self.oldstdout
        if self.print_at_end:
            print(''.join(self.data))


class CmdLineStdin:
    """Reads input from `data` until its exhausted, then uses the initial stdin."""

    def __init__(self, data):
        self.init_stdin = None
        self.data = data

    def __enter__(self):
        sys.stdin, self.init_stdin = self, sys.stdin
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdin = self.init_stdin

    def write(self, s):
        self.data.append(s)

    def readline(self):
        if not self.data:
            s = self.init_stdin.readline()
        else:
            s = self.data.pop(0)
            print(s)
        return s


if os.path.exists(os.path.join(os.desktop, 'ffmpeg.exe')):
    FFMPEG_EXE = os.path.join(os.desktop, 'ffmpeg.exe')

    def videolength(filename):
        z = os.popen3('""%s" -i "%s"' % (FFMPEG_EXE, filename))[2].read()
        anchor = 'Duration: '
        begin = z.index(anchor) + len(anchor)
        strtime = z[begin:z.index(',', begin)]
        return (int(strtime[:2]) * 3600) + (int(strtime[3:5]) * 60) + float(strtime[6:])
else:
    FFMPEG_EXE = None

    def videolength(filename):
        raise NotImplementedError('requires ffmpeg in expected location on windows')


def filled_queue(length=0):
    que = queue.Queue(length)
    for i in range(length):
        que.put(i)
    return que


def convert_sr_str(s):
    finalout = [[]]
    CURSPOT = 0
    for char in s + '\n':  # Hack because I'm lazy.
        if char == '\r':
            CURSPOT = 0
        elif char == '\n':
            CURSPOT = 0
            finalout[-1] = ''.join(finalout[-1])
            finalout.append([])
        else:
            try:
                finalout[-1][CURSPOT] = char
            except IndexError:
                finalout[-1].append(char)
            CURSPOT += 1
    return '\n'.join(finalout[:-1])


TEST_SECONDS_TTR = 0.5


def test_seconds(func, args=(), kwargs=None, time_to_run=TEST_SECONDS_TTR, loops=0):
    """
    Runs a function for some length of time to benchmark its speed.

    :param func: The function to benchmark, called like so: func(*args, **kwargs).
    :param args: Unnamed arguments passed into func like func(*args).
    :param kwargs: Named arguments passed into func like func(**kwargs).
    :param time_to_run: How long the benchmarking should continue.
    :param loops: How many times to call func before checking if it's time to stop.
                  For extremely short-running functions this can be very important to fine-tune.
                  e.g. test_seconds(time.time, loops=100) will run 2.3x more times than test_seconds(time.time).
                  Going beyond 100 will have a minimal reduction in this function's overhead.
                  If you choose to go higher, keep in mind which integers python generates vs looks up.
                  Keep this below 256 for CPython.
                  loops=2 will silently work like loops=1 due to range() overhead making it slower.
    :return tuple: (average time per func call, times func ran within time_to_run, result from func).
                   Since the actual runtime may not equal time_to_run exactly, the second argument may be a float.
    """
    if kwargs is None:
        if isinstance(args, dict):
            args, kwargs = (), args
        else:
            kwargs = {}
    elif not hasattr(args, '__iter__'):
        args = [args]

    # Build a function with partial so the overhead of *args and **kwargs is only done once.
    benchmark_function = functools.partial(func, *args, **kwargs)

    # Run benchmark_function() once here to get the answer and set an end_time.
    # Also has the side effect of sometimes preventing large loop values from running for much longer than a short time_to_run.
    ran = 1
    start_time = monotonic()
    answer = benchmark_function()
    time_to_stop = start_time + time_to_run
    end_time = monotonic()

    # If loops <= 1 we just run it once. If we let loops == 1 in here there would be needless range() overhead.
    # For the same reason we don't run loops == 2 here; range() overhead is harmful when running the function twice per loop.
    if loops >= 3:
        # Run the function `loops` times if it's a slower function so less of
        #  the runtime is spent getting the current time and adding 1 to ran.
        # test_seconds(time.time) vs test_seconds(time.time, loops=100) is 2.3x the func executions.
        while time_to_stop > end_time:
            for _ in range(loops):
                benchmark_function()
            ran += loops
            end_time = monotonic()
    else:
        while time_to_stop > end_time:
            benchmark_function()
            ran += 1
            end_time = monotonic()

    runtime = end_time - start_time
    if runtime <= 0:
        # If the runtime was so short as to be considered 0, avoid divide-by-zero errors.
        actual_ran = ran
    else:
        # Since the runtime won't match time_to_run exactly, normalize `ran` for accurate comparisons.
        if not time_to_run:
            actual_ran = ran / runtime
        else:
            actual_ran = ran / (runtime / time_to_run)
        if not actual_ran % 1:
            actual_ran = int(actual_ran)
    return runtime / ran, actual_ran, answer


def test_seconds_prnt(func, args=(), kwargs=None, ttr=None):
    if kwargs is None:
        kwargs = {}
    a, b, c = test_seconds(func, args, kwargs, ttr)
    print('(%s, %s, %s)' % (not isinstance(a, int) and round(a, 4) or a,
                            not isinstance(b, int) and round(b, 4) or b,
                            c))


def dims_from_pixels(pixels, format):
    # format is 4/3, 16/9, etc, or None for...
    if format is None:  # guessing
        for form in (4 / 3, 5 / 4, 16 / 9, 16 / 10, 19 / 12, 8 / 7):
            try:
                return dims_from_pixels(pixels, form)
            except AssertionError:
                pass
        raise ArithmeticError("can't guess format")
    format = float(format)
    y = (pixels / format) ** .5
    x = y * format
    assert not x % 1, ('x dimension is float', x)
    assert not y % 1, ('y dimension is float', y)
    return int(x), int(y)


def lint(file=None, outputfile=None, ignore=[], extras='', defaultignores=True):
    import warnings
    warnings.warn('gen.lint is deprecated, use lint.lint')
    lint.lint(file, outputfile, ignore, extras, defaultignores)


def lint_many(files=[], outputfolder=None, ignore=[], extras='', defaultignore=True):
    import warnings
    warnings.warn('gen.lint_many is deprecated, use lint.lint_many')
    lint.lint_many(files, outputfolder, ignore, extras, defaultignore)


def default_of(ask, default, type):
    d = input(ask)
    if not d:
        return default
    else:
        return type(d)


def runalittlebitfaster():
    # doesn't work, or does it?
    for i in dir(__builtins__):
        try:
            exec('global %s; %s = __builtins__.%s' % (i, i, i))
        except SyntaxError:  # things you're not allowed to redefine
            pass


def count(iter, val):
    if isinstance(iter, dict):
        return int(not not iter.get(val, False))
    try:
        return iter.count(val)
    except AttributeError:
        t = 0
        for i in iter:
            if i == val:
                t += 1
        return t


def chainfor(var):
    if not hasattr(var, '__iter__'):
        return [var]
    try:
        iterator = iter(var)
    except TypeError:
        return []
    values = []
    for i in iterator:
        values.extend(chainfor(i))
    return values


def list_of(something):
    if hasattr(something, '__iter__'):
        return something
    return [something]


def updated_import(module):
    import importlib
    if isinstance(module, str):
        module = __import__(module)
    return importlib.reload(module)


def uptodateimport(s):
    import warnings
    warnings.warn('uptodateimport(s) is deprecated, use updated_import(module)')
    return updated_import(s)


def stritem_replace(string, index, value, len=1):
    return string[:index] + value + string[index + len:]


def binary_search_insert(list, item):
    if not list:
        list.append(item)
        return
    low = 0
    high = len(list) - 1
    while 1:
        middle = low + ((high - low) // 2)
        if list[middle] < item:
            low = middle + 1
        else:
            high = middle
        if low >= high:
            break
    if list[low] < item:
        list.insert(low + 1, item)
    else:
        list.insert(low, item)


def array(*dims):
    if type(dims[0]) in (tuple, list):
        dims = dims[0]
    return _array(dims)


def _array(dims):
    if len(dims) == 1:
        return [0] * dims[-1]
    return [_array(dims[:-1]) for i in range(dims[-1])]


def changebase(number, base=10):
    """inverse operation of __builtins__.int()"""
    if number:  # and (base != 10 and (base >= 2 and base <= 32)):
        string = ''
        for i in range(int(math.log(number, base)), -1, -1):
            string = __basestr[number % base] + string
            number //= base
        return string
    return str(number)


__basestr = list('0123456789ABCDEFGHIJKLMNOPQRSTUV')


def binary_byte(number):
    """Returns an 8-bit string representation of the number."""
    return f'{number%256:08b}'


def binarybyte(number):
    import warnings
    warnings.warn('binarybyte(number) is deprecated, use binary_byte(number)')
    return binary_byte(number)


def encode(what, by):
    by = [ord(char) for char in by]
    i = iter(by)
    what = list(what)
    for char in range(len(what)):
        try:
            nextmod = next(i)
        except:
            i = iter(by)
            nextmod = next(i)
        what[char] = chr(ord(what[char]) ^ nextmod)
    return ''.join(what)


def insertevery(string, each=8, join=' '):
    if not isinstance(string, str):
        string = str(string)
    return join.join([string[i:i + each] for i in range(0, len(string), each)])


def rinsertevery(string, each=8, join=' '):
    if not isinstance(string, str):
        string = str(string)
    return insertevery(string[::-1], each, join)[::-1]


def str_range(start, stop=None, step=1, str_len=1):
    """
    Functions like range() except returns strings zfilled to str_len or largest number's string length.
    """
    if stop is None:
        stop = start
        start = 0
    stop_len = len(str(stop - 1))
    start_len = len(str(start))
    if stop_len > start_len:
        top_len = stop_len
    else:
        top_len = start_len
    if top_len > str_len:
        str_len = top_len
    return (str(i).zfill(str_len) for i in range(start, stop, step))


def remove_duplicates(data, new_type=None):
    # Takes in an iterable, and removes duplicate entries (makes it like a
    # set), but stays in order.
    curind = 0
    done = set()
    parsed_data = []
    for element in data:
        if element not in done:
            done.add(element)
            parsed_data.append(element)
    if not new_type:
        new_type = type(data)
    if new_type == str:
        return ''.join(parsed_data)
    if isinstance(parsed_data, new_type):
        return parsed_data
    return new_type(parsed_data)


def extras(it):
    curind = 0
    data = {}  # deque or queue, again?
    extras = []
    for i in it:
        if data.get(i) is None:
            data[i] = curind
            curind += 1
        else:
            extras.append(i)
    data2 = [None] * curind
    for item, ind in data.items():
        data2[ind] = item
    if type(it) == str:
        data2 = ''.join(data2)
    else:
        data2 = type(it)(data2)
    return data2, extras


def _set_compare(one, two, func):
    if len(one) > len(two):
        one, two = two, one
    if not isinstance(one, set):
        one = set(one)
    return list(func(one, two))
_set_compare2 = _set_compare

def change_tuple(tuple, index, data):
    if index < 0:
        if index < -len(tuple):
            raise IndexError(index)
        index %= len(tuple)
    if index >= len(tuple):
        raise IndexError(index)
    return tuple[:index] + (data,) + tuple[index + 1:]


def pop_rand(li):
    return li.pop(int(random.random() * len(li)))


def pop_kwargs(kwargs_dict, *varnames, **kwargs):
    """pop_kwargs(kwargs_dict, *varnames, allow_extra=False
    varname in the form of: string, default
    var1, default1, var2, default2, varN, defaultN

    allow_extra determines whether extra kwargs will raise "too many arguments"
    exception, or do nothing (leave them be)"""
    allow_extra = kwargs.get('allow_extra', False)
    if len(varnames) == 2:
        toreturn = kwargs_dict.pop(varnames[0], varnames[1])
    else:
        toreturn = []
        for i in range(0, len(varnames), 2):
            toreturn.append(kwargs_dict.pop(varnames[i], varnames[i + 1]))
    if not allow_extra and kwargs_dict:
        raise TypeError("unexpected keyword argument '%s'" %
                        next(iter(kwargs_dict.keys())))
    return toreturn


def flip_dict(dictionary):
    return {value: key for key, value in dictionary.items()}


def parse_dict(dictionary, recurse=False, spaces=0, between='\n'):
    return between.join(['%s%s: %s' % (
        ' ' * spaces,
        repr(key),
        (recurse and type(value) == dict) and _return_print_dict(value, spaces + 2) or repr(value)
    ) for key, value in dictionary.items()])


def print_dict(dictionary, recurse=False, spaces=0, between='\n'):
    print(parse_dict(dictionary, recurse, spaces, between))


def _return_print_dict(dictionary, spaces=0, between='\n'):
    return ''.join(['%s%s%s: %s' % (
        between,
        ' ' * spaces,
        repr(key),
        isinstance(value, dict) and _return_print_dict(value, spaces + 2) or repr(value)
    ) for key, value in dictionary.items()])


def timer(*args, **kwargs):
    import warnings
    warnings.warn('gen.timer is deprecated, use timer.Timer')
    return timer.Timer(*args, **kwargs)


def menu(*args, **kwargs):
    import warnings
    warnings.warn('gen.menu is deprecated, use menu.menu)')
    return menu.menu(*args, **kwargs)


def formatli(li):  # I made to print out a number triangle from a euler problem
    f = [' '.join(map(str, i)) for i in li]
    maxlen = max((len(i) for i in f))
    for i in f:
        print(' ' * ((maxlen // 2) - int(i) // 2), end=' ')
        print(i)
