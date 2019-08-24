import os, sys
import shutil
import threaded_worker, threading
import gen, zipgen, filegen
myhome = os.path.sep.join(os.environ['TMP'].split(os.path.sep)[:3])
KZIP_EXE_PATH = os.path.join(myhome, 'Desktop', 'kzip.exe')

SWITCHDIR_LOCK = threading.Lock()

def kzip(zipfile, *files):
    if len(files) == 1 and hasattr(files[0], '__iter__'):
        files = files[0]
    a,s,d = os.popen3('START /LOW /B /WAIT %s /r /y "%s" %s'%(
                    KZIP_EXE_PATH, zipfile, ' '.join(['"%s"'%i for i in files])))
    read = s.read()

def rekzip(zipfile):
    with filegen.switch_dir(os.path.split(zipfile)[0]):
        tempfolder = gen.unused_filename(folder=filegen.TEMPfolder)
        tempzipfile = os.path.abspath(gen.unused_filename(ending='.zip', folder=filegen.TEMPfolder))
        try:
            zipgen.zipunzip(zipfile, destfolder=tempfolder)
            with filegen.switch_dir(tempfolder):
                a,s,d = os.popen3('START /LOW /B /WAIT %s /r /y "%s" *'%(
                    KZIP_EXE_PATH, tempzipfile))
            read = s.read()
            if (os.path.exists(tempzipfile) and
                    os.stat(tempzipfile)[6] < os.stat(zipfile)[6]):
                os.remove(zipfile)
                os.rename(tempzipfile, zipfile)
        finally:
            shutil.rmtree(tempfolder)
    return zipfile, read, d.read()

def run(zipfile, tempfolder, tempzipfile):
    try:
        with SWITCHDIR_LOCK:
            zipgen.zipunzip(zipfile, destfolder=tempfolder)
            with filegen.switch_dir(tempfolder):
                a,s,d = os.popen3('START /LOW /B /WAIT %s /r /y "%s" *'%(
                    KZIP_EXE_PATH, tempzipfile))
        read = s.read()
        if os.path.exists(tempzipfile):
            os.remove(zipfile)
            os.rename(tempzipfile, zipfile)
    finally:
        shutil.rmtree(tempfolder)
    return zipfile, read, d.read()

def main():
    with threaded_worker.threaded_worker(run, 2) as tw:
        l = []
        for i in filegen.ifiles_in('C:\\'):
            if i[-4:] == '.zip':
                tarfolder = os.path.abspath(os.path.split(i)[0])
                l.append(tw.put(i, os.path.join(tarfolder, gen.unused_filename(folder=tarfolder)),
                                os.path.join(tarfolder, gen.unused_filename(folder=tarfolder, ending='.zip'))))
        with gen.timer():
            for i in range(len(l)):
                try:
                    name, out, err = tw.get()
                except:
                    continue
                print(name)
                if err:
                    print(err, file=sys.stderr)
if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1][-4:].lower() == '.zip':
            with gen.timer(before='rekzipped in '):
                rekzip(sys.argv[1])
