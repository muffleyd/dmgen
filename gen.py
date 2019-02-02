import time
curtime = time.time
import sys, os
import getpass, itertools, math, random, threading, Queue
import types
from collections import deque
##from filegen import *
xmap = itertools.imap
try:
    import psyco
except ImportError:
    psyco = None
##else:
##    psyco.full()

hdrive_lock = threading.Lock()

os.myhome = os.environ.get('USERPROFILE',
                   os.path.sep.join(os.environ['TMP'].split(os.path.sep)[:3]))
os.desktop = os.path.join(os.myhome, 'Desktop')

class nested_context:
    def __init__(self, *c):
        self.contexts = c
    def __enter__(self):
        return [i.__enter__() for i in self.contexts]
    def __exit__(self, etype, exc, tb):
        noraise = False
        for i in reversed(self.contexts):
            try:
                noraise = i.__exit__(etype, exc, tb)
            except: #'i' has raised an exception, bad, but... gotta push it along
                noraise = False
                etype, exc, tb = sys.exc_info()
            else:
                if noraise:
                    etype = exc = tb = None
        if exc:
            raise etype, exc, tb
        return noraise

class empty_printer:
    def __init__(self, dostderr=False):
        self.dostderr = dostderr
    def realwrite(self, what):
        self.oldstdout.write(what)
    def flush(self):
        pass
    def write(self, *what):
        pass
    def writelines(self, *what):
        pass
    def read(self):
        return ''
    def __enter__(self):
        self.oldstdout = sys.stdout
        if self.dostderr:
            self.oldstderr = sys.stderr
            sys.stderr = self
        sys.stdout = self
        return self
    def __exit__(self, a, b, c):
        sys.stdout = self.oldstdout
        if self.dostderr:
            sys.stderr = self.oldstderr
_gen_stdout = empty_printer()
def toggle_printing():
    global _gen_stdout
    _gen_stdout, sys.stdout = sys.stdout, _gen_stdout
    return not isinstance(sys.stdout, empty_printer)
def real_print(val):
    sys.stdout.realwrite(val + "\n")

try:
    _gen_stdin
except NameError:
    pass
else:
    if isinstance(sys.stdin, stdin):
        tstdin()
class stdin:
    """basic dropin replacement for sys.stdin"""
    def __init__(self, s=[], doprint=True):
        self.data = deque(s)
        self.readline = doprint and self.readline_P or self.readline_NP

    def write(self, s):
        self.data.append(s)
    def readline_P(self):
        s = self.readline_NP()
        print s
        return s
    def readline_NP(self):
        return self.data.popleft()
class print_capture(stdin):
    def __init__(self, doprint=True):
        self.doprint = doprint
        stdin.__init__(self, doprint=False)
##        print self.write
    def __enter__(self):
        self.oldstdout = sys.stdout
        sys.stdout = self
        return self
    def __exit__(self, a, b, c):
        sys.stdout = self.oldstdout
        if self.doprint:
            print ''.join(self.data)
##        for i in self.data:
##            print i,
try:
    _gen_stdin
except NameError:
    _gen_stdin = stdin()

def tstdin(iterable=None, doprint=True):
    global _gen_stdin
    if iterable is not None:
        if isinstance(sys.stdin, stdin):
            sys.stdin = stdin(iterable, doprint)
            return
        else:
            _gen_stdin = stdin(iterable, doprint)
    _gen_stdin, sys.stdin = sys.stdin, _gen_stdin
    return not isinstance(sys.stdin, stdin)

__ENDPRINT = (lambda : -1)
__RAWINPUT = (lambda : -2)
def Print(*what, **OUT):
    if what and what[0] is __ENDPRINT:
        pqueue.put((what[0], None))
    else:
        pqueue.put((' '.join(str(i) for i in what), OUT.get('OUT')))
def end_print_main():
    Print(__ENDPRINT)
