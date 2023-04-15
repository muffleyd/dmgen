from functools import partial as _partial
import threading
import sys
version = '0.9'

# Queue2:
# calls task_done() whenever something is removed,
# allows items to be placed at the head of the Queue with
#           q.put[_nowait](item, head=True)
# I define these things below if Queue2 does not exist.


def partial(target, *args, **keywords):
    f = _partial(target, *args, **keywords)
    try:
        f.__name__ = func.__name__
    except:
        pass
    return f


partial.__doc__ = _partial.__doc__
try:
    from Queue2 import Queue
except ImportError:
    from queue import Queue as _Queue, Full
    from time import time as _time

    class Queue(_Queue):
        def get(self, block=True, timeout=None):
            z = _Queue.get(self, block, timeout)
            self.task_done()
            return z

        def remove(self, item):
            with self.not_empty:
                self.queue.remove(item)
                self.not_full.notify()
            self.task_done()

        def put(self, item, block=True, timeout=None, head=False):
            """Put an item into the queue.

            If optional args 'block' is true and 'timeout' is None (the default),
            block if necessary until a free slot is available. If 'timeout' is
            a non-negative number, it blocks at most 'timeout' seconds and raises
            the Full exception if no free slot was available within that time.
            Otherwise ('block' is false), put an item on the queue if a free slot
            is immediately available, else raise the Full exception ('timeout'
            is ignored in that case).
            """
            with self.not_full:
                if self.maxsize > 0:
                    if not block:
                        if self._qsize() == self.maxsize:
                            raise Full
                    elif timeout is None:
                        while self._qsize() == self.maxsize:
                            self.not_full.wait()
                    elif timeout < 0:
                        raise ValueError("'timeout' must be a positive number")
                    else:
                        endtime = _time() + timeout
                        while self._qsize() == self.maxsize:
                            remaining = endtime - _time()
                            if remaining <= 0.0:
                                raise Full
                            self.not_full.wait(remaining)
                if head:
                    self._puthead(item)
                else:
                    self._put(item)
                self.unfinished_tasks += 1
                self.not_empty.notify()

        # Put a new item at the head of the queue
        def _puthead(self, item):
            self.queue.appendleft(item)

# TODO:
# thread 1 puts data, so this handles it. meanwhile thread 2 puts data, then
# thread 3 puts data.  thread 3 requests it's answer, then thread 1's data
# finishes. currently thread 2's answer will be handled first,
# >>>>>> instead thread 3 should be done now.

# Exceptions on store=False?

# </TODO>

# active threaded_workers (if track is True and has active threads)
_workers = []
# 'end': sent to worker thread to end it (see self.close() and self._handle)
_ENDTHREAD = (0, 0, 0, 0, 0, 0)
# active threads place self (the worker) in here
_THREADS = []
_EMPTY_LIST = []

THREADS_AS_NEEDED = -1
UNLIMITED_PENDING = -1


