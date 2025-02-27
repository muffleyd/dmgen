
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


def divisors(number):
    return [i for i in range(2, 1 + number // 2) if number // i == number / i]


def primerange(limit, primes=None):
    if not primes:
        primes = [False, True] * (limit // 2)
        if limit % 2:
            primes.append(False)
        primes[1] = False
        primes[2] = True
    for i in range(3, int(math.ceil(limit ** .5))):
        if primes[i]:
            for j in range(i * 2, limit, i):
                primes[j] = False
    return primes


def primeslist(limit):
    return [i for i, j in enumerate(primerange(limit)) if j]


def factorial(n):
    for x in range(n - 1, 0, -1):
        n *= x
    return n


def factors(num):
    facts = []
    for x in range(2, int(num ** .5) + 1):
        if not num % x:
            facts.append(x)
    last = num // facts[-1]
    if last != facts[-1]:
        facts.append(last)
    for x in facts[:-1:-1]:
        facts.append(num // x)
    return facts


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
        for form in (4 / 3, 5 / 4, 16 / 9, 16 / 10, 19 / 12):
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


LINT_DEFAULT_IGNORES = ['C0103', 'C0111',
                        'W0622', 'W0702', 'R0913',
                        'W0401', 'W0703', 'W0603']


def lint(file=None, outputfile=None, ignore=[], extras='', defaultignores=True):
    import pylint.lint
    ignore = defaultignores and ignore + LINT_DEFAULT_IGNORES or ignore
    file = file or sys.argv[0]
    if outputfile is sys.stdout:
        outputfile = ''
    elif outputfile is None:
        outputfile = os.path.splitext(file)[0] + '.lint.txt'
    # do i really need this to be r'""%s" -m...', with 2 " at the start?
    command = '""%s" -m pylint.lint --include-ids=y%s%s%s%s' \
              % (sys.executable.replace('pythonw.exe', 'python.exe'),
                 ignore and ' --disable=' + ','.join(ignore) or '',
                 extras and ' %s ' % extras or '',
                 ' "%s"' % file,
                 outputfile and ' > "%s"' % outputfile or '')
    command = ['--extension-pkg-whitelist=pygame']
    if ignore:
        command.append('--disable=' + ','.join(ignore))
    if extras:
        command.append(extras)
    if outputfile:
        command.append('--output=%s' % (outputfile))
    command.append(file)
    print(command)
    pylint.lint.Run(command, do_exit=False)


def lint_many(files=[], outputfolder=None, ignore=[], extras='', defaultignore=True):
    for i in files:
        f = os.path.join(outputfolder, os.path.split(i)[0])
        if not os.path.exists(f):
            os.makedirs(f)
        lint(i, os.path.join(outputfolder, i + 'LINT.txt'), ignore, extras, defaultignore)

# lint_many([i for i in os.listdir('.') if i[-3:] == '.py'], 'lint')


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


_fibonacci_known = [None, 1, 1]


def fibonacci(k):
    if round(k) == k and k > 0:
        return _fibonacci(int(k))
    if not k > 0:
        raise ValueError("Must be a positive integer")
    raise TypeError("Must be an integer")


def _fibonacci(k):
    if len(_fibonacci_known) > k:
        return _fibonacci_known[k]
    z = _fibonacci(k - 2) + _fibonacci(k - 1)
    _fibonacci_known.append(z)
    return z


def isprime(i):
    for j in range(2, int(i ** .5) + 1):
        if not i % j:
            return False
    return True


def isprime2(i):
    """returns False if it is a prime, otherwise the number it is divisible by
    """
    for j in range(2, int(i ** .5) + 1):
        if not i % j:
            return j
    return False


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

def binarybyte(number):  # direct method is fastest :]
    return ('1' if (number // 128) & 1 else '0') + ('1' if (number // 64) & 1 else '0') + \
           ('1' if (number // 32) & 1 else '0') + ('1' if (number // 16) & 1 else '0') + \
           ('1' if (number // 8) & 1 else '0') + ('1' if (number // 4) & 1 else '0') + \
           ('1' if (number // 2) & 1 else '0') + ('1' if number & 1 else '0')


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
    # making the smaller one into a set is faster
    if isinstance(one, set):
        if isinstance(two, set):
            if len(one) < len(two):
                s = one
                t = two
            else:
                s = two
                t = one
        else:
            s = one
            t = two
    elif isinstance(two, set):
        s = two
        t = one
    elif len(one) < len(two):
        s = set(one)
        t = two
    else:
        s = set(two)
        t = one
    return list(func(s, t))


def _set_compare2(one, two, func):
    if len(one) < len(two):
        if not isinstance(one, set):
            s = set(one)
        else:
            s = one
        t = two
    else:
        if not isinstance(two, set):
            s = set(two)
        else:
            s = two
        t = one
    return list(func(s, t))


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


class timer:
    def __init__(self, do_print=True, decimals=3, newline=True, before='', after=''):
        self.do_print = do_print
        self.before_print = before
        self.decimals_print = decimals
        self.after_print = after
        self.newline = newline

    def get_runtime(self):
        if self.runtime is None:
            raise ValueError('timer still running')
        return self.runtime

    def build_print_string(self):
        # Format runtime to decimal length.
        runtime_fstring = f'{self.runtime:.{self.decimals_print}f}'
        # Format the rest of the string.
        return f'{self.before_print}{runtime_fstring}{self.after_print}'

    def print_me(self, newline=True):
        to_print = self.build_print_string()
        if newline:
            print(to_print)
        else:
            print(to_print, end=' ')

    def __repr__(self):
        return str(self.get_runtime())

    def __enter__(self):
        self.runtime = None
        self.start = monotonic()
        return self

    def __exit__(self, *exc):
        self.runtime = monotonic() - self.start
        if self.do_print:
            self.print_me()


def menu(title, options=None, question=None, numbers=0, format=1, mod=1, entry=None):
    """Prints out the given input to a menu type format

       title is what is printed on the first (next) line

       options is a LIST/TUPLE or a STRING which will be printed, and the inputs that correspond with each option
       ex: [['Option 1',['o','op1']], ['Option 2',['O','op2']]]
         will yield
       'o'/'op1' - Option 1
       'O'/'op2' - Option 2
                                   ----  or  ----
       'Option 1, o/op1, Option 2, O/op2'
         will yield the same

       spaces may be placed liberally after each ',' in the string form, as the program will remove them
        when generating the menu
       ex: "o,o,p,p"  and "o,    o   , p    ,p" both give:
       'o' - o
       'p' - p
       as the resulting options

       using double commas: 'Option 1,,Option 2' creates a number as an option for each with the ',,', which will yield
       '1' - Option 1
       '2' - Option 2

       if numbers is set as 1, '1' is set as the first option for the first value,
        '2' is set as the first option for the second value, etc.

       placing a '-' before any of the options will make that option recieve a number as it's first possible input
       example:
           menu('Title','Option 1, -o/op1, Option 2, o2/op2, Option 3, -o3/op3') #note, numbers == 0 here
        or menu('Title','Option 1, -/o/op1, Option 2, o2/op2, Option 3, -o3/op3') #note, numbers == 0 here
        or menu('Title',[['Option 1', ['-','o','op1']], ['Option 2', ['o2','op2']], ['Option 3', ['-','o3','op3']]]) #note, numbers == 0 here

                   will print
           Title
           '1'/'o'/'op1' - Option 1
           'o2'/'op2' - Option 2
           '2'/'o3'/'op3' - Option 3

       placing a '-' before any of the options, and having numbers == 1 causes that option to not contain a number as the first choice
       example:
           menu('Title','Option 1, -o/op1, Option 2, o2/op2, Option 3, o3/op3', numbers=1)
                  will print
           Title
           'o'/'op1' - Option 1
           '1'/'o2'/'op2' - Option 2
           '2'/'o3'/'op3' - Option 3

       question is what is asked in the raw_input() call

       if format is set as 1 (default), all options are spaced out equally.
       example:
           'a'/'asdf'        - This option
           'anything'/'here' - That option


       example use of menu:
       a = menu('Main menu',[['Option 1',['o','op']],['Option 2',['O','op2']]],'Select an option',1)
                 -------- or -------
       a = menu('Main menu', 'Option 1,    o/op, Option 2,O/op2', 'Select an option', 1)
                               will yield:
           Main menu
           '1'/'o'/'op'  - Option 1
           '2'/'O'/'op2' - Option 2
           Select an option: (waits for user input here)

        if the user's input is not a possible option, it asks the question again
        the number option is what is returned (second option selected means 2 (type==int) is returned)"""
    if options is None:
        title, options = None, title

    ##### converts the string 'options' argument into the lists argument #####

    # example option (used throughout this section)
    # 'Option 1,     o/op, Option 2,, Option 3,  o/op3'
    # NoOptionException = 'Bad menu, you have a double comma, along with numbers flag on, means this option has nothing assigned to it!'
    if type(options) == str:
        options = [i.strip() for i in options.split(',')]
        options.append('')  # adds an extra option, if an odd number of args are sent (no comma after the last one)
        options = [[options[i], options[i + 1].split('/')]
                   for i in range(0, len(options) - 1, 2)]
        curNum = 1
        test = ['']
        for i in options:
            if not numbers and i[1] == test:  # no option given at all
                i[1][0] = i[0]
            elif numbers or i[1] == test or '-' in i[1]:
                if i[1] == test:
                    i[1] = [str(curNum)]
                elif '-' in i[1]:
                    if numbers:
                        del i[1][i[1].index('-')]
                        curNum -= 1
                    else:
                        i[1][i[1].index('-')] = str(curNum)
                else:
                    i[1].insert(0, str(curNum))
                curNum += 1

    # now is [['Option 1', ['o', 'op']], ['Option 2', ['-']], ['Option 3', ['o/op3']]] (ready for below)

    if question is None:
        question = 'Make a selection: '
    ask = ''
    max_len = 0
    current_num = 1
    all_options_str = []
    all_options = []

    for op in range(len(options)):
        all_options.append(options[op][1])
        all_options_str.append(''.join(["'%s'/" % j for j in options[op][1]])[:-1])
        if format:  # gets the max length of the options
            if max_len < len(all_options_str[-1]):
                max_len = len(all_options_str[-1])

    toP = ['%s%s - %s' % (all_options_str[i], ' ' * (max_len - len(all_options_str[i])),
                          options[i][0]) for i in range(len(options))]
    if title is not None:
        toP.insert(0, title)
    print('\n'.join(toP))
    while 1:
        if entry is not None:
            ask = entry
            print('%s%s' % (question, ask))
        else:
            ask = input(question)
        for get_op in range(len(all_options)):
            if ask in all_options[get_op]:
                return get_op + mod
        if entry:
            raise ValueError('data sent not valid (%s)' % entry)


def formatli(li):  # I made to print out a number triangle from a euler problem
    f = [' '.join(map(str, i)) for i in li]
    maxlen = max((len(i) for i in f))
    for i in f:
        print(' ' * ((maxlen // 2) - int(i) // 2), end=' ')
        print(i)


def test_set_cmpr(ttr=.2, firstset=True, secondset=False):
    a = list(range(5))
    b = list(range(15))
    print(test_seconds(_set_compare, [firstset and set(a) or a, secondset and set(b) or b, set.symmetric_difference],
                       time_to_run=ttr, loops=10000)[:2])
    print(test_seconds(_set_compare, [firstset and set(b) or b, secondset and set(a) or a, set.symmetric_difference],
                       time_to_run=ttr, loops=10000)[:2])
    print(test_seconds(_set_compare2, [firstset and set(a) or a, secondset and set(b) or b, set.symmetric_difference],
                       time_to_run=ttr, loops=10000)[:2])
    print(test_seconds(_set_compare2, [firstset and set(b) or b, secondset and set(a) or a, set.symmetric_difference],
                       time_to_run=ttr, loops=10000)[:2])