def print_main(out=None):#, gen=False):
    if out is None:
        out = sys.stdout
    while 1:
        d = pqueue.get()
        where = d[1] or out
        if d[0] is __ENDPRINT:
            break
        elif d[0] is __RAWINPUT:
            where.write(d[2])
            inputq.put(d[3].readline().strip())
        else:
            print >> where, d[0]
##        if gen:
##            yield None
def Raw_Input(q='', OUT=None, IN=None):
    pqueue.put((__RAWINPUT, OUT, q, IN or sys.stdin))
    return inputq.get()
def print_empty():
    #dunno if this is a good idea
    global pqueue, inputq
    pqueue = Queue.Queue()
    inputq = Queue.Queue(1)
print_empty() #defines them


class threadsafeSTDOUT:
    def __init__(self, stdout=None):
        if stdout is None:
            self.stdout = sys.stdout
            sys.stdout = self
        else:
            self.stdout = stdout
        self.writing = threading.Lock()
    def __del__(self):
        sys.stdout = self.stdout
    def Print(self, s, newline=True):
        #this issue isn't printing at the same time, it's a thread printing
        #such that the IDLE output window shifts everything up that breaks it
        self.writing.acquire()
        try:
            self.stdout.write(str(s) + (newline and '\n' or ' '))
        finally:
            self.writing.release()
    write = Print

if os.path.exists(os.path.join(os.desktop, 'ffmpeg.exe')):
    FFMPEG_EXE = os.path.join(os.desktop, 'ffmpeg.exe')
    def videolength(filename):
        z = os.popen3('""%s" -i "%s"'%(FFMPEG_EXE, filename))[2].read()
        anchor = 'Duration: '
        begin = z.index(anchor) + len(anchor)
        strtime = z[begin:z.index(',', begin)]
        return (int(strtime[:2])*3600) + (int(strtime[3:5]) * 60) + float(strtime[6:])
else:
    FFMPEG_EXE = None
    def videolength(filename):
        raise NotImplementedError('requires ffmpeg in expected location on windows')

def divisors(number):
    fnumber = float(number)
    return [i for i in xrange(2, number) if number / i == fnumber / i]

def primerange(limit, primes=None):
    if not primes:
        primes = [False, True] * (limit/2)
        if limit % 2:
            primes.append(False)
        primes[1] = False
        primes[2] = True
    for i in xrange(3, int(math.ceil(limit ** .5))):
        if primes[i]:
            for j in xrange(i*2, limit, i):
                primes[j] = False
    return primes

def primeslist(limit):
    return [i for i, j in enumerate(primerange(limit)) if j]
    

def factorial(n):
    for x in xrange(n-1, 0, -1):
        n *= x
    return n

def factors(num):
    facts = []
    for x in xrange(2, int(num**.5)+1):
        if not num % x:
            facts.append(x)
    last = num / facts[-1]
    if last != facts[-1]:
        facts.append(last)
    for x in facts[:-1:-1]:
        facts.append(num / x)
    return facts

def filledQueue(length=0, modFill=0):
    que = Queue.Queue(length)
    for i in xrange(modFill, length + modFill):
        que.put(i)
    return que

def convert_sr_str(s):
    finalout = [[]]
    CURSPOT = 0
    for char in s+'\n':  #hack cause i'm lazy
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
def test_seconds(func, args=(), kwargs={}, ttr=None):
    if isinstance(args, dict) and kwargs == {}:
        args, kwargs = (), args
    elif not hasattr(args, '__iter__'):
        args = [args]
    if ttr is None:
        ttr = TEST_SECONDS_TTR
    ran = 0
    endtime = 0
    starttime = curtime()
    while starttime+ttr > endtime:
        answer = func(*args, **kwargs)
        ran += 1
        endtime = curtime()

    runtime = endtime - starttime
    if runtime:
        if not ttr:
            actualran = ran / runtime
        else:
            actualran = ran / (runtime / ttr)
        if not actualran % 1:
            actualran = int(actualran)
    else:
        actualran = 1
    return runtime / ran, actualran, answer

