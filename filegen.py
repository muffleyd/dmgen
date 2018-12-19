import os, shutil
import Queue
import random
#defaultdict in these things below doesn't speed up any
from itertools import chain
import threaded_worker
import hashlib

def extensionis(filename, ext):
    if ext[0] != '.':
        ext = '.' + ext
    return os.path.splitext(filename)[1].lower() == ext.lower()

def search_files(folder, filename='', substr=None, ignorecase=True,
                 maxsize=1073741824): #one gigabyte
    yes = []
    splitpath = os.path.split
    filename = filename.lower()
    if ignorecase and substr:
        substr = substr.lower()
    for i in ifiles_in(folder):
        if filename in splitpath(i)[-1].lower():
            if substr and os.stat(i)[6] <= maxsize:
                d = open(i, 'rb').read()
                if ignorecase:
                    d = d.lower()
                if substr in d:
                    yes.append(i)
            else:
                yes.append(i)
    return yes


def _read2():#fileo, num, type='b'): #'b' for bits, 'B' for Bytes
    tbyte = ''
    data = ''
    while 1:
        self, num, type = yield data
        print self, num, type
_read2 = _read2().send
_read2(None)
##def read2(fileo, num, type='b'):
##    return _read2((fileo, num, type))
class open2(file):
    """open2(name[, mode[, buffering]])"""
    def read2(self, num, type='b'):
        return _read2((self, num, type))

##file.read2 = read2

def rewrite_file(filename):
    """for the love of god, don't use this on any important files"""
    print "for the love of god, don't use this on any important files"
    global rewrite_file
    rewrite_file = _rewrite_file
    _rewrite_file(filename)
def _rewrite_file(filename):
    z = open(filename, 'rb').read()
    temp = unused_filename()
    q = open(temp, 'wb')
    q.write(z)
    q.close()
    os.remove(filename)
    os.rename(temp, filename)

def assert_file_trees(one, two, justcomparefiles=0):
    _1 = os.path.exists(one)
    _2 = os.path.exists(two)
    if not _1 or not _2:
        if not _1 and not _2:
            raise Exception("Neither folder provided exists.")
        if not _1:
            raise Exception("Folder '%s' does not exist."%one)
        raise Exception("Folder '%s' does not exist."%two)

    t = os.walk(two)
    for i in os.walk(one):
        j = t.next()
        if not justcomparefiles:
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

def assert_files(file1, file2, f1size=None, f2size=None, start=0):
    if not f1size:
        f1size = os.stat(file1)[6]
    if not f2size:
        f2size = os.stat(file2)[6]
    if f1size != f2size: #compare file sizes
        return False, 'size'#max((f1size, f2size))
    _CHUNKSIZE = 163840 #2**14 and a 0
    if not hasattr(file1, 'read'):
        f1 = open(file1, 'rb')
    else:
        f1 = file1
    if not hasattr(file2, 'read'):
        f2 = open(file2, 'rb')
    else:
        f2 = file2
    if start:
        f1.seek(start)
        f2.seek(start)
    for cycles in xrange(1, (f1size / _CHUNKSIZE) + 2):
##        print float(cycles) / (f1size / _CHUNKSIZE)
        if f1.read(_CHUNKSIZE) != f2.read(_CHUNKSIZE):
            return False, (_CHUNKSIZE/cycles)-_CHUNKSIZE
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

def resetfile(file):
    b = readfile(file,'b')
    a = open(file, 'wb')
    a.write(b)
    a.close()
def readfile(file, mode=''):
    return open(file, 'r'+mode).read().replace('\r\n', '\n').replace('\r', '\n')

def replaceinfile(filename, str1, strrep):
    a = open(filename)
    b = a.read().replace(str1, strrep)
    a.close()
    a = open(filename, 'w')
    a.write(b)
    a.close()

