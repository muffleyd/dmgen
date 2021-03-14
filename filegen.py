import os
import shutil
import random
import hashlib

_walk = os.walk


def extensionis(filename, ext):
    if ext[0] != '.':
        ext = '.' + ext
    return os.path.splitext(filename)[1].lower() == ext.lower()


def search_files(folder, filename='', substr=None, ignorecase=True,
                 maxsize=1073741824):  # one gigabyte
    matches = []
    splitpath = os.path.split
    filename = filename.lower()
    if ignorecase and substr:
        substr = substr.lower()
    for i in files_in(folder):
        if filename in splitpath(i)[-1].lower():
            if substr and os.stat(i)[6] <= maxsize:
                d = open(i, 'rb').read()
                if ignorecase:
                    d = d.lower()
                if substr in d:
                    matches.append(i)
            else:
                matches.append(i)
    return matches


def assert_file_trees(one, two, just_compare_files=0):
    _1 = os.path.exists(one)
    _2 = os.path.exists(two)
    if not _1 or not _2:
        if not _1 and not _2:
            raise Exception("Neither folder provided exists.")
        if not _1:
            raise Exception("Folder '%s' does not exist." % one)
        raise Exception("Folder '%s' does not exist." % two)

    t = _walk(two)
    for i in _walk(one):
        j = next(t)
        if not just_compare_files:
            if j[1] != i[1]:
                raise Exception("Folder lists don't match.", i[0], j[0])
            if j[2] != i[2]:
                raise Exception("File lists don't match.", (i[0], len(i[2])),
                                (j[0], len(j[2])))
        for file in i[2]:
            same, spot = assert_files(os.path.join(i[0], file),
                                      os.path.join(j[0], file))
            if not same:
                raise Exception("Files do not match.", spot,
                                os.path.join(i[0], file),
                                os.path.join(j[0], file))
    return True


class FileOrOpen:
    def __init__(self, file):
        self.file = file
        self.opened_file = False

    def __enter__(self):
        if not hasattr(self.file, 'read'):
            self.opened_file = True
            self.file = open(self.file, 'rb')
        return self.file

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.opened_file:
            self.file.close()


