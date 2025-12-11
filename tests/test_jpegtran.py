import unittest

import os
import contextlib
import tempfile
from dmgen import jpegtran


class JpegtranTest(unittest.TestCase):

    BASE_JPG_FILENAME = os.path.join(os.path.dirname(__file__), '1x1.jpg')
    
    def test_jpegtran(self):
        for optimize in (True, False):
            for options in ('', '-progressive'):
                self.assert_jpegtran_runs(options=options, optimize=optimize)
                self.assert_jpegtran_runs(filename='other_var.jpg', options=options, optimize=optimize)
                self.assert_jpegtran_runs(filename='other$var.jpg', options=options, optimize=optimize)

    def assert_jpegtran_runs(self, filename=None, output_filename=None, options='', optimize=True):
        if filename is not None:
            file = tempfile.NamedTemporaryFile('wb', suffix=filename)
            filename = file.name
            with open(self.BASE_JPG_FILENAME, 'rb') as f:
                file.write(f.read())
            file.flush()
        else:
            filename = self.BASE_JPG_FILENAME
            file = contextlib.nullcontext()
        with file:
            with tempfile.NamedTemporaryFile('wb', suffix=output_filename or '.jpg') as f:
                jpegtran.jpeg(filename, f.name, options, optimize)
                self.assertGreater(os.stat(f.name).st_size, 0)


if __name__ == "__main__":
    unittest.main()
