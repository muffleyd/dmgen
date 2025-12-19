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


VERBOSE = False


OXIPNG_EXE_PATH = shutil.which('oxipng') or ''
if not os.path.exists(OXIPNG_EXE_PATH) and os.name == 'nt':
    myhome = os.environ.get('HOME') or os.environ.get('USERPROFILE')
    OXIPNG_EXE_PATH = os.path.join(myhome, 'Desktop', 'oxipng.exe')
if not os.path.exists(OXIPNG_EXE_PATH):
    import warnings
    EXE_MISSING = 'oxipng executable not found, set variable `OXIPNG_EXE_PATH` as file location'
    warnings.warn(EXE_MISSING, Warning)

# Process priority (windows and linux).
if os.name == 'nt':
    PREFIX = 'start /LOW /B /WAIT'
elif os.name == 'posix':
    PREFIX = 'nice -n 19'
else:
    PREFIX = ''


def oxipng(filename, options=None, optimize=True):
    # handle options spacing + slashes yourself please
    """Runs oxipng on filename to output_filename (if given, else it's smart).
    Fill this out with the oxipng executable options."""
    if not OXIPNG_EXE_PATH:
        raise FileNotFoundError('OXIPNG_EXE_PATH not set')
    if not options:
        options = {}
    if optimize:
        if '-s' not in options and '--strip' not in options:
            options['-s'] = True
        # if '-o' not in options:
        #     options['-o'] = 6
        if '-f' not in options:
            options['-f'] = 9
        if '--zc' not in options:
            options['--zc'] = 12
        if '--brute-level' not in options:
            options['--brute-level'] = 5
        if '--brute-lines' not in options:
            options['--brute-lines'] = 16
    if VERBOSE:
        options['-vv'] = True
    out = (
        f'{PREFIX} {OXIPNG_EXE_PATH} {options_to_string(options)} --force --stdout -'
    )
    out = [i for i in [
        *(PREFIX.split(' ')),
        OXIPNG_EXE_PATH,
        *(options_to_string(options).split(' ')),
        '--force',
        '--stdout',
        '-'
    ] if i]
    if VERBOSE:
        print(out)
    with open(filename, 'rb') as input_object:
        proc = subprocess.run(out, stdin=input_object, capture_output=True, check=False)
    if VERBOSE:
        print('success' if proc.returncode == 0 else 'error', len(proc.stdout), len(proc.stderr))
        print(proc.stderr)
    return proc.returncode, proc.stdout, proc.stderr


def options_to_string(options):
    if isinstance(options, dict):
        # Convert {'-i': 'off', '-s': True} to '-i off -s'
        return ' '.join(f'{key}{f" {value}" if value is not True else ""}' for key, value in options.items())
    if isinstance(options, str):
        return options
    if not options:
        return ''
    raise ValueError('Unknown options type.')


def string_to_options(options: str) -> dict:
    options_dict = {}
    options = options.strip()
    if not options:
        return options_dict
    key = None
    for option in (options + ' -').split(' '):
        if not option:
            continue
        if not key:
            key = option
        elif option[0] == '-':
            options_dict[key] = True
            key = option
        else:
            options_dict[key] = option
            key = None
    return options_dict


def validate_image(one, two):
    if VERBOSE:
        print('validating images')
    if not CAN_VALIDATE:
        raise Exception('Required packages for validation are not found.')
    one.seek(0)
    image_one = pygame.image.load(one)
    two = BytesIO(two)
    two.seek(0)
    image_two = pygame.image.load(two, '.png')
    same = compare_surfs(image_one, image_two)
    return same


def do(input_filename, output_filename=None, options=None, validate=True):
    if hasattr(input_filename, 'stat'):
        stat = input_filename.stat()
        input_filename = input_filename.path
    else:
        stat = os.stat(input_filename)
    file_times = (
        stat.st_atime_ns,
        stat.st_mtime_ns,
    )
    if output_filename is None:
        output_filename = input_filename
    initial_size = size = stat[6]
    # TODO:
    #  Run with and without -z. -z is usually but not alawys better, running both adds ~15% runtime.
    #  Run with various --brute-lines values. Not predictable, large impact.
    error, output, stderr = oxipng(input_filename, options)
    if error:
        raise Exception(f'Error while processing file "{input_filename}" -> "{options}"\n{stderr}')
    new_size = len(output)
    if VERBOSE:
        print(new_size, size)
    if new_size and new_size < size:
        if validate:
            with open(input_filename, 'rb') as file_object:
                if not validate_image(file_object, output):
                    raise Exception(f'Processed file is not identical to source file: {input_filename}')
        if os.path.exists(output_filename):
            if VERBOSE:
                print('overwriting')
            with tempfile.NamedTemporaryFile() as temp_file:
                temp_file.write(output)
                os.utime(temp_file.name, ns=file_times)
                shutil.move(temp_file.name, output_filename)
        else:
            if VERBOSE:
                print('writing')
            with open(output_filename, 'wb') as output_file:
                output_file.write(output)
            os.utime(output_filename, ns=file_times)
        if VERBOSE:
            print('done')
        size = new_size

    return input_filename, initial_size, new_size


def do_many(files, options=None, threads=None, verbose=True):
    # do_many_yield yields everything, this only returns all the exceptions.
    return [
        (filename, *exception)
        for filename, exception
        in do_many_yield(files, options, threads, verbose)
        if exception
    ]


def do_many_yield(files, options=None, threads=None, verbose=True):
    # global worker #global for debugging purposes
    if isinstance(files, str):
        files = filegen.files_in_scandir(files)
    if not threads:
        threads = CORES
    todo = []
    start_size = end_size = 0
    with threaded_worker.threaded_worker(do, threads, wait_at_end=True) as worker:
        for filename in files:
            todo.append((filename, worker.put(filename, None, options)))
        total = len(todo)
        if verbose:
            print(f'0/{total}')
        for x in range(total):
            index = worker.get_completed_index()
            filename, _ = todo[index - 1]
            try:
                filename, size, new_size = worker.get(index)
            except Exception as e:
                print(str(e)[:80])
                print(traceback.format_exc())
                yield filename, (e, traceback.format_exc())
                continue
            yield filename, None
            if new_size < size:
                end_size += new_size
                start_size += size
            if verbose:
                front = f'{x + 1}/{total} {filename}:'
                if new_size < size:
                    print(f'{front} {new_size - size} {100 * new_size / size:.1f}%')
                elif new_size == size:
                    print(f'{front} no diff')
                else:
                    print(f'{front} worse ({new_size} > {size})')
    if verbose:
        if start_size:
            print(f'{start_size} -> {end_size} ({100 * end_size / start_size:.1f}%)')
        else:
            print(f'{start_size} -> {end_size} ({100:.1f}%)')


if __name__ == '__main__':
    import sys

    if len(sys.argv) > 1:
        if os.path.exists(sys.argv[1]) and not os.path.isfile(sys.argv[1]):
            do_many(sys.argv[1], string_to_options(' '.join(sys.argv[2:])))
        else:
            do(sys.argv[1], None, string_to_options(' '.join(sys.argv[2:])))