def iter_file(file, chunksize=16384, filelen=None):
    if isinstance(file, str): #filename
        if filelen is None:
            filelen = int(os.stat(file)[6])
        file = open(file, 'rb')
    #file must now be a file-like object
    elif filelen is None:
        raise ValueError("File size must be given for file-like object.")

    for cycles in xrange(1, int(filelen / chunksize) + 2):
        yield file.read(chunksize)

def _get_duplicate_filesS(li, minsize=1):
    datasizes = {} #datasizes[file_size] -> [filename1, filename2, etc]
    for i in li:
        if not os.path.isfile(i):
            continue
        thissize = os.stat(i)[6] #six is for size
        if thissize >= minsize:
            datasizes.setdefault(thissize, []).append(i)
    return datasizes

def coerce_dir(thing):
    if isinstance(thing, basestring):
        return ifiles_in(thing)
    return thing

def dict_of_data(files, blocksize, doopen=False):
    if doopen:
        files = [open(file, 'rb') for file in files]
    data = {}
    for file in files:
        data.setdefault(file.read(blocksize), []).append(file)
    return data

def get_duplicate_files(li, minsize=1, BLOCKSIZE=2**14, firstblocksize=32):
    li = coerce_dir(li)
    if not firstblocksize:
        firstblocksize = BLOCKSIZE
    datasizes = _get_duplicate_filesS(li, minsize)
    positives = []
    #Reads BLOCKSIZE bytes from each file at a time and compares those
    #relatively small strings rather than several whole files.
    #All but needed for comparing large files.
    for size, files in datasizes.iteritems():
        if len(files) == 1:
            continue
        #reads a small amount first, as most files will be different so read
        #a little amount for a first check..
        data = dict_of_data(files, firstblocksize, True)
        o_files = set()
        for i in data.itervalues():
            if len(i) > 1: #if the block is not unique in this set of files
                o_files.update(i)
        #..and then check large blocks at a time
        for i in xrange(1 + (size - firstblocksize) / BLOCKSIZE):
            #data[string] -> [filename1, filename2, etc]
            data = dict_of_data(o_files, BLOCKSIZE)
            for i in data.itervalues():
                if len(i) == 1: #if the block is unique in this set of files
                    o_files.remove(i[0])
            if not o_files:
                break
        else:
            for i in data.itervalues():
                if len(i) > 1:
                    positives.append([q.name for q in i])
    return positives
get_duplicate_files3 = get_duplicate_files2 = get_duplicate_files

def get_same_as_file(f1, li):
    targetsize = os.stat(f1)[6]
    #[6] is for size
    samesizes = [file for file in li if targetsize == os.stat(file)[6]]
    if not samesizes:
        return samesizes #[]
    targetdata = open(f1, 'rb').read()
    return [file for file in samesizes if open(file, 'rb').read() == targetdata]

def get_same_as_many_files(files, li, minsize=1): #def get_same_as_many_files2(files, li):
    #there's probably some optimization in which list is smaller
    if not files or not li:
        return []
    files = coerce_dir(files)
    li = coerce_dir(li)
    abspath = os.path.abspath
    samesizes = {}
    filessizes = {}
    filesset = set() #prevents comparing a file to itself (same size, afterall!)
    isfile = os.path.isfile
    for i in files:
        if not isfile(i):
            continue
        filesset.add(abspath(i)) #
        isize = os.stat(i)[6]
        if isize < minsize:
            continue
        samesizes[isize] = []
        filessizes.setdefault(isize, []).append(['', i])#[file data, filename]
    
    for i in li:
        if abspath(i) in filesset:
            continue #don't compare a file to itself
        targetlist = samesizes.get(os.stat(i)[6])
        if targetlist < minsize: # [] < 1, or ['a.txt'] < 1 ?  ummm, wut
            continue
        if targetlist is not None:
            targetlist.append(i)
    del filesset, files, li #all files are correctly in both dicts, so bye bye!

    for j,i in samesizes.items():
        if not i:
            del filessizes[j]
            del samesizes[j]
    if not samesizes: #no files in 'li' are the same size as any in 'files'
        return []
    positives = []
    for targetsize, filenames in filessizes.items():
        for data in filenames: #do reading of files of size 'targetsize' here
            data[0] = open(data[1],'rb').read()
        for targetfilename in samesizes[targetsize]:
            targetdata = open(targetfilename,'rb').read()
            for filess in filessizes.itervalues():
                for filesdata, filesname in filess: #filess... comeon..
                    if targetdata == filesdata:
                        positives.append((filesname, targetfilename))
        for data in filenames: #release the memory for the read in files
            data[0] = ''
    return positives
