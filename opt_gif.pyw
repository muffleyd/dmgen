import os, sys
import filegen

myhome = os.path.sep.join(os.environ['TMP'].split(os.path.sep)[:3])
GIFOUT_EXE_PATH = os.path.join(myhome, 'Desktop', 'gifsicle.exe')
def gif(filename, destfilename, options=None):
    z = os.popen3('start /LOW /B /WAIT %s %s %s > "%s"'
                  %(GIFOUT_EXE_PATH, options == None and "-O=3" or options,
                    filename, destfilename))
    return z

def main(filename, *options):
    exitcode = 0
    if filename[-4:].lower() != '.gif': #try recompress
        return 1
    tofilename = filegen.unused_filename('.gif', folder=os.path.dirname(filename) or '.')
    gif('"%s"'%filename, tofilename, options and ' '.join(options) or None)
    if os.path.exists(tofilename):
        if os.stat(tofilename)[6] < os.stat(filename)[6]:
            os.remove(filename)
            os.rename(tofilename, filename)
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