def test_seconds_prnt(func, args=(), kwargs={}, ttr=None):
    a, b, c = test_seconds(func, args, kwargs, ttr)
    print '(%s, %s, %s)'%(not isinstance(a, int) and round(a, 4) or a,
                          not isinstance(b, int) and round(b, 4) or b,
                          c)

def dims_from_pixels(pixels, format):
    #format is 4/3., 16/9., etc, or None for...
    if format is None: #guessing
        for form in (4/3., 5/4., 16/9., 16/10., 19/12.):
            try:
                return dims_from_pixels(pixels, form)
            except AssertionError:
                pass
        raise ArithmeticError("can't guess format")
    format = float(format)
    y = (pixels / format)**.5
    x = y * format
    assert not x%1, ('x dimension is float', x)
    assert not y%1, ('y dimension is float', y)
    return int(x), int(y)

LINT_DEFAULT_IGNORES = ['C0103', 'C0111', 'C0323',
                        'W0142', 'W0622', 'W0702', 'W0704', 'R0913',
                        'W0401', 'W0703', 'W0603']
def lint(file=None, outputfile=None, ignore=[], extras='', defaultignores=True):
##    with switch_dir('
    ignore = defaultignores and ignore + LINT_DEFAULT_IGNORES or ignore
    file = file or sys.argv[0]
    if outputfile is sys.stdout:
        outputfile = ''
    elif outputfile is None:
        outputfile = os.path.splitext(file)[0] + '.lint.txt'
    # do i really need this to be r'""%s" -m...', with 2 " at the start?
    command = '""%s" -m pylint.lint --include-ids=y%s%s%s%s'\
              %(sys.executable.replace('pythonw.exe','python.exe'),
                ignore and ' --disable='+','.join(ignore) or '',
                extras and ' %s '%extras or '',
                ' "%s"'%file,
                outputfile and ' > "%s"'%outputfile or '')
    print command
    returned = os.popen3(command)
##    return returned
##    return outputfile
    return returned[1].read() or returned[2].read() or outputfile
def lint_many(files=[], outputfolder=None, ignore=[],
              extras='', defaultignore=True):
    for i in files:
        f = os.path.join(outputfolder, os.path.split(i)[0])
        if not os.path.exists(f):
            os.makedirs(f)            
        lint(i, os.path.join(outputfolder, i+'LINT.txt'), ignore,
             extras, defaultignore)

def diff(one, two, out=None):
    if isinstance(out, str):
        out = open(out,'w')
    elif not out:
        out = sys.stdout
    diff = os.popen('fc.exe "%s" "%s"'%(one, two)).read()
    return diff
##    print >>out, diff

def _tryremove(what, li):
    try:
        li.remove(what)
    except ValueError:
        pass

def default_of(ask, default, type):
    d = raw_input(ask)
    if not d:
        return default
    else:
        return type(d)

def runalittlebitfaster():
    #doesn't work, or does it?
    for i in dir(__builtins__):
        try:
            exec 'global %s; %s = __builtins__.%s'%(i, i, i)
        except SyntaxError: #things you're not allowed to redefine
            pass

def count(iter, val):
    if type(iter) == tuple:
        return len([i for i in iter if i == val])
    if type(iter) == dict:
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
    if hasattr(var, '__iter__'):
        try:
            it = iter(var)
        except TypeError:
            return []
        a = []
        for i in it:
            a.extend(chainfor(i))
        return a
    return [var]

def listof(something):
    if hasattr(something, '__iter__'):
        return something
    return [something]

def uptodateimport(s):
    return reload(__import__(s))

def filename_extension(file, ext='py'):
    return os.path.splitext(file)[0]+'.'+ext

def stritem_replace(string, index, value, len=1):
    return string[:index] + value + string[index+len:]

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

