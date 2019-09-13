import os, zipfile, shutil
from filegen import unused_filename

def zipstr(string, zipfilename, inarchivename=None):
    """string can be a string or a file-like object"""
    if not isinstance(string, str):
        string = string.read()
    if not inarchivename:
        inarchivename = zipfilename[:-4] #assuming it's blah.zip
    with zipfile.ZipFile(zipfilename,
                         os.path.exists(zipfilename) and 'a' or 'w',
                         zipfile.ZIP_DEFLATED) as zip:
        zip.writestr(inarchivename, string)

NOCOMPRESSTYPES = '.gz', '.bz2', '.zip', '.rar', '.png', '.mp3', '.ogg', '.tar'
def zipinsert(filename, zipfilename=None, removeArchivedFile=False,
              includeBase=True, compress=None, dryrun=False):
    """Inserts 1 file/folder (filename) into a ZIP archive.  Creates one if the
        .zip file does not exist.

        compress:
         True: compress everything
         None (default): compress everything except filetype in 'NOCOMPRESSTYPES'
         False: compress nothing
    """
    filename = os.path.abspath(filename)
    if not os.path.exists(filename):
        raise OSError('File does not exist (%s)'%filename)
    if zipfilename is None:
        zipfilename = filename+'.zip'

    #includeBase: True = includes the Folder
    if includeBase:
        if os.path.isfile(filename):
            temp = os.path.split(filename)
            if dryrun:
                print(temp, end=' ')
            BASE, filename = os.path.split(temp[0])
            filename = os.path.join(filename, temp[1])
        else:
            BASE, filename = os.path.split(filename)
    else:
        if os.path.isfile(filename):
            BASE, filename = os.path.split(filename)
        else:
            BASE, filename = filename, ''

    if dryrun:
        print(BASE, filename, '-->', zipfilename)
        _zipinsert(BASE, filename, zipfilename, compress, dryrun)

    else:
        if isinstance(zipfilename, zipfile.ZipFile):
            zip = zipfilename
        else:
            zip = zipfile.ZipFile(zipfilename,
             os.path.exists(zipfilename) and 'a' or 'w',
             zipfile.ZIP_DEFLATED)

        try:
            _zipinsert(BASE, filename, zip, compress)
        except:
            if zip is not zipfilename:
                zip.close()
                os.remove(zipfilename)
                raise
        else:
            if zip is not zipfilename:
                zip.close()

        if removeArchivedFile:
            if os.path.isfile(os.path.join(BASE, filename)):
                os.remove(os.path.join(filename))
            else:
                shutil.rmtree(os.path.join(BASE, filename))

def _zipinsert(BASE, filename, zip, compress, dryrun=False):
#does not ask if you want to replace an already existing file
    totalname = os.path.join(BASE, filename)
    if totalname and totalname[-1] == '\\':
        totalname = totalname[:-1]
##    print totalname
    if dryrun:
        print(totalname, filename)#, not compress and os.path.splitext(filename)[1] in COMPRESSTYPES or False
    isthiszip = os.path.abspath(totalname)
    thiszip = os.path.abspath(dryrun and zip or zip.filename)
    if thiszip == isthiszip:
        return #don't insert yourself into the archive
    if os.path.isfile(totalname):
        if not dryrun:
            if compress is None:
                if os.path.splitext(filename)[1] in NOCOMPRESSTYPES:
                    c = zipfile.ZIP_STORED
                else:
                    c = zipfile.ZIP_DEFLATED
            elif compress is False:
                c = zipfile.ZIP_STORED
            else:
                c = zipfile.ZIP_DEFLATED
            zip.write(totalname, filename, c)
    else:
        for i in os.listdir(totalname):
            _zipinsert(BASE, os.path.join(filename, i), zip, compress, dryrun)

def zipcompressionof(what):
    return max(i.compress_type for i in what.infolist())

def zipremove(zipfilename, *stufftoremove):
#if the end result is no files in zipfile, remove the zipfile
#this rewrites the whole .zip file, can't just remove pieces /sigh
    """Removes files from a zip file."""
    with zipfile.ZipFile(zipfilename) as zip:
        comp = zipcompressionof(zip)
        stufftokeep = zip.namelist()
        for i in stufftoremove:
            try:
                stufftokeep.remove(i)
            except ValueError:
                pass
        if stufftokeep == zip.namelist(): #what is to be removed isn't in here
            return
        with zipfile.ZipFile(unused_filename('.zip'), 'w', comp, zip._allowZip64) as zip2:
            for i in stufftokeep:
                if i[-1] == '/': #it's a folder!
                    continue
                zip2.writestr(i, zip.read(i))
    shutil.move(zip2.filename, zipfilename)

def zipunzip(zipfilename, files=None, destfolder='.'):
    """zipunzip(zipfilename[, files=everything])

    Extracts files from zipfilename."""

    base_path, filename = os.path.split(zipfilename)
    base_path = os.path.join(base_path, destfolder)
    with zipfile.ZipFile(zipfilename) as zip:
        if files is None:
            files = zip.namelist()

        if not os.path.exists(base_path):
            os.makedirs(base_path)
        for i in files:
            if i.split('/')[-1]:
                zip.extract(i, base_path)
