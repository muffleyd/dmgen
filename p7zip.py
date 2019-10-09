import os, sys
import shutil
from dmgen import zipgen
from dmgen import filegen
EXE_PATH = '7z'

p7zip_add = 'a'
p7zip_delete = 'd'
p7zip_extract = 'e'
p7zip_update = 'u'
p7zip_xtract = 'x'

if os.name == 'nt':
    PREFIX = 'start /LOW /B /WAIT '
elif os.name == 'posix':
    PREFIX = 'nice -n 19 '
else:
    PREFIX = ''

def _7zip(command, zfilename, *files, **switches):
    raise NotImplementedError()
    a,s,d = os.popen3(PREFIX + ' %s %s -o"%s" "%s"'%(
        EXE_PATH, command, destfolder, zipfile))

def x7zip(zipfile, destfolder=None):
    if not destfolder:
        destfolder = os.path.join(filegen.TEMPfolder or filegen.unused_filename(), os.path.split(zipfile)[1])
    a,s,d = os.popen3('START /LOW /B /WAIT %s x -o"%s" "%s"'%(
        EXE_PATH, destfolder, zipfile))
    return destfolder, s.read(), d.read()

def a7zip(folder, zipfile=None, type='zip', sizecompare=None):
    if not zipfile:
        zipfile = os.path.split(folder)[1] #file with name of source folder at present path
    elif os.path.exists(zipfile) and not os.path.isfile(zipfile): #existing folder
        zipfile = os.path.join(zipfile, os.path.split(folder)[1])
    tempzipfile = filegen.unused_filename('.'+type)
    a,s,d = os.popen3('START /LOW /B /WAIT %s a -t%s -mx9 "%s" "%s"'%(
        EXE_PATH, type, tempzipfile, os.path.join(folder, '*')))
    read = s.read()
##    if os.path.exists(tempzipfile):
##        if os.path.exists(zipfile) and sizecompare:
##            if os.stat(tempzipfile)[6] < sizecompare:
##                os.remove(zipfile)
##                os.rename(tempzipfile, zipfile)
##            else:
##                os.remove(tempzipfile)
    return zipfile, read, d.read()

def re7zip(zipfile, processing=None):
    assert zipfile[-4:].lower() == '.zip', "only does zip files yet"
    tempfolder = filegen.unused_filename(folder=filegen.TEMPfolder)
    tempzipfile = os.path.abspath(filegen.unused_filename(ending='.zip', folder=filegen.TEMPfolder))
    try:
        zipgen.zipunzip(zipfile, destfolder=tempfolder)
        if processing:
            processing(tempfolder)
        a,s,d = os.popen3('START /LOW /B /WAIT %s a -tzip -mx9 "%s" "%s"'%(
            EXE_PATH, tempzipfile, os.path.join(tempfolder, '*')))
        read = s.read()
        if os.path.exists(tempzipfile):
            if os.stat(tempzipfile)[6] < os.stat(zipfile)[6]:
                os.remove(zipfile)
                os.rename(tempzipfile, zipfile)
            else:
                os.remove(tempzipfile)
    except Exception as e:
        print(e)
        raise
    finally:
        if os.path.exists(tempfolder):
            shutil.rmtree(tempfolder)
    return zipfile, read, d.read()

def main():
    if sys.argv[1][-4:].lower() == '.zip':
        re7zip(sys.argv[1])

if __name__ == '__main__':
    main()