class threaded_worker(object):
    """A class which allows multiple threads to request some action,
    and get the response at some later point.  Useful for putting I/O into
    some other thread and keep doing whatever calculations you need while the
    I/O does it's work.

    THE IMPLEMENTING MODULE IS RESPONSIBLE FOR ENDING THE THREADS!!!!
    There's a bit of circular referencing with locks waiting, so it doesn't
    ever really fall out of scope on it's own.
    They are run as daemon threads, so it's not imperitive that it happen if
    the program will exit often.  However...

    context manager:
      If used as part of a 'with' statement, threads are marked for 
      closing at the __exit__ of the 'with'.  __init__ recieves several
      arguments that affect it's behavior at the end of a 'with', including
      how it deals with unhandled exceptions.

    Exceptions in a function are stored in place of a return value, and
    re-raised during .get() .

    All of these __iter__ functions (get_all, get_all_until_closed, e.g.)
    have not been tested for thread-saftey, but probably aren't.  Know
    what you're getting in to, and probably only use them from one place
    once everything has been .put()'d.  Also they're subparly written at best.
    And their mothers were hampsters...
    """

    # __slots__ = ('onexc', 'completed_inds', 'track', 'numthreads', 'active',
    #              'allow_pending', 'wait_at_end', 'results', 'raise_onexc',
    #              'putlock', 'active_threads', 'threads_as_needed', 'isdone',
    #              'func', 'thisindex', 'pending', 'changethreads_lock')
    def __init__(self, func=None,
                 threads=THREADS_AS_NEEDED, max_pending=UNLIMITED_PENDING,
                 max_done_stored=UNLIMITED_PENDING,
                 onexc=lambda etype, value, tb: None,
                 wait_at_end=False, raise_onexc=True,
                 track=False):
        """Starts the worker.
        func is the function that will be called by default in .put().
        threads is the number of threads to run together.
        max_pending is the amount of pending data that can be placed before
          a .put() call blocks and waits for an active thread to finish;
          default means do not block, 0 means a .put() will block until its
          data is being run, effectively preventing any pending data.
        onexc is a function to be called if an exception kills the worker
          in a 'with' statement.  Recieves the 3 exception arguments.
        wait_at_end is a flag indicating if after leaving a 'with' context,
          should we wait for threads to end.
        raise_onexc is a bool; if True, an exception in a 'with' statment will
          raise, else it will not.  Either way, function onexc will be called.
        track will keep the worker in a list ONLY if it has active threads
          for debugging purposes."""
        self.track = track
        if track:
            self.active = []
        self.func = func
        self.completed_inds = Queue()
        # pending_inds stores which indexes are either being worked on or are completed and not yet get()'d.  It's
        #  important to track this in case max_done_stored is set to prevent some very slow jobs from being locked out.
        if max_done_stored is UNLIMITED_PENDING:
            self.pending_inds = Queue()
        elif max_done_stored == 0:
            raise NotImplementedError('not supported yet')
        else:
            self.pending_inds = Queue(max_done_stored)
        self.results = [None]
        if max_pending == 0:
            self.pending = Queue(1)
            self.allow_pending = False
        elif max_pending is UNLIMITED_PENDING:
            self.pending = Queue()
            self.allow_pending = True
        else:
            self.pending = Queue(max_pending)
            self.allow_pending = True

        self.isdone = threading.Lock()
        self.putlock = threading.Lock()
        # self.getlock = threading.Lock()

        self.thisindex = 1
        self.active_threads = 0
        self.numthreads = 0
        self.changethreads_lock = threading.Lock()
        if threads < 0:
            if threads is THREADS_AS_NEEDED:
                self.threads_as_needed = True
        else:
            try:
                self.start(threads)
            except:
                self.close()
                raise
            self.threads_as_needed = False

        self.onexc = onexc
        self.wait_at_end = wait_at_end
        self.raise_onexc = raise_onexc

       # def __del__(self):
       # #but there's references in the worker threads so this can't be collected
       #     self.close()

    def __repr__(self):
        return '<t_worker(%d threads (%d active), %d pending)>' % \
               (self.numthreads, self.active_threads, self.pending.qsize())

    def __iter__(self):
        """Iterates through available results, until there are none available.
        Does not pay attention to if there is pending data."""
        while 1:
            items = self.results[:]
            if not items:
                break
            for i in items:
                yield self.get()

    def __enter__(self):
        return self

    def __exit__(self, etype=None, value=None, tb=None):
        if etype:  # run onexception function
            self.onexc(etype, value, tb)
        if self.raise_onexc and etype:
            # close everything now, then let it reraise
            self.close_now()
            return False
        else:  # issue order to close and wait or don't
            if self.wait_at_end:
                self.close(wait=True)
            else:
                self.close()
            return True

    def get_all_until_closed(self):
        while 1:
            if not self.isdone:
                break
            yield self.get()

    get_all = __iter__

    def num_done(self):
        """returns the number of completed items (not reliable)"""
        return len(self.results) - 1 - self.pending.qsize() - self.active_threads

    def set_func(self, func):
        """changes the default function to call in each thread"""
        self.func = func

    def wait(self):
        """waits for all threads to end and returns"""
        self.isdone.acquire()
        self.isdone.release()

    def close_now(self, wait=False):
        """marks all threads for closing by placing the request at the start
        of the put queue.  Requires a modified Queue.py to work, else it
        falls back on self.close().

        See function 'close'"""
        self.close(wait=wait, now=True)

    def close(self, num=None, wait=False, now=False):
        """Finishes the pending jobs, and then ends the threads.
        if num is specified, will only close that many threads.
        if wait is True and all threads are to be closed, will block until all
         threads are closed.
        #data sent in after this is called will be left hanging around,
        #and restarting these threads may cause those jobs to run.
        (MAY because it might change at some point, don't count on it working)
        if now is True, the request to end threads will be placed at the front
         of the Queue instead of the back, but will not overtake currently
         running threads. Useful for ending threads after a program-halting
         exception.
        """
        if num is None or num > self.numthreads:
            num = self.numthreads
        elif num < 0:
            return
        for t in range(num):
            self.pending.put(_ENDTHREAD, head=now)
        if wait and num >= self.numthreads:
            # cannot just .join the Queue because there may be other items
            # after the .close()
            self.wait()

    def _updatenumthreads(self, mod):
        """internal use only. use .start() or .close() instead.
        starts/ends threads."""
        self.changethreads_lock.acquire()
        if not self.numthreads:  # was no threads until now
            self.isdone.acquire()
            if self.track:
                _workers.append(self)
        self.numthreads += mod
        if not self.numthreads:  # was threads, now they are done
            self.isdone.release()
            # self.putlock.acquire()
            # #releases all locks, marks all pending data as completed
            # for i, j in self.results.items():
            #    if j[2] is not None:
            #        continue
            #    j[2] = -1
            #    j[0].release()
            # self.putlock.release()
            if self.track:
                try:
                    _workers.remove(self)
                except ValueError:
                    pass
        self.changethreads_lock.release()

    def start(self, num=1):
        """Creates 'num' number of threads."""
        num = int(num)
        if num <= 0:
            return
        # number of threads updated one by one in case thread creation fails
        # (possibly due to OS complaint: too many threads)
        for t in range(num):
            thread = threading.Thread(target=self._handle)
            thread.setDaemon(True)
            thread.start()
            self._updatenumthreads(1)

    def __call__(self, *data, **kwargs):
        """shorthand for
        >>> ind = worker.put(stuff)
        >>> worker.get(ind)"""
        return self.get(self.put(*data, **kwargs))

    def build(self, func=None, store=True):
        """builds a partial .put() function
        e.g:
        >>> tempfunc = lambda x: x*x
        >>> ind1 = tw.put(4, func=tempfunc)
        >>> ind2 = tw.put(5, func=tempfunc)
        >>> print tw.get(ind1), tw.get(ind2)
        (16, 25)
            is the same as
        >>> p = tw.build(lambda x: x*x)
        >>> ind1 = p(4)
        >>> ind2 = p(5)
        >>> print tw.get(ind1), tw.get(ind2)
        (16, 25)
        """
        if func is None:
            func = self.func
        f = partial(self.put, func=func, store=store)
        f.__doc__ = """put(*args, **kwargs) #func=%s, store=%s""" % (
            hasattr(func, 'func_name') and func.__name__ or func, store)
        return f

    def put(self, *data, **kwargs):
        """self.send(*data, **kwargs, func=self.func, store=True)

        all non-keyword items sent here are used as arguments for func
        keyword arguments to be sent to func must be a mapping struct set to
          'kwargs' as a key-word argument.
        keyword arguments 'func' and 'store' can be sent here too
        'func' is the function that will be called for this data
        'store' is a boolean for if the return data should be stored to be
          retrieved later.  *NOTE* if store is False, exceptions raised from
          that function call will just be lost.
        'alsoreturn' is a variable that will be returned along with the data
          from the function execution.  Forced into an iterable."""
        func = kwargs.pop('func', self.func)
        if not hasattr(func, '__call__'):
            func = data[0]
            data = data[1:]
        store = kwargs.pop('store', True)
        if 'alsoreturn' in kwargs:
            alsoreturn = kwargs.pop('alsoreturn')
            if not hasattr(alsoreturn, '__iter__'):
                alsoreturn = (alsoreturn,)
        else:
            alsoreturn = None
        self.putlock.acquire()
        try:
            if store:
                thisindex = self.thisindex
                self.thisindex += 1
                this_lock = threading.Lock()
                this_lock.acquire()
                self.results.append([this_lock, None, None])
            else:
                thisindex = 1  # cannot eval to False, that ends the thread
            self.pending.put((func, data, kwargs, alsoreturn, store, thisindex))
        finally:
            self.putlock.release()

        if self.threads_as_needed:
            self.start(1)
        if not self.allow_pending:
            self.pending.join()
        if store:
            return thisindex

    def check(self, index):
        """Returns if the job of ID index is done, or None if not started."""
        if len(self.results) <= index:
            return None
        return not self.results[index][0].locked()

    def wait_for_job(self, index):
        """Waits until the job of ID index is done."""
        if len(self.results) <= index:
            return
        self.results[index][0].acquire()
        self.results[index][0].release()
        return

    def get(self, index=None, wait=True):
        """if index evals to False, block until a job is finished and return it,
            will be some random one (use only if you don't care about order)
           otherwise, blocks until the index value is finished, and returns
            that data.  If wait is False, raise Exception if thread is not
            complete."""
        # self.getlock.acquire()
        if not wait and not index:
            raise ValueError('wait may only be false if index is an index')
        _index = index or self.completed_inds.get()
        # things is = (lock, return_data, exception_flag)
        # cannot do lock, rd, ef = results[_index] because the data and flag
        # may not be finished when this is called (lock blocked!)
        done = self.results[_index][0].acquire(wait)  # not not self.numthreads)
        if wait and not done:
            raise ThreadNotComplete(index)
        # lock, data, exception_flag = things
        # data is the exception if exception_flag is True
        # otherwise it's (result, to_also_return)
        things = self.results[_index][:]
        # ensures the only copy is returned and can be gc'd
        self.results[_index][:] = _EMPTY_LIST
        if things[2] == -1:  # worker closed
            things[2] = None
            return
        if index is not None:
            # Not good, alter Queue.py for this.
            self.completed_inds.remove(index)
            self.pending_inds.remove(index)
        if things[2]:
            exc = things[1][0]
            exc[1].traceback = exc[2]
            raise exc[0](exc[1]).with_traceback(exc[2])
        if things[1][1] is None:
            return things[1][0]
        return things[1]

    def _handle(self):
        """internal use only,
           handles calling functions and places return values"""
        _THREADS.append(self)
        while 1:
            func, data, kwargs, alsoreturn, store, index = self.pending.get()
            if not index:  # ends the thread
                self._updatenumthreads(-1)
                _THREADS.remove(self)
                return
            if self.track:
                current_work = (func, data, kwargs, index)
                self.active.append(current_work)
            self.active_threads += 1
            self.pending_inds.put(index)
            try:
                returned_data = func(*data, **kwargs)
                exc = 0
            except:
                returned_data = sys.exc_info()
                exc = 1
            self.active_threads -= 1
            del data, kwargs
            if store:
                self.completed_inds.put(index)
                putspot = self.results[index]
                putspot[2] = exc
                putspot[1] = (returned_data, alsoreturn)
                putspot[0].release()
            if self.track:
                self.active.remove(current_work)
            if self.threads_as_needed:
                self.close(1)