def get_same_as_many_files2(files, li, minsize=1):
    #there's probably some optimization in which list is smaller
    if not files or not li:
        return []
    files = coerce_dir(files)
    li = coerce_dir(li)
    abspath = os.path.abspath
    isfile = os.path.isfile
    filessizes = {}
    filesset = {} #prevents comparing a file to itself (same size, afterall!)
    for i in files:
        if not isfile(i):
            continue
        isize = os.stat(i)[6]
        if isize < minsize:
            continue
        filesset[abspath(i)] = 1 #see first line of next for loop (for i in li)
        filessizes.setdefault(isize, ([], []))[0].append(['', i])
        #([[filedata, filename], [fd2, fn2], [etc]], [same sized files in arg2])
    
    for i in li: #place the filenames
        if not isfile(i) or filesset.get(abspath(i)):
            continue #don't compare a file to itself
        targetlist = filessizes.get(os.stat(i)[6])
        if targetlist < minsize:
            continue
        if targetlist is not None:
            targetlist[1].append(i)
    del filesset, files, li #all files are correctly in both dicts, so bye bye!

    for j, i in filessizes.items():
        if not i[1]: #if no arg2 files are of the same size as arg1 files,
            del filessizes[j] #remove it as an option for iteration

    positives = []
    for targetsize, filesofsize in filessizes.iteritems():
        fileinfo, filesize = filesofsize

        for data in fileinfo: #do reading of files of size 'targetsize' here
            data[0] = open(data[1],'rb').read()
        for targetfilename in filesize:
            targetdata = open(targetfilename,'rb').read()
            for filedata, filename in fileinfo:
                if targetdata == filedata:
                    positives.append((filename, targetfilename))
        for data in fileinfo: #release the memory for the read in files
            data[0] = ''
    return positives

def makedirs(*dirs):
    for dir in dirs:
        if hasattr(dir, '__iter__'):
            dir = os.path.join(*dir)
        if not os.path.exists(dir):
            os.makedirs(dir)

ENABLE_SCANDIR = True
scandir = False
if ENABLE_SCANDIR:
    try:
        import scandir
    except ImportError:
        scandir = False

def ifiles_in(directory='.', include='', includeend='', exclude=[]): #generator for files_in
    if type(exclude) != set:
        exclude = set(isinstance(exclude, basestring) and [exclude] or exclude)
    pathsep = os.path.sep
    if scandir:
        walker = scandir.walk(directory)
    else:
        walker = os.walk(directory)
    includeend = includeend.lower()

    #to avoid returning "./filename"
    if not directory or directory == '.':
        for onefile in next(walker)[2]:
            if onefile in exclude or include not in onefile:
                continue
            if includeend:
                if onefile[-len(includeend):].lower() != includeend:
                    continue
            yield onefile

    for curdir, folders, files in walker:
        if exclude:
            curdirs = curdir.split(os.path.sep)
        for i in exclude:
            if i in curdirs:
                break
        else:
            for onefile in files:
                if onefile in exclude:
                    continue
                if includeend:
                    if onefile[-len(includeend):].lower() != includeend:
                        continue
                if include in curdir or include in onefile:
                    yield curdir + pathsep + onefile

def files_in(directory='', exclude=[]):
    #returns a list of every file in directory and it's subdirectories
    return list(ifiles_in(directory, '','', exclude))