def safeaverage(a, b): #(int, int)
    return (a^b) >= 0 and a + (b-a)/2 or (a+b)/2

def samesign(a, b): #(int, int)
    return a^b >= 0

allowedchars = 'abcdefghijklmnopqrstuvwxyz0123456789_'
def unused_filename(ending='', donotuse=(), folder='.', maxlen=15, start=''):
    numgenerate = max(3, maxlen - len(start) - len(ending))
    rand = random.random
    name = ''
    while (name in donotuse or name in (i.lower() for i in os.listdir(folder)) or not name):
##               ''.join([random.choice(allowedchars)
        name = (start +
                ''.join([allowedchars[int(rand() * len(allowedchars))]
                         for i in xrange(int(1 + rand() * numgenerate))]) +
                ending)
    return name

def isprime(i):
    for j in xrange(2, int(i**.5) + 1):
        if not i % j:
            return False
    return True
def isprime2(i):
    """returns False if it is a prime, otherwise the number it is divisible by
    """
    for j in xrange(2, int(i**.5) + 1):
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
        middle = low + ((high - low) / 2)
        if list[middle] < item:
            low = middle+1
        else:
            high = middle
        if low >= high:
            break
    if list[low] < item:
        list.insert(low+1, item)
    else:
        list.insert(low, item)

def array(*dims):
    if type(dims[0]) in (tuple, list):
        dims = dims[0]
    return _array(dims)

def _array(dims):
    if len(dims) == 1:
        return [0] * dims[-1]
    return [_array(dims[:-1]) for i in xrange(dims[-1])]

def changebase(number, base=10):
    """inverse operation of __builtins__.int()"""
    if number:# and (base != 10 and (base >= 2 and base <= 32)):
        string = ''
        for i in xrange(int(math.log(number, base)), -1, -1):
            string = __basestr[number%base] + string
            number /= base
        return string
    return str(number)
__basestr = list('0123456789ABCDEFGHIJKLMNOPQRSTUV')
if psyco:
    psyco.bind(changebase)

def binarybyte(number): #direct method is fastest :]
    return ((number/128)&1 and '1' or '0') + ((number/64)&1 and '1' or '0') +\
           ((number/32)&1 and '1' or '0') + ((number/16)&1 and '1' or '0') +\
           ((number/8)&1 and '1' or '0') + ((number/4)&1 and '1' or '0') +\
           ((number/2)&1 and '1' or '0') + (number&1 and '1' or '0')
if psyco:
    psyco.bind(binarybyte)

def passwordprompt():
    return getpass.getpass()
def intsofchar(what):
    if len(what) == 1:
        return ord(what[0]) #* ord(what[0])
    return (ord(what[0]) * ord(what[0])) * intsofchar(what[1:])
def intofchar(what):
    return [int(i) for i in list(str(intsofchar(what)).strip('0'))]

def encode(what, by):
    by = [ord(char) for char in by]
    i = iter(by)
    what = list(what)
    for char in xrange(len(what)):
        try:
            nextmod = i.next()
        except:
            i = iter(by)
            nextmod = i.next()
        what[char] = chr(ord(what[char]) ^ nextmod)
    return ''.join(what)

def insertevery(string, each=8, join=' '):
    if not isinstance(string, basestring):
        string = str(string)
    return join.join([string[i:i+each] for i in xrange(0, len(string), each)])
def rinsertevery(string, each=8, join=' '):
    if not isinstance(string, basestring):
        string = str(string)
    return insertevery(string[::-1], each, join)[::-1]

def printf(toprint, extra='', split='\n'):
    if not toprint: return
    print "%s\n%s"%(extra, split.join(map(str, toprint)))

def strrange(start, stop=None, step=1, tolen=1):
    if stop is None:
        stop = start
        start = 0

    stoplen = len(str(stop-1))
    startlen = len(str(start))
    if stoplen > startlen:
        toplen = stoplen
    else:
        toplen = startlen
    if toplen > tolen: tolen = toplen
    return [i.zfill(tolen) for i in map(str, xrange(start, stop, step))]

