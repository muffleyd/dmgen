import os
import sys
import shutil
import re
import time
import threading
import traceback
from collections import deque
from dmgen import threaded_worker
from dmgen import gen

sepjoin = os.sep.join


class Event(object):
    def __init__(self, type, dict):
        self.type = type
        self.dict = dict
        for i in dict:
            setattr(self, i, dict[i])
        self.__setattr__ = self.later__setattr__
        self.__delattr__ = self.later__delattr__

    def later__setattr__(self, what, val):
        self.dict[what] = val
        object.__setattr__(self, what, val)

    def later__delattr__(self, what):
        del self.dict[what]
        object.__delattr__(self, what)


NEWFILE = 0
SKIPFILE = 1
NOEXIST = 6
REMOVEFILE = 2
REMOVEFILEQUIET = 3
DONEREMOVE = 10
QUIT = 12

EVENTQUEUE = deque()
SECONDQUEUE = deque()


def check_excludes(what, excludes):
    for f in excludes:
        if isinstance(f, re.Pattern):
            if f.search(what):
                return True
        elif f in os.path.split(what) or what[-len(f):] == f:
            return True
    return False


def copytree(base_dir, source, destination, excludes, andcopy=True):
    # If destination directory has not been modified since after source directory, skip it and save so much time.
    curdir_dest = sepjoin((destination, source))
    curdir_dest_exists = os.path.exists(curdir_dest)
    curdir = sepjoin((base_dir, source))
    if (curdir_dest_exists and
            os.stat(curdir).st_atime <= os.stat(curdir_dest).st_atime):
        return
    if check_excludes(curdir, excludes):
        if curdir_dest_exists:
            postit(Event(REMOVEFILE, {'file': curdir_dest}))
        return

    items = list(os.scandir(curdir))
    # print(base_dir, source)
    # print(os.stat(curdir).st_atime, os.stat(destination).st_atime)
    if curdir_dest_exists:
        this_dir = set(i.name for i in items)
        # Remove items in destination that don't exist in source
        for target in os.scandir(curdir_dest):
            if target.name not in this_dir or check_excludes(target.name, excludes):
                postit(Event(REMOVEFILE, {'file': target.path}))
    elif andcopy:
        os.mkdir(curdir_dest)
    if andcopy:
        for i in items:
            if i.is_dir():
                copytree(base_dir, sepjoin((source, i.name)), destination, excludes, andcopy)
            else:
                copy2(sepjoin((curdir, i.name)), sepjoin((curdir_dest, i.name)), excludes)


def copy2(source, destination, excludes, overwrite=False):
    if check_excludes(destination, excludes):
        if os.path.exists(destination):
            postit(Event(REMOVEFILE, {'file': destination}))
        return
    if os.path.exists(destination):
        if not overwrite:
            o = os.stat(source)
            t = os.stat(destination)
            if o[6] == t[6] and o[8] == t[8]:  # size and edit_timestamp
                # postit(Event(SKIPFILE, {'file': source}))
                return
        # Deletes the target file, so after everything has been run through,
        #  new slightly larger files will not all be fragmented (probably)
        postit(Event(REMOVEFILEQUIET, {'file': destination}))
    postit(Event(NEWFILE, {'file': source, 'dest': destination}))


def postit(event):
    EVENTQUEUE.append(event)


def docopy(sources, destination, excludes, clean_base_directory=False):
    try:
        # postit(6)
        if clean_base_directory:
            copytree('.', '.', destination, excludes, andcopy=False)
        for entity in sources:
            entity_abs = os.path.abspath(entity)
            if not os.path.exists(entity_abs):
                postit(Event(NOEXIST, {'file': entity_abs}))
                continue
            base, name = os.path.split(entity_abs)
            if os.path.isfile(entity_abs):
                copy2(entity_abs, os.sep.join((destination, name)), excludes)
            else:
                copytree(base, name, destination, excludes)
        postit(Event(QUIT, {'ex': None}))
    except Exception as a:
        postit(Event(QUIT, {'ex': sys.exc_info()}))
        # raise


def handle_exc(e=None):
    print("EXCEPTION!!!-------------------------")
    if not e:
        traceback.print_exc(),
    else:
        print(traceback.print_exception(*e))  # ''.join(traceback.format_exception(*e))
    print("EXCEPTION!!!-------------------------")