class ThreadNotComplete(Exception):
    def __init__(self, index):
        Exception.__init__(self)
        self.index = index


def thread_map(data, func, toput=None, threads=1, *args, **kwargs):
    """thread_map
        `data` is data to handle.
        `func` is function to use to process the data.
        `toput` is a function that takes an item from 'data',
                and returns a piece of it to pass to the threaded_worker.
        `threads` is number of threads to run."""
    todo = 0  # don't take len(data) because it could be a generator
    with threaded_worker(func, threads) as tw:
        for d in data:
            if toput:
                data = toput(d)
            else:
                data = d
            tw.put(data, alsoreturn=d, *args, **kwargs)
            todo += 1
        for i in range(todo):
            yield tw.get()


def tmap(data, func, threads=1, toput=None, *args, **kwargs):
    return thread_map(data, func, toput, threads, *args, **kwargs)


def _thread_map2_put(tw, data, toput, *args, **kwargs):
    done = 0
    for original_data in data:
        if toput:
            processed_data = toput(original_data)
        else:
            processed_data = original_data
        tw.put(processed_data, alsoreturn=original_data, *args, **kwargs)
        done += 1
    return done


def thread_map2(data, func, threads=1, toput=None,
                max_pending=-1, max_done_stored=-1,
                order=False,
                *args, **kwargs):
    """thread_map2
        `data` is the data to handle.
        `func` is function to use to process the data.
        `toput` is a function that takes an item from 'data',
                and returns a piece of it to pass to the threaded_worker.
        `threads` and 'max_pending` are sent to threaded_worker.__init__()."""
    todo = 0  # don't take len(data) because it could be a generator
    index = 1
    done = False
    with threaded_worker(_thread_map2_put, 1, max_pending, max_done_stored) as putter:
        with threaded_worker(func, threads, max_pending, max_done_stored) as tw:
            main_put = putter.put(tw, data, toput, *args, **kwargs)
            while tw.check(index) is None:
                pass  # loops until the first item is started
            while 1:
                # if not done and putter not found to be done
                if not done and putter.check(main_put):
                    # set todo with the number of items put into tw
                    todo += putter.get(main_put)
                    done = True
                # if putter is done and todo is back to 0, end it
                if done and not todo:
                    break
                if order:
                    yield tw.get(index)
                    index += 1
                else:
                    yield tw.get()
                todo -= 1


def test(fname='readme.txt'):
    global w
    import time
    import traceback
    from dmgen import filegen

    def f(filename, mode='r'):
        return open(filename, mode).read()

    def onexc(etype, value, tb):
        print('exception ------------------------------')
        traceback.print_exception(etype, value, tb)
        print('----------------------------------------')

    with threaded_worker(f, 1, track=1, onexc=onexc, raise_onexc=False) as w:
        print(_workers)
        r = w.put(fname)
        w.put(func=lambda: time.sleep(1), store=False)
        print(_workers)
        f = filegen.unused_filename()
        r2 = w.put(f)
        print(r, r2)
        _ = w.get(r)
        try:
            _ = w.get(r2)
        except FileNotFoundError as a:
            # File expected to be not found!
            pass
        print('success!')
       # print w.get(r)
       # del _
       # return w