def remove_duplicates(it, todo=None):
    #takes in an iterable, and removes duplicate entries (makes it like a set)
    # but stays in order
    curind = 0
    done = set()
    data2 = []
    for i in it:
        if i not in done:
            data2.append(i)
    typeit = todo and todo or type(it)
    if typeit == str:
        return ''.join(data2)
    if isinstance(data2, typeit):
        return data2
    return typeit(data2)

def extras(it):
    curind = 0
    data = {} #deque or queue, again?
    extras = []
    for i in it:
        if data.get(i) is None:
            data[i] = curind
            curind += 1
        else:
            extras.append(i)
    data2 = [None] * curind
    for item, ind in data.iteritems():
        data2[ind] = item
    if type(it) == str:
        data2 = ''.join(data2)
    else:
        data2 = type(it)(data2)
    return data2, extras


def _set_compare(one, two, func):
    #making the smaller one into a set is faster
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
            if isinstance(two, set):
                s = two
                t = one
            else:
                s = set(one)
                t = two
        else:
            s = one
            t = two
    else:
        if not isinstance(two, set):
            if isinstance(one, set):
                s = one
                t = two
            else:
                s = set(two)
                t = one
        else:
            s = two
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
    return tuple[:index] + (data,) + tuple[index+1:]

def list_same(one, two):
    return _set_compare(one, two, set.intersection)

def list_diff(one, two):
    return _set_compare(one, two, set.symmetric_difference)

def remove_all_of(list, what):
    #isiter(what) == True
    return [i for i in list if i not in what]

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
        for i in xrange(0, len(varnames), 2):
            toreturn.append(kwargs_dict.pop(varnames[i], varnames[i+1]))
    if not allow_extra and kwargs_dict:
        raise TypeError("unexpected keyword argument '%s'"%
                        kwargs_dict.iterkeys().next())
    return toreturn

def _dict_plus_oncollide(one, two, ind):
    return ind, two[ind]
def dict_plus(*dicts, **kwargs):
    """def dict_plus(*dicts, oncollide=_dict_plus_oncollide)"""
    #oncollide is a function that takes dict1, dict2, and current item
    #of dict1, called when item exists in both dictionaries.
    #@returns the item and key to be stored in the resulting dict
    oncollide = pop_kwargs(kwargs, 'oncollide', _dict_plus_oncollide)
    if not isinstance(oncollide, types.FunctionType):
        raise TypeError("oncollide must be a function")
    new = dict(dicts[-1].iteritems())
    for d in dicts[:-1]:
        for i in d:
            if new.has_key(i):
                key, val = oncollide(d, new, i)
                new[key] = val
            else:
                new[i] = d[i]
    return new

def flip_dict(di):
    return dict((j, i) for (i, j) in di.iteritems())

def parse_dict(di, recurse=False, spaces=0, between='\n'):
    return between.join(['%s%s: %s'%(' '*spaces, repr(i),
                                     (recurse and type(di[i]) == dict) and
                                         _return_print_dict(di[i],spaces+2) or
                                         repr(di[i])) for i in di])
def print_dict(di, recurse=False, spaces=0, between='\n'):
    print parse_dict(di, recurse, spaces, between)
def _return_print_dict(di, spaces=0, between='\n'):
    return ''.join(['%s%s%s: %s'%(between,
                                  ' '*spaces,
                                  repr(i),
                                  type(di[i]) == dict and\
                                      _return_print_dict(di[i],spaces+2) or
                                      repr(di[i])) for i in di])

def ls(folder='.', match='', case=False):
##    print match
    if hasattr(match, '__iter__'):
        match = [str(i) for i in match]
        if not case:
            match = [i.lower() for i in match]
            return [i for i in os.listdir(folder)
                    for j in match if j in i.lower()]
        return [i for i in os.listdir(folder) for j in match if j in i]
    elif not isinstance(match, str):
        match = str(match)
    if not case:
        match = match.lower()
        return [i for i in os.listdir(folder) if match in i.lower()]
    return [i for i in os.listdir(folder) if match in i]