def assert_files(file1, file2, file1_size=None, file2_size=None, start=0):
    if not file1_size:
        file1_size = os.stat(file1)[6]
    if not file2_size:
        file2_size = os.stat(file2)[6]
    if file1_size != file2_size:  # compare file sizes
        return False, 'size'  # max((f1size, f2size))
    CHUNK_SIZE = 163840  # 2**14 times 10
    with FileOrOpen(file1) as f1:
        with FileOrOpen(file2) as f2:
            if start:
                f1.seek(start)
                f2.seek(start)
            for cycles in range(1, (file1_size // CHUNK_SIZE) + 2):
                # print float(cycles) / (f1size // _CHUNKSIZE)
                if f1.read(CHUNK_SIZE) != f2.read(CHUNK_SIZE):
                    return False, (CHUNK_SIZE // cycles) - CHUNK_SIZE
    return True, -1


def copyfile(one, two, mode=None):
    if os.path.exists(one):
        if os.path.isfile(one):
            shutil.copy(one, two)
        else:
            if mode is None:
                os.makedirs(os.path.dirname(two))
            else:
                os.makedirs(os.path.dirname(two), mode)
            shutil.copy(one, two)


def iter_file(file, chunk_size=16384, mode='rb'):
    if isinstance(file, str):  # filename
        file = open(file, mode)
    while 1:
        chunk = file.read(chunk_size)
        if not chunk:
            return
        yield chunk


def files_by_size(files, min_size=1):
    data_sizes = {}  # data_sizes[file_size] -> [filename1, filename2, etc]
    for i in files:
        if not os.path.isfile(i):
            continue
        this_size = os.stat(i)[6]  # six is for size
        if this_size >= min_size:
            data_sizes.setdefault(this_size, []).append(i)
    return data_sizes


def coerce_dir(thing):
    if isinstance(thing, str):
        return files_in(thing)
    return thing


def dict_of_data(files, block_size):
    data = {}
    for file in files:
        with FileOrOpen(file) as file:
            data.setdefault(file.read(block_size), []).append(file)
    return data


def get_duplicate_files(files, min_size=1, BLOCKSIZE=2 ** 14, first_block_size=32):
    files = coerce_dir(files)
    if not first_block_size:
        first_block_size = BLOCKSIZE
    data_sizes = files_by_size(files, min_size)
    positives = []
    # Reads BLOCKSIZE bytes from each file at a time and compares those
    # relatively small strings rather than several whole files.
    # All but needed for comparing large files.
    for size, files in data_sizes.items():
        if len(files) == 1:
            continue
        # reads a small amount first, as most files will be different so read
        # a little amount for a first check..
        data = dict_of_data(files, first_block_size)
        o_files = set()
        for i in data.values():
            if len(i) > 1:  # if the block is not unique in this set of files
                o_files.update(i)
        # ..and then check large blocks at a time
        for i in range(1 + (size - first_block_size) // BLOCKSIZE):
            # data[string] -> [filename1, filename2, etc]
            data = dict_of_data(o_files, BLOCKSIZE)
            for i in data.values():
                if len(i) == 1:  # if the block is unique in this set of files
                    o_files.remove(i[0])
            if not o_files:
                break
        else:
            for i in data.values():
                if len(i) > 1:
                    positives.append([q.name for q in i])
    return positives


# Experiments of different methods that still linger around my computers.
get_duplicate_files3 = get_duplicate_files2 = get_duplicate_files


def get_same_as_file(file, list):
    targetsize = os.stat(file)[6]
    # [6] is for size
    samesizes = [file for file in list if targetsize == os.stat(file)[6]]
    if not samesizes:
        return samesizes  # []
    # TODO Read through files in chunks rather than loading whole files, like below functions do.
    targetdata = open(file, 'rb').read()
    return [file for file in samesizes if open(file, 'rb').read() == targetdata]


def get_same_as_many_files(files1, files2, minsize=1):
    # there's probably some optimization in which list is smaller
    if not files1 or not files2:
        return []
    files1 = coerce_dir(files1)
    files2 = coerce_dir(files2)
    abspath = os.path.abspath
    same_sizes = {}
    files_sizes = {}
    files_set = set()  # prevents comparing a file to itself (same size, afterall!)
    isfile = os.path.isfile
    for i in files1:
        if not isfile(i):
            continue
        files_set.add(abspath(i))  #
        isize = os.stat(i)[6]
        if isize < minsize:
            continue
        same_sizes[isize] = []
        files_sizes.setdefault(isize, []).append(['', i])  # [file data, filename]

    for i in files2:
        if abspath(i) in files_set:
            continue  # don't compare a file to itself
        target_list = same_sizes.get(os.stat(i)[6])
        if target_list is not None:
            target_list.append(i)
    del files_set, files1, files2  # all files are correctly in both dicts, so bye bye!

    for size, files in list(same_sizes.items()):
        if not files:
            del files_sizes[size]
            del same_sizes[size]
    if not same_sizes:  # no files in 'li' are the same size as any in 'files'
        return []
    positives = []
    for target_size, file_info in list(files_sizes.items()):
        for data in file_info:  # do reading of files of size 'target_size' here
            data[0] = open(data[1], 'rb').read()
        for target_filename in same_sizes[target_size]:
            target_data = open(target_filename, 'rb').read()
            for same_size_files in files_sizes.values():
                for file_data, file_name in same_size_files:
                    if target_data == file_data:
                        positives.append((file_name, target_filename))
        for data in file_info:  # release the memory for the read in files
            data[0] = ''
    return positives


def get_same_as_many_files2(files1, files2, minsize=1):
    # there's probably some optimization in which list is smaller
    if not files1 or not files2:
        return []
    files1 = coerce_dir(files1)
    files2 = coerce_dir(files2)
    abspath = os.path.abspath
    isfile = os.path.isfile
    files_sizes = {}
    files_set = {}  # prevents comparing a file to itself (same size, afterall!)
    for i in files1:
        if not isfile(i):
            continue
        isize = os.stat(i)[6]
        if isize < minsize:
            continue
        files_set[abspath(i)] = 1  # see first line of next for loop (for i in li)
        files_sizes.setdefault(isize, ([], []))[0].append(['', i])
        # ([[filedata, filename], [fd2, fn2], [etc]], [same sized files in arg2])

    for i in files2:  # place the filenames
        if not isfile(i) or files_set.get(abspath(i)):
            continue  # don't compare a file to itself
        target_list = files_sizes.get(os.stat(i)[6])
        if target_list is not None:
            target_list[1].append(i)
    del files_set, files1, files2  # all files are correctly in both dicts, so bye bye!

    for j, i in list(files_sizes.items()):
        if not i[1]:  # if no arg2 files are of the same size as arg1 files,
            del files_sizes[j]  # remove it as an option for iteration

    positives = []
    for target_size, files_of_size in files_sizes.items():
        file_info, file_size = files_of_size

        for data in file_info:  # do reading of files of size 'targetsize' here
            data[0] = open(data[1], 'rb').read()
        for target_filename in file_size:
            target_data = open(target_filename, 'rb').read()
            for file_data, filename in file_info:
                if target_data == file_data:
                    positives.append((filename, target_filename))
        for data in file_info:  # release the memory for the read in files
            data[0] = ''
    return positives


def files_in(directory='.', include='', include_end='', exclude=None):  # generator for files_in
    if exclude is None:
        exclude = set()
    elif type(exclude) != set:
        exclude = set(isinstance(exclude, str) and [exclude] or exclude)
    pathsep = os.path.sep
    walker = _walk(directory)
    include_end = include_end.lower()

    # to avoid returning "./filename"
    if not directory or directory == '.':
        for onefile in next(walker)[2]:
            if onefile in exclude or include not in onefile:
                continue
            if include_end:
                if onefile[-len(include_end):].lower() != include_end:
                    continue
            yield onefile

    for current_directory, folders, files in walker:
        if exclude:
            current_directories = current_directory.split(os.path.sep)
        for i in exclude:
            if i in current_directories:
                break
        else:
            for onefile in files:
                if onefile in exclude:
                    continue
                if include_end:
                    if onefile[-len(include_end):].lower() != include_end:
                        continue
                if include in current_directory or include in onefile:
                    yield current_directory + pathsep + onefile


# yields scandir objects for each file in a directory and its children
def files_in_scandir(directory='.', exclude=None):
    if exclude is None:
        exclude = set()
    elif type(exclude) != set:
        exclude = set(isinstance(exclude, str) and [exclude] or exclude)
    if not directory:
        directory = '.'
    for i in _files_in_scandir(directory, exclude):
        yield i


def _files_in_scandir(directory, exclude):
    walker = os.scandir(directory)
    if directory == '.' or not directory:
        directory = ''
    else:
        directory += os.path.sep
    folders = []
    for onefile in walker:
        for e in exclude:
            if e in onefile.name:
                continue
        if onefile.is_dir():
            folders.append(onefile.path)
            continue
        yield onefile
    for dir in folders:
        for i in _files_in_scandir(dir, exclude):
            yield i


def list_folders(directory='.'):
    return (i for i in os.scandir(directory) if i.is_dir())


def list_files(directory='.'):
    return (i for i in os.scandir(directory) if not i.is_dir())


def foldersfiles_in(directory, includes=[], exclude=[]):
    raise NotImplementedError()
    return []


def folder_stats(directory):
    types = {}
    folders = 0
    for i in _walk(directory):
        folders += len(i[1])
        for j in i[2]:
            ext = os.path.splitext(j)[1][1:]
            try:
                types[ext] += 1
            except:
                types[ext] = 1
    return types, folders


class switch_dir:
    def __init__(self, directory):
        self.directory = directory

    def __enter__(self):
        self.previous_directory = os.path.abspath('.')
        if self.directory:  # sometimes it's os.chdir('')
            os.chdir(self.directory)

    def __exit__(self, etype, exc, tb):
        os.chdir(self.previous_directory)


# Sort files by number where the file is like %s.%d.%s
def _renumber_files_sort(files):
    return sorted([i for i in files if isint(os.path.splitext(os.path.split(i)[1])[0])],
                  key=lambda i: int(os.path.splitext(os.path.split(i)[1])[0]))


def isint(what):
    try:
        _ = int(what)
    except ValueError:
        return False
    return True


def renumber_files(files):
    if isinstance(files, str):
        files = [os.path.join(files, i) for i in os.listdir(files)]
    files = _renumber_files_sort(files)
    mod2 = []
    for ind, i in enumerate(files):
        path, file = os.path.split(i)
        num, ext = os.path.splitext(file)
        os.rename(i, os.path.join(path, str(ind + 1) + ext))
    for i in mod2:
        # ?
        pass


# os.path.abspath('/tmp') because windows is allows /tmp
TEMPfolder = os.path.exists('/tmp') and os.path.abspath('/tmp') or os.environ.get('tmp')
allowedchars = 'abcdefghijklmnopqrstuvwxyz0123456789_'


def unused_filename(ending='', donotuse=(), folder='', maxlen=15, start=''):
    if not folder:
        if TEMPfolder:
            folder = TEMPfolder
        else:
            folder = '.'
    generate_characters = max(3, maxlen - len(start) - len(ending))
    rand = random.random
    name = None
    while not name or name in donotuse or name in (i.lower() for i in os.listdir(folder)):
               # ''.join([random.choice(allowedchars)
        name = (start +
                ''.join([allowedchars[int(rand() * len(allowedchars))]
                         for i in range(int(1 + rand() * generate_characters))]) +
                ending)
    if folder and folder != '.':
        name = os.path.join(folder, name)
    return name


##### Work on this thing.
def split_file(file, blocks):
    folder = '.'.join(file.split('.')[:-1])
    if not os.path.exists(folder):
        os.mkdir(folder)
    if os.path.isfile(folder):
        raise ValueError('folder to be created already exists as a file', folder)
    with open(file, 'rb') as a:
        size = int(os.stat(file)[6])
        split_points = [i * (size // blocks) for i in range(blocks)] + [size]
        for i in range(blocks):
            with open(os.path.join(folder, '%s.%s' % (file, str(i))), 'wb') as write:
                write.write(a.read(split_points[i + 1] - split_points[i]))


def merge_files(files, read=2 ** 15):
    with open('.'.join(files[0].split('.')[:-1]), 'wb') as f:
        for i in files:
            r = open(i, 'rb')
            while 1:
                d = r.read(read)
                if not d:
                    r.close()
                    break
                f.write(d)


def hashfile(hash_type, filename, block_size=None):
    h = hash_type()
    block_size = block_size or (h.block_size * 128)
    with open(filename, 'rb') as file:
        while 1:
            bytes = file.read(block_size)
            if not bytes:
                break
            h.update(bytes)
    return h.hexdigest()


def md5file(filename, block_size=None):
    return hashfile(hashlib.md5, filename, block_size)


def sha256file(filename, block_size=None):
    return hashfile(hashlib.sha256, filename, block_size)