def listfolders(directory='.'):
    path = os.path
    return [i for i in os.listdir(directory) if not path.isfile(path.join(directory, i))]
def listfiles(directory='.'):
    return [i for i in os.listdir(directory) if os.path.isfile(os.path.join(directory, i))]

def ifoldersfiles_in(directory, includes=[], exclude=[]):
    raise NotImplementedError()
    return []

def foldersfiles_in(directory='', includes=[], exclude=[]):
    return list(ifoldersfiles_in(directory, includes, exclude))

def folder_stats(directory):
    types = {}
    folders = 0
    for i in os.walk(directory):
        folders += len(i[1])
        for j in i[2]:
            ext = os.path.splitext(j)[1][1:]
            try:
                types[ext] += 1
            except:
                types[ext] = 1
    return types,folders

class switch_dir:
    def __init__(self, dirname):
        self.dirname = dirname
    def __enter__(self):
        self.prevdir = os.path.abspath('.')
        if self.dirname: #sometimes it's os.chdir('')
            os.chdir(self.dirname)
    def __exit__(self, etype, exc, tb):
        os.chdir(self.prevdir)

def _renumber_files_sort(files):
    return sorted([i for i in files if isint(os.path.splitext(os.path.split(i)[1])[0])],
                  key=lambda i:int(os.path.splitext(os.path.split(i)[1])[0]))
def isint(what):
    try:
        _=int(what)
    except ValueError:
        return False
    return True
def renumber_files(files):
    if isinstance(files, basestring):
        files = [os.path.join(files, i) for i in os.listdir(files)]
    files = _renumber_files_sort(files)
    mod2 = []
    for ind, i in enumerate(files):
        path, file = os.path.split(i)
        num, ext = os.path.splitext(file)
        os.rename(i, os.path.join(path, str(ind+1)+ext))
    for i in mod2:
        pass

#os.path.abspath('/tmp') because windows is allows /tmp
TEMPfolder = os.path.exists('/tmp') and os.path.abspath('/tmp') or os.environ.get('tmp')
allowedchars = 'abcdefghijklmnopqrstuvwxyz0123456789_'
def unused_filename(ending='', donotuse=(), folder='', maxlen=15, start=''):
    if not folder:
        if TEMPfolder:
            folder = TEMPfolder
        else:
            folder = '.'
    numgenerate = max(3, maxlen - len(start) - len(ending))
    rand = random.random
    name = None
    while (not name or name in donotuse or name in (i.lower() for i in os.listdir(folder))):
##               ''.join([random.choice(allowedchars)
        name = (start +
                ''.join([allowedchars[int(rand() * len(allowedchars))]
                         for i in xrange(int(1 + rand() * numgenerate))]) +
                ending)
    if folder and folder != '.':
        name = os.path.join(folder, name)
    return name

#####work on this thing
def split_file(what, many): 
    a = open(what, 'rb')
    try:
        size = int(os.stat(what)[6])
        splitpoints = [i * (size / many) for i in xrange(many)] + [size]
        folder = '.'.join(what.split('.')[:-1])
        if not os.path.exists(folder):
            os.mkdir(folder)
        if os.path.isfile(folder):
            raise ValueError('folder to be created already exists as a file',folder)
        for i in xrange(many):
            with open(os.path.join(folder, '%s.%s'%(what, str(i))), 'wb') as write:
                write.write(a.read(splitpoints[i+1] - splitpoints[i]))
    finally:
        a.close()

def merge_files(what, read=2**15):
    with open('.'.join(what[0].split('.')[:-1]), 'wb') as f:
        for i in what:
            r = open(i, 'rb')
            while 1:
                d = r.read(read)
                if not d:
                    r.close()
                    break
                f.write(d)

def md5file(filename):
    h = hashlib.md5()
    block = h.block_size * 128
    with open(filename, 'rb') as f:
        while 1:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()