class timer:
    def __init__(self, prnt=True, decimals=3, newline=True, before='', after=''):
        self.prnt = prnt
        #yea yea... I have practice doing rediculous strings like this.
        #Do not try this at home.
        #if decimals is 3, this ends up as
        #  "%s%.3f%s"% (before, self.runtime, after)
        #path is: (before="before ", after=" after")
        #  start: '%%s%%%%.%df%%s' %decimals
        # second: '%s%%.3f%s' %(before, after)
        #  third: 'before %.3f after'
        #then in .print_me(), self.runtime goes in %.3f
        self.printing = ('%%s%%%%.%df%%s'%decimals)% (before, after)
        self.newline = newline
    def get_runtime(self):
        if self.runtime is None:
            raise ValueError('timer still running')
        return self.runtime

    def print_me(self, newline=None):
        if newline is None:
            newline = self.newline
        toprint = self.printing % self.runtime
        if newline:
            print toprint
        else:
            print toprint,

    def __repr__(self):
        return str(self.get_runtime())

    def __enter__(self):
        self.runtime = None
        self.start = curtime()
        return self
    def __exit__(self, *exc):
        self.runtime = curtime() - self.start
        if self.prnt:
            self.print_me()
def timeit():
    z = timeret()
    if z is not None:
        print z
def timeret():
    global TIMEIT
    try:
        a = curtime()-TIMEIT
        del TIMEIT
        return a
    except NameError:
        TIMEIT = curtime()

def randomize_list(li):
    try:
        li = li[:]
    except TypeError:
        li = list(li)
    rand = random.random
    for i in xrange(len(li)):
        r = int(rand() * len(li))
        li[i], li[r] = li[r], li[i]
    return li

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
##    NoOptionException = 'Bad menu, you have a double comma, along with numbers flag on, means this option has nothing assigned to it!'
    if type(options) == str:
        options = [i.strip() for i in options.split(',')]
        options.append('') #adds an extra option, if an odd number of args are sent (no comma after the last one)
        options = [[options[i], options[i+1].split('/')]
                   for i in xrange(0, len(options)-1, 2)]
        curNum = 1
        test = ['']
        for i in options:
            if not numbers and i[1] == test: #no option given at all
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

    for op in xrange(len(options)):
        all_options.append(options[op][1])
        all_options_str.append(''.join(["'%s'/"%j for j in options[op][1]])[:-1])
        if format: #gets the max length of the options
            if max_len < len(all_options_str[-1]):
                max_len = len(all_options_str[-1])

    toP=['%s%s - %s' %(all_options_str[i], ' '*(max_len - len(all_options_str[i])),
                       options[i][0]) for i in xrange(len(options))]
    if title is not None:
        toP.insert(0, title)
    print '\n'.join(toP)
    while 1:
        if entry is not None:
            ask = entry
            print '%s%s'%(question, ask)
        else:
            ask = raw_input(question)
        for get_op in xrange(len(all_options)):
            if ask in all_options[get_op]:
                return get_op + mod
        if entry:
            raise ValueError('data sent not valid (%s)'%entry)

def formatli(li): #I made to print out a number triangle from a euler problem
    f=[' '.join(map(str, i)) for i in li]
    maxlen = max((len(i) for i in f))
    for i in f:
        print ' '*((maxlen/2) - len(i)/2),
        print i


