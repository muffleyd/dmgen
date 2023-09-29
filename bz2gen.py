import os
import bz2

FILE_APPENDAGE = '.bz2'


def bz2compress(filename, bz2filename=None, removeArchivedFile=False,
                buffering=None, compress_by=9):
    """Compresses 1 file (filename) into a BZ2 file.
    """
    if not os.path.isfile(filename):
        raise IOError(f'File not found {filename}.')
    filename = os.path.abspath(filename)
    if bz2filename is None:
        bz2filename = filename + FILE_APPENDAGE

    if isinstance(bz2filename, bz2.BZ2File):
        zip = bz2filename
    else:
        zip = bz2.BZ2File(bz2filename, 'w', compresslevel=compress_by)

    try:
        zip.write(open(filename, 'rb').read())
    except:
        if zip is not bz2filename:
            zip.close()
            os.remove(bz2filename)
        raise
    if zip is not bz2filename:
        zip.close()

    if removeArchivedFile:
        os.remove(filename)


def bz2uncompress(bz2filename, outputfile=None, buffering=None):
    """bz2uncompress(bz2filename[, outputfile=bz2filename[:-4]])

    Extracts file from bz2filename."""

    if isinstance(bz2filename, bz2.BZ2File):
        zip = bz2filename
        if outputfile is None:
            outputfile = zip.filename[:-4]
    else:
        zip = bz2.BZ2File(bz2filename, 'r')
        if outputfile is None:
            outputfile = bz2filename[:-4]

    base_path = os.path.split(outputfile)[0]
    if base_path and not os.path.exists(base_path):
        os.makedirs(base_path)
    try:
        out = open(outputfile, 'wb')
        try:
            out.write(zip.read())
        except:
            out.close()
            os.remove(outputfile)
            raise
    finally:
        zip.close()
