import os, gzip
try:
    import tarfile
    from io import StringIO
except ImportError:
    tarfile = None
FILE_APPENDAGE = '.gz'

def handle_tar_gzip(filename, todir=None):
    assert tarfile
    tar = StringIO()
    gzuncompress(filename, tar)
    tf = tarfile.TarFile(fileobj=tar)
    if todir:
        tf.extractall(filename[:-7])
    else:
        tf.extractall()

def gzcompress(filename, gzfilename=None, data=None, removeArchivedFile=False,
              compress_by=9):
    """Compresses 1 file (filename) into a GZIP file.
    """
    if isinstance(filename, str):
        if not os.path.isfile(filename):
            raise IOError('File not found %s.'%filename)
        filename = os.path.abspath(filename)
        if gzfilename is None:
            gzfilename = filename + FILE_APPENDAGE
        file = open(filename, 'rb')
    elif filename is str:
        if data is None:
            raise ValueError('set to write string, must supply string to write!')
        file = None
    else: #a file-like object or bust
        if gzfilename is None:
            if hasattr(filename, 'name'):
                gzfilename = filename + FILE_APPENDAGE
            else:
                UNKNOWN_DESTINATION = ValueError('Destination could not be infered from %s.'%filename)
                raise UNKNOWN_DESTINATION
        file = filename

    if isinstance(gzfilename, gzip.GzipFile):
        zip = gzfilename
    elif isinstance(gzfilename, str):
        zip = gzip.GzipFile(gzfilename, 'w', compress_by)
    else: #a file-like object
        zip = gzip.GzipFile(None, 'w', compress_by, gzfilename)

    try:
        if filename is str:
            zip.write(data)
        else:
            zip.write(file.read())
    except:
        if zip is not gzfilename:
            zip.close()
            if file: #file-like objects cannot be removed,
                os.remove(gzfilename) #only files on disk can be
        raise
    else:
        if zip is not gzfilename:
            zip.close()
    finally:
        if filename is not str:
            file.close()

    if removeArchivedFile and isinstance(filename, str):
        os.remove(filename)
def gzuncompress(gzfile, outputfile=None):
    """gzuncompress(gzfilename[, outputfile=gzfilename[:-3]])

    Extracts file from gzfilename.
    Either arg can be a string filename, or a filetype object, while
    outputfile can be <type 'str'> to return the uncompressed string."""
    #zip will be the GzipFile object made from gzfile
    #out will be the output GzipFile made from outputfile

    if isinstance(gzfile, gzip.GzipFile):
        zip = gzfile
        if outputfile is None:
            outputfile = zip.filename[:-len(FILE_APPENDAGE)]
    elif isinstance(gzfile, str):
        zip = gzip.GzipFile(gzfile, 'r')
        if outputfile is None:
            outputfile = gzfile[:-len(FILE_APPENDAGE)]
    else: #a file-type object or bust
        zip = gzip.GzipFile(fileobj=gzfile)

    if isinstance(outputfile, str):
        out = open(outputfile, 'wb')
        base_path = os.path.split(outputfile)[0]
        if base_path and not os.path.exists(base_path):
            os.makedirs(base_path)
    elif outputfile is str: #will return the string data
        data = zip.read()
        zip.close()
        return data
    else: #a file-type object or bust
        out = outputfile

    try:
        out.write(zip.read())
    except:
        if isinstance(outputfile, str):
            out.close()
            os.remove(outputfile)
    else:
        if isinstance(outputfile, str):
            out.close()
    finally:
        zip.close()
    try:
        out.seek(0)
    except:
        pass