def ensure_every_function_works():
    #my very own test function?
    tstdin()
    try:
        sys.stdin.write('1')
        print '* default_of'
        assert default_of('give me a 1! ', float, int) == 1
        #runalittlebitfaster doesn't work, as I said.. a while ago
        print '* count'
        assert count([1,4,2,3,3,1,2], 1) == 2
        assert count([1,23,4,1,2,3,4,1], 2) == 1
        assert count((1,4,2,3,3,1,2), 1) == 2
        assert count(set((1,23,4,1,2,3,4,1)), 23) == 1
        assert count({1: 2, 2: 1, 3: 4}, 1) == 1
        assert count({5: 2, 2: 1, 3: 4}, 1) == 0
        print '* listof'
        assert listof([1,2,3,4,4]) == [1,2,3,4,4]
        assert listof((1,2,3,4,4)) == (1,2,3,4,4)
        assert listof('aagsawerqwer') == ['aagsawerqwer']
        assert listof(9999999) == [9999999]
        print '* prime range (additive seive)'
        assert primerange(100) == [False, False, True, True, False, True, False, True, False, False, False, True, False, True, False, False, False, True, False, True, False, False, False, True, False, False, False, False, False, True, False, True, False, False, False, False, False, True, False, False, False, True, False, True, False, False, False, True, False, False, False, False, False, True, False, False, False, False, False, True, False, True, False, False, False, False, False, True, False, False, False, True, False, True, False, False, False, False, False, True, False, False, False, True, False, False, False, False, False, True, False, False, False, False, False, False, False, True, False, False]
        assert primerange(101) == [False, False, True, True, False, True, False, True, False, False, False, True, False, True, False, False, False, True, False, True, False, False, False, True, False, False, False, False, False, True, False, True, False, False, False, False, False, True, False, False, False, True, False, True, False, False, False, True, False, False, False, False, False, True, False, False, False, False, False, True, False, True, False, False, False, False, False, True, False, False, False, True, False, True, False, False, False, False, False, True, False, False, False, True, False, False, False, False, False, True, False, False, False, False, False, False, False, True, False, False, False]
