import os, sys
import time
from dmgen import filegen
from dmgen import cores
from dmgen import threaded_worker

myhome = os.environ.get('HOMEDRIVE') + os.environ.get('HOMEPATH')
GIFOUT_EXE_PATH = os.path.join(myhome, 'Desktop', 'gifsicle.exe')
def gif(filename, destfilename, options=None):
##    print 'start %s'%filename
    z = os.popen('start /LOW /B /WAIT %s %s %s > "%s"'
                  %(GIFOUT_EXE_PATH, options == None and "-O=3" or options,
                    filename, destfilename))
##    print 'end %s'%filename
    return z

def do_many(files, *options):
    #todo investigate why additional threads doesn't help
    with threaded_worker.threaded_worker(main, min(cores.CORES, 1)) as tw:
        num = 0
        for i in files:
            num += 1
            tw.put(i, *options, alsoreturn=i)
        for i in range(num):
            diff, filename = tw.get()
            filename = filename[0]
            if diff == 0:
                diff = 'smaller'
            else:
                diff = 'not smaller'
            print('%d/%d %s: %s'%(i+1, len(files), diff, filename))

def main(filename, *options):
##    print filename, options
    exitcode = 0
    if filename[-4:].lower() != '.gif': #try recompress
        return 2
    tofilename = filegen.unused_filename('.gif')
    tempcopy_filename = filegen.unused_filename('.gif', folder=os.path.split(filename)[0])
    gif('"%s"'%filename, tofilename, options and ' '.join(options) or None)
    if os.path.exists(tofilename):
        if os.stat(tofilename)[6] < os.stat(filename)[6]:
##            print '%s %s'%(filename, tempcopy_filename)
            os.rename(filename, tempcopy_filename)
            try:
                for i in range(10):
                    try:
                        os.rename(tofilename, filename)
                        break
                    except OSError:
                        time.sleep(0.1)
                else:
                    time.sleep(5)
                    os.rename(tofilename, filename)
            except:
                os.rename(tempcopy_filename, filename)
                raise
            else:
                os.remove(tempcopy_filename)
        else:
            os.remove(tofilename)
            exitcode = 1
    return exitcode

if __name__ == '__main__':
    if len(sys.argv) == 1:
        sys.exit(2)
    try:
        sys.exit(main(*sys.argv[1:]))
    except:
        raise
