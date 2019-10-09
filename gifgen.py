import os
import shutil
import sys
import filegen
from dmgen import pygamegen as pg
from dmgen.opt_gif import GIFOUT_EXE_PATH

def explode(file, folder=None):
    if not folder:
        folder = filegen.unused_filename(folder='.')
    os.mkdir(folder)
    tar = os.path.split(file)[1]
    shutil.copy(file, folder)
    folder = os.path.abspath(folder)
    with filegen.switch_dir(folder):
        os.system(GIFOUT_EXE_PATH + ' -e ' + tar)
        os.remove(tar)
        for i in os.listdir('.'):
            f = i.split('.')
            #turns a.b.gif.001 into a.b.001.gif
            os.rename(i, '.'.join(f[:-2])+'.'+f[-1]+'.'+f[-2])
    return folder

def implode(file, folder, prefix=''):
    with filegen.switch_dir(folder):
        os.system(GIFOUT_EXE_PATH + ' -m %s*.gif > a.gif'%prefix)
    tar_base = os.path.splitext(file)[0]
    new = tar_base + '_r.gif'
    i = 0
    while os.path.exists(new):
        new = tar_base + '_r%d.gif'%i
        i += 1
    os.rename(os.path.join(folder, 'a.gif'), new)
    return new

def recolor(file, colormod=.5, prefix='m_'):
    if not os.path.isfile(file) and os.path.exists(file):
        #folder
        for i in os.listdir(file):
            recolor(os.path.join(file, i), colormod, prefix)
        return
    elif hasattr(file, '__iter__'):
        for i in file:
            recolor(file, colormod, prefix)
        return
    folder, file = os.path.split(file)
    out = prefix + file
    with filegen.switch_dir(folder):
        if colormod < 1:
            colormod = int(len(pg.colors_in(file)) * colormod)
        os.popen(GIFOUT_EXE_PATH + ' -k %d %s > %s'%(colormod, file, out))

def main(file, colormod=.5):
    initfolder, tar = os.path.split(file)
    initfolder = os.path.abspath(initfolder)
    z = filegen.unused_filename()
    os.mkdir(z)
    try:
        shutil.copy(file, z)
        z = os.path.abspath(z)
        os.chdir(z)
        print('exploding')
        os.system(GIFOUT_EXE_PATH + ' -e ' + tar)
        os.remove(tar)
        print('recoloring')
        for ind, i in enumerate(os.listdir('.')):
            out = 'm_' + i
            if not ind:
                shutil.copy(i, out)
                continue
            if colormod < 1:
                colors = int(len(pg.colors_in(i)) * colormod)
            else:
                colors = colormod
            os.popen(GIFOUT_EXE_PATH + ' -k %d %s > %s'%(colors, i, out))
        print('imploding')
        os.system(GIFOUT_EXE_PATH + ' -m m_* > a.gif')
        tar_base = os.path.splitext(tar)[0]
        new = os.path.join(initfolder, tar_base + '_r.gif')
        i = 0
        while os.path.exists(new):
            new = os.path.join(initfolder, tar_base + '_r%d.gif'%i)
            i += 1
        os.rename('a.gif', new)
    finally:
        os.chdir(initfolder)
        shutil.rmtree(z)

if __name__ == '__main__':
    try:
        main(sys.argv[1], float(input('colormod (0.5): ') or .5))
    except:
        import traceback
        traceback.print_exc()
        input('done')
