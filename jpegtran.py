import os
import shutil
import subprocess
import traceback
from dmgen import threaded_worker
from dmgen import filegen
from dmgen.cores import CORES

JPEGTRAN_EXE_PATH = ''
if os.name == 'nt':
    myhome = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    JPEGTRAN_EXE_PATH = os.path.join(myhome, 'Desktop', 'jpegtran.exe')
if not os.path.exists(JPEGTRAN_EXE_PATH):
    JPEGTRAN_EXE_PATH = shutil.which('jpegtran') or ''
if not os.path.exists(JPEGTRAN_EXE_PATH):
    EXE_MISSING = 'jpegtran executable not found, set variable `JPEGTRAN_EXE_PATH` as file location'
    raise Warning(EXE_MISSING)

# Process priority (windows and linux).
if os.name == 'nt':
    PREFIX = 'start /LOW /B /WAIT '
elif os.name == 'posix':
    PREFIX = 'nice -n 19 '
else:
    PREFIX = ''


def jpeg(filename, destfilename=None, options='', optimize=True):
    # handle options spacing + slashes yourself please
    """Runs jpegtran on filename to destfilename (if given, else it's smart).
    Fill this out with the jpegtran executable options."""
    if not JPEGTRAN_EXE_PATH:
        raise FileNotFoundError('JPEGTRAN_EXE_PATH not set')
    if '-copy ' not in options:
        options = '-copy none ' + options
    out = PREFIX + '%s %s%s-outfile "%s" "%s"' % (
        JPEGTRAN_EXE_PATH,
        optimize and '-optimize ' or '',
        options and '%s ' % options or '',
        destfilename or filename,
        filename)
    p = subprocess.Popen(out, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    f = (None, p.stdout, p.stderr)
    p.wait()
    return destfilename or filename, f[1].read(), f[2].read()


TEMPprefix = 'jpeg_TEMP_'


def do2(input_filename, output_filename=None, options='', tw=None):
    if output_filename is None:
        output_filename = input_filename
    initsize = size = os.stat(input_filename)[6]
    folder, tfile = os.path.split(input_filename)
    if filegen.TEMPfolder:
        folder = filegen.TEMPfolder
    temp1 = filegen.unused_filename('_' + tfile, folder=folder)
    temp2 = filegen.unused_filename('_prog_' + tfile, [temp1], folder=folder)
    if tw is None:
        _tw = threaded_worker.threaded_worker(jpeg, min(2, CORES), wait_at_end=True)
    else:
        _tw = tw
    try:
        gets = (_tw.put(input_filename, temp1, options, func=_tw.func or jpeg),
                _tw.put(input_filename, temp2, '-progressive ' + options, func=_tw.func or jpeg))
        newfile = None
        out = None
        newsize = None
        for get in gets:
            temp, out, err = _tw.get(get)
            if err or out:
                raise Exception(err or out)
            if os.path.exists(temp):
                newsize = os.stat(temp)[6]
                if newsize and newsize < size:
                    newfile = temp
                    size = newsize
            if err:
                out += '\nError: ' + err
        if newfile:
            os.remove(input_filename)
            shutil.move(newfile, output_filename)
    finally:
        if tw is None:
            _tw.__exit__()
        try:
            if os.path.exists(temp1):
                os.remove(temp1)
            if os.path.exists(temp2):
                os.remove(temp2)
        except:
            print('%s %s %s' % (input_filename, temp1, temp2))
            raise
    return input_filename, out, initsize, newsize


def do(filename, options='', tw=None):
    return do2(filename, None, options, tw)


def do_many(files, options='', threads=None, verbose=True):
    # global worker #global for debugging purposes
    if isinstance(files, str):
        files = filegen.files_in(files)
    if not threads:
        threads = CORES
    todo = []
    failed = []
    startsize = endsize = 0
    with threaded_worker.threaded_worker(do, threads, wait_at_end=True) as worker:
        with threaded_worker.threaded_worker(jpeg, threads, wait_at_end=True) as internal_worker:
            for filename in files:
                todo.append(worker.put(filename, options, internal_worker))
            for ind in range(1, len(todo) + 1):
                try:
                    filename, out, size, newsize = worker.get(ind)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    failed.append((ind, e, traceback.format_exc()))
                    continue
                front = '%d/%d %s:' % (ind, len(todo), filename)
                if newsize < size:
                    endsize += newsize
                    startsize += size
                if verbose:
                    if newsize < size:
                        print('%s %d %.1f%%' % (front, newsize - size,
                                                100 * float(newsize) / size))
                    elif newsize == size:
                        print('%s no diff' % front)
                    else:
                        print('%s worse' % front)
                    if out:
                        print('output:', out)
    if verbose and startsize:
        print('%d -> %d (%.1f%%)' % (startsize, endsize, 100. * endsize / startsize))
    return failed


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]) and not os.path.isfile(sys.argv[1]):
            do_many(sys.argv[1], ' '.join(sys.argv[2:]))
        else:
            do(sys.argv[1], ' '.join(sys.argv[2:]))