def print_(worker, info):
    def _func(e): return None
    func = _func

    def doeval(func, e):
        ff = func(e)
        if ff:
            print(ff)
            if ff[-9:] in ('(100.00%)', 'REMOVING)', '(NOEXIST)'):
                return _func
        return func

    def newfile(e):
        original_size = os.stat(e.file)[6]
        dest_size = os.path.exists(e.dest) and os.stat(e.dest)[6] or 0
        perc = not original_size and 100 or (100 * dest_size / original_size)
        return '%s: %s/%s (%.2f%%)' % (e.file, dest_size, original_size, perc)

    def skipfile(e):
        return 'file: %s (SKIPPING)' % e.file

    def noexistfile(e):
        return 'file: %s (NOEXIST)' % e.file

    def removefile(e):
        return 'file: %s (REMOVING)' % e.file

    def remove(f):
        if os.path.isfile(f):
            os.remove(f)
        else:
            shutil.rmtree(f)
        return 'remove'

    def new(f, d):
        shutil.copy2(f, d)
        return 'new'

    if info:
        from dmgen import filegen

        def mk_num(val, by=1024):
            val //= by
            return '%s%s' % (val < 0 and '-' or '', gen.rinsertevery(abs(val), 3, ','))

        def info_dir(where):
            size = 0
            num = 0
            for i in filegen.ifiles_in(where):
                num += 1
                size += os.stat(i)[6]
            return num, size
        file_add = 0
        file_remove = 0
        size_add = 0
        size_remove = 0

    xr1000 = range(500)
    curq = EVENTQUEUE
    done_removing = False
    while 1:
        for _ in xr1000:
            size = len(curq)
            if size and (worker.thisindex == 1 or worker.check(worker.thisindex-1)):
                e = curq.popleft()
                try:
                    if not done_removing:
                        if e.type == QUIT:
                            done_removing = True
                            curq = SECONDQUEUE
                            curq.append(e)
                            if len(curq) > 1:
                                print('\n----------------- COPYING -----------------\n')
                            continue
                        else:
                            if e.type == NEWFILE:
                                print('file copy pending: %s' % e.file)
                                if info:
                                    file_add += 1
                                    size_add += os.stat(e.file)[6]
                            elif e.type in (REMOVEFILE, REMOVEFILEQUIET):
                                if e.type == REMOVEFILE:
                                    print('file removal: %s' % e.file)
                                    if info:
                                        if os.path.isfile(e.file):
                                            file_remove += 1
                                            size_remove += os.stat(e.file)[6]
                                        else:
                                            num, size = info_dir(e.file)
                                            file_remove += num
                                            size_remove += size
                                elif info:
                                    file_add -= 1
                                    size_add -= os.stat(e.file)[6]
                                worker.put(e.file, func=remove)
                            SECONDQUEUE.append(e)
                            continue
                    else:
                        if e.type == NEWFILE:
                            worker.put(e.file, e.dest, func=new)
                            func = newfile
                        elif e.type == REMOVEFILE:
                            func = removefile
                        elif e.type == SKIPFILE:
                            func = skipfile
                        elif e.type == NOEXIST:
                            func = noexistfile
                        elif e.type == QUIT:
                            if e.ex:
                                handle_exc(e.ex)
                                input()
                            if info and (file_add or file_remove or size_add or size_remove):
                                print('new files    ', file_add)
                                print('removed files', file_remove)
                                print('new Kbytes ', mk_num(size_add))
                                print('less Kbytes', mk_num(size_remove))
                                print()
                                print('diff files  ', file_add - file_remove)
                                print('diff KBytes ', mk_num(size_add-size_remove))
                            return e.ex
                        else:
                            continue
                    func = doeval(func, e)
                except:
                    handle_exc()
                break
            else:
                time.sleep(.001)
        else:
            if func is not _func:
                func = doeval(func, e)
            continue


def stripsplit(i, sep=','):
    return i.strip().split(sep)


def main(copy, dest, excludes=[], cleanbasedir=False, orders='orders.txt', niceend=True, info=True):
    assert isinstance(dest, str), TypeError('destination must be a string (got %s)' % type(dest))
    if isinstance(copy, str):
        copy = [copy]
    if len(copy) == 1:
        dest = os.path.join(dest, os.path.split(copy[0])[1])
        copy = [os.path.join(copy[0], i) for i in os.listdir(copy[0])]
    if not os.path.exists(dest):
        os.makedirs(dest)
    # print(orders)
    if os.path.exists(orders):
        for i in open(orders).read().split('\n'):
            if i:
                # print(i)
                demand, file1, file2 = stripsplit(i)
                if demand.lower() == 'rename':
                    os.rename(os.path.join(dest, file1), os.path.join(dest, file2))
                    print('renamed "%s" -> "%s"' % (file1, file2))
        open(orders, 'w').close()

    with gen.timer():
        with threaded_worker.threaded_worker(track=1) as worker:
            # docopy(copy, dest, excludes)
            t = threading.Thread(target=docopy, args=(copy, dest, excludes, cleanbasedir))
            t.daemon = True
            t.start()
            exitcode = int(not not print_(worker, info))  # i just love doing not not and I don't know why

    if niceend and sys.stdin == sys.__stdin__:
        time.sleep(3 + (info and 3 or 0))
    return exitcode
