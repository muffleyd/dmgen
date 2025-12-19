from io import BytesIO
import os
import shutil
import subprocess
import tempfile
import traceback
from . import threaded_worker
from . import filegen
from .cores import CORES
try:
    import pygame
    from .pygamegen import compare_surfs
except ImportError:
    CAN_VALIDATE = False
else:
    CAN_VALIDATE = True

JPEGTRAN_EXE_PATH = shutil.which('jpegtran') or ''
if not os.path.exists(JPEGTRAN_EXE_PATH) and os.name == 'nt':
    myhome = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    JPEGTRAN_EXE_PATH = os.path.join(myhome, 'Desktop', 'jpegtran.exe')
if not os.path.exists(JPEGTRAN_EXE_PATH):
    import warnings
    EXE_MISSING = 'jpegtran executable not found, set variable `JPEGTRAN_EXE_PATH` as file location'
    warnings.warn(EXE_MISSING, Warning)

# Process priority (windows and linux).
if os.name == 'nt':
    PREFIX = 'start /LOW /B /WAIT'
elif os.name == 'posix':
    PREFIX = 'nice -n 19'
else:
    PREFIX = ''

TEMP_prefix = 'jpeg_TEMP_'


def jpeg(filename, output_filename=None, options='', optimize=True):
    # handle options spacing + slashes yourself please
    """Runs jpegtran on filename to output_filename (if given, else it's smart).
    Fill this out with the jpegtran executable options."""
    if not JPEGTRAN_EXE_PATH:
        raise FileNotFoundError('JPEGTRAN_EXE_PATH not set')
    if '-copy ' not in options:
        options = f'-copy none {options}'
    optimize_str = '-optimize' if optimize else ''
    out = [i for i in [
        *(PREFIX.split(' ')),
        JPEGTRAN_EXE_PATH,
        optimize_str,
        *(options.split(' ')),
    ] if i]
    with open(filename, 'rb') as input_object:
        proc = subprocess.run(out, stdin=input_object, capture_output=True, check=False)
    return proc.returncode, proc.stdout, proc.stderr


def validate_image(one, two):
    if not CAN_VALIDATE:
        raise Exception('Required packages for validation are not found.')
    image_one = pygame.image.load(one)
    image_two = pygame.image.load(two)
    same = compare_surfs(image_one, image_two)
    return same


def do2(input_filename, output_filename=None, options='', tw=None, validate=True):
    if hasattr(input_filename, 'stat'):
        stat = input_filename.stat()
        input_filename = input_filename.path
    else:
        stat = os.stat(input_filename)
    if output_filename is None:
        output_filename = input_filename
    initial_size = stat.st_size
    if tw is None:
        _tw = threaded_worker.threaded_worker(jpeg, min(2, CORES), wait_at_end=True)
    else:
        _tw = tw
    try:
        gets = (_tw.put(input_filename, None, options, func=_tw.func or jpeg),
                _tw.put(input_filename, None, '-progressive ' + options, func=_tw.func or jpeg))
        new_size = None
        new_contents = None
        for get in gets:
            return_code, out, err = _tw.get(get)
            if return_code or err or not out:
                raise Exception(f'Error while processing file "{input_filename}"\n{return_code=}, out={len(out)}, {err=}')
            size = len(out)
            if size and (not new_size or size < new_size):
                if validate:
                    if not validate_image(input_filename, BytesIO(out)):
                        raise Exception(f'Processed file is not identical to source file: {input_filename}')
                new_contents = out
                new_size = size
        overwrite_input_file = os.path.abspath(output_filename) == os.path.abspath(input_filename)
        write_file = True
        if (
            not new_contents or
            not new_size or (
                overwrite_input_file and
                new_size >= initial_size
            )
        ):
            write_file = False
        if write_file:
            file_times = (
                stat.st_atime_ns,
                stat.st_mtime_ns,
            )
            if overwrite_input_file:
                with tempfile.NamedTemporaryFile() as temp_file:
                    temp_file.write(new_contents)
                    os.utime(temp_file.name, ns=file_times)
                    shutil.move(temp_file.name, output_filename)
            else:
                with open(output_filename, 'wb') as output_file:
                    output_file.write(new_contents)
                os.utime(output_filename, ns=file_times)
    finally:
        if tw is None:
            _tw.__exit__()
    return input_filename, initial_size, new_size


def do(filename, options='', tw=None):
    return do2(filename, None, options, tw)


def do_many(files, options='', threads=None, verbose=True):
    # do_many_yield yields everything, this only returns all the exceptions.
    return [
        (filename, *exception)
        for filename, exception
        in do_many_yield(files, options, threads, verbose)
        if exception
    ]


def do_many_yield(files, options='', threads=None, verbose=True):
    # global worker #global for debugging purposes
    if isinstance(files, str):
        files = filegen.files_in_scandir(files)
    if not threads:
        threads = CORES
    todo = []
    start_size = end_size = 0
    with threaded_worker.threaded_worker(do, threads, wait_at_end=True) as worker:
        with threaded_worker.threaded_worker(jpeg, threads, wait_at_end=True) as internal_worker:
            for filename in files:
                todo.append((filename, worker.put(filename, options, internal_worker)))
            total = len(todo)
            if verbose:
                print(f'0/{total}')
            for original_filename, ind in todo:
                try:
                    filename, size, new_size = worker.get(ind)
                except Exception as e:
                    yield original_filename, (e, traceback.format_exc())
                    continue
                yield filename, None
                if new_size < size:
                    end_size += new_size
                    start_size += size
                if verbose:
                    front = f'{ind}/{total} {filename}:'
                    if new_size < size:
                        print(f'{front} {new_size - size} {100 * new_size / size:.1f}%')
                    elif new_size == size:
                        print(f'{front} no diff')
                    else:
                        print(f'{front} worse')
    if verbose:
        if start_size:
            print(f'{start_size} -> {end_size} ({100 * end_size / start_size:.1f}%)')
        else:
            print(f'{start_size} -> {end_size} ({100:.1f}%)')


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]) and not os.path.isfile(sys.argv[1]):
            do_many(sys.argv[1], ' '.join(sys.argv[2:]))
        else:
            do(sys.argv[1], ' '.join(sys.argv[2:]))