##        assert primerange(100) == primerange0(100)
##        assert primerange(101) == primerange0(101)
        print '* filename_extension'
        assert filename_extension('hello.world', 'moto') == 'hello.moto'
        assert filename_extension('hello', 'world') == 'hello.world'
        assert fibonacci(99) == 218922995834555169026L
        assert _fibonacci_known[98] == 135301852344706746049L
        print '* safeaverage'
        assert safeaverage(1, 5) == 3
        assert safeaverage(sys.maxint, 12) == 1073741829
        assert type(safeaverage(sys.maxint, 12)) == int
        print '* samesign'
        assert samesign(1,2) == True
        assert samesign(-1,-2) == True
        assert samesign(-1,2) == False
        assert samesign(1,-2) == False
        assert samesign(0,-2) == False
        print '* binary_search_insert'
        baseli = range(10)
        binary_search_insert(baseli, 55)
        assert (baseli == [0,1,2,3,4,5,6,7,8,9,55]), baseli
        binary_search_insert(baseli, 4.9)
        assert (baseli == [0,1,2,3,4,4.9,5,6,7,8,9,55]), baseli
        binary_search_insert(baseli, -2)
        assert (baseli == [-2,0,1,2,3,4,4.9,5,6,7,8,9,55]), baseli
        print '* array' #i think I have array backwards right now
        assert array(2,3) == [[0, 0], [0, 0], [0, 0]]
        print '* changebase'
        assert changebase(255, 2) == '11111111'
        assert changebase(255, 16) == 'FF'
        assert changebase(65535, 4) == '33333333'
        assert changebase(65536, 4) == '100000000'
        print '* binarybyte'
        assert binarybyte(255) == '11111111'
        assert binarybyte(254) == '11111110'
        assert binarybyte(25) == '00011001'
        assert binarybyte(-1) == '11111111'
        print '* binarybyte2'
        assert binarybyte2(255) == '11111111'
        assert binarybyte2(254) == '11111110'
        assert binarybyte2(25) == '00011001'
        assert binarybyte2(-1) == '11111111'
        print '* insertevery'
        assert insertevery(changebase(int(2147483647*.8), 2),8) == '11001100 11001100 11001100 1100101'
        print '* strrange'
        assert strrange(10) == ['0','1','2','3','4','5','6','7','8','9']
        assert strrange(9,11) == ['09','10']
        assert strrange(10,tolen=2) == ['00','01','02','03','04','05','06','07','08','09']
        assert strrange(0, 10, tolen=2) == strrange(10,tolen=2)
        print '* remove_duplicates'
        assert remove_duplicates(range(10)) == range(10)
        assert remove_duplicates([1,1,1,1,1,1]) == [1]
        assert remove_duplicates((1,1,1,1,1,1)) == (1,)
        assert remove_duplicates([8,6,7,5,3,0,9,9,9,9,9,9,9]) == [8,6,7,5,3,0,9]
        assert remove_duplicates('hello world') == 'helo wrd'
        print '* extras'
        assert extras(range(10)) == (range(10),[])
        assert extras([1,1,1,1,1,1]) == ([1], [1,1,1,1,1])
        assert extras((1,1,1,1,1,1)) == ((1,), [1,1,1,1,1])
        assert extras([8,6,7,5,3,0,9,9,9,9,9,9,9]) == ([8,6,7,5,3,0,9], [9,9,9,9,9,9])
        assert extras('hello world') == ('helo wrd', ['l','o','l'])
        print '* list_same'
        assert sorted(list_same(range(10), range(5,15))) == [5,6,7,8,9]
        assert list_same(range(10), range(11,20)) == []
        assert sorted(list_same(range(10), range(10))) == range(10)
        assert sorted(list_same('aerhaskeuf', 'fjasekluas')) == ['a', 'e', 'f', 'k', 's', 'u']
        print '* list_diff'
        assert sorted(list_diff(range(10), range(5,15))) == [0,1,2,3,4,10,11,12,13,14]
        assert sorted(list_diff(range(10), range(11,20))) == [0,1,2,3,4,5,6,7,8,9,11,12,13,14,15,16,17,18,19]
        assert list_diff(range(10), range(10)) == []
        assert sorted(list_diff('aerhaskeuf', ['f','j','a','s','e','k','l','u','a','s'])) == ['h', 'j', 'l', 'r']
        print '* remove_all_of'
        assert remove_all_of(range(10), [11]) == range(10)
        assert remove_all_of(range(10), [0]) == range(1,10)
        assert remove_all_of([9,9,9,9,9,9,9], [9]) == []
        assert remove_all_of([9,9,9,'9',9,9,'9'], [9]) == ['9','9']
        assert remove_all_of(range(10), range(3,6)) == [0,1,2,6,7,8,9]
        print '* randomize_list (1:1000**1000 of test failing when it works)'
        assert randomize_list(range(1000)) != range(1000)
    finally:
        tstdin()
##if __name__ == '__main__':
##    ensure_every_function_works()
##

def test_set_cmpr(ttr=1, firstset=True, secondset=False):
    a = range(5)
    b = range(15)
    print test_seconds(_set_compare, [firstset and set(a) or a, secondset and set(b) or b, set.symmetric_difference], ttr)[:2]
    print test_seconds(_set_compare, [firstset and set(b) or b, secondset and set(a) or a, set.symmetric_difference], ttr)[:2]
    print test_seconds(_set_compare2, [firstset and set(a) or a, secondset and set(b) or b, set.symmetric_difference], ttr)[:2]
    print test_seconds(_set_compare2, [firstset and set(b) or b, secondset and set(a) or a, set.symmetric_difference], ttr)[:2]


##def tt():
##    import threaded_worker
##    def a(tw):
##        def run():
##            for i in xrange(4):
##                time.sleep(1)
##                Print(i+1)
##        tw.put(func=run)
##        time.sleep(1.3)
##        tw(func=run)
##        end_print_main()
##    with threaded_worker.threaded_worker(a, 3) as tw:
##        tw.put(tw)
##        print_main()

