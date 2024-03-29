import os
import shutil
import sys
from . import filegen
from . import pygamegen as pg
from .opt_gif import GIFOUT_EXE_PATH


def explode(file, folder=None):
    if not folder:
        folder = filegen.unused_filename(folder='.')
    os.mkdir(folder)
    tar = os.path.split(file)[1]
    shutil.copy(file, folder)
    folder = os.path.abspath(folder)
    with filegen.switch_dir(folder):
        os.system(f'{GIFOUT_EXE_PATH} -e {tar}')
        os.remove(tar)
        for i in os.listdir('.'):
            f = i.split('.')
            # turns a.b.gif.001 into a.b.001.gif
            os.rename(i, f"{'.'.join(f[:-2])}.{f[-1]}.{f[-2]}")
    return folder


def implode(file, folder, prefix=''):
    temp_filename = filegen.unused_filename('.gif')
    # Implode the gifs inside the directory
    with filegen.switch_dir(folder):
        os.system(f'{GIFOUT_EXE_PATH} -m "{prefix}*.gif" > {temp_filename}')
    # Get the filename from `file` without the file extension.
    tar_base = os.path.splitext(file)[0]
    # Generate the actual output filename, not overwriting an existing file.
    new_filename = f'{tar_base}_r.gif'
    i = 0
    while os.path.exists(new_filename):
        new_filename = f'{tar_base}_r{i}.gif'
        i += 1
    # Move the imploded file to the current directory.
    shutil.move(temp_filename, new_filename)
    return new_filename


def recolor(file, colormod=.5, prefix='m_'):
    if not os.path.isfile(file) and os.path.exists(file):
        # folder
        for i in os.listdir(file):
            recolor(os.path.join(file, i), colormod, prefix)
        return
    if hasattr(file, '__iter__'):
        for i in file:
            recolor(file, colormod, prefix)
        return
    folder, file = os.path.split(file)
    out = prefix + file
    with filegen.switch_dir(folder):
        if colormod < 1:
            colormod = int(len(pg.colors_in(file)) * colormod)
        os.popen(f'{GIFOUT_EXE_PATH} -k {colormod} {file} > {out}' % (colormod, file, out))


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
        os.system(f'{GIFOUT_EXE_PATH} -e {tar}')
        os.remove(tar)
        print('recoloring')
        for ind, filename in enumerate(os.listdir('.')):
            out = f'm_{filename}'
            if not ind:
                shutil.copy(filename, out)
                continue
            if colormod < 1:
                colors = int(len(pg.colors_in(filename)) * colormod)
            else:
                colors = colormod
            os.popen(f'{GIFOUT_EXE_PATH} -k {colors} {filename} > {out}')
        print('imploding')
        os.system(f'{GIFOUT_EXE_PATH} -m m_* > a.gif')
        tar_base = os.path.splitext(tar)[0]
        new = os.path.join(initfolder, f'{tar_base}_r.gif')
        i = 0
        while os.path.exists(new):
            new = os.path.join(initfolder, f'{tar_base}_r{i}.gif')
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
