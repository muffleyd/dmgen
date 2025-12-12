import unittest

import os
import contextlib
import tempfile
from dmgen import oxipng


option_sets = {
    '--foo bar --bar --spam --eggs 1': {
        '--foo': 'bar',
        '--bar': True,
        '--spam': True,
        '--eggs': '1',
    },
    '-p --spam --eggs': {
        '-p': True,
        '--spam': True,
        '--eggs': True,
    },
    '': {},
}


class OxipngTest(unittest.TestCase):
    def test_string_to_options(self):
        for option_string, option_dict in option_sets.items():
            self.assertEqual(oxipng.string_to_options(option_string), option_dict, option_string)
        self.assertEqual(oxipng.string_to_options('--foo  1'), {'--foo': '1'}, 'Extra space handled.')
    
    def test_options_to_string(self):
        for option_string, option_dict in option_sets.items():
            self.assertEqual(oxipng.options_to_string(option_dict), option_string, option_string)
            self.assertEqual(oxipng.options_to_string(option_string), option_string, option_string)
        self.assertEqual(oxipng.options_to_string(None), '')
        with self.assertRaises(ValueError, msg='Invalid type.'):
            oxipng.options_to_string(['--foo'])

    BASE_PNG_FILENAME = os.path.join(os.path.dirname(__file__), '1x1.png')
    
    def test_oxipng(self):
        options = {
            '-o': 0,
            '--zc': 0,
        }
        self.assert_oxipng_runs(filename='other$var.png', options=options, optimize=False)

    def assert_oxipng_runs(self, filename=None, options='', optimize=True):
        if filename is not None:
            file = tempfile.NamedTemporaryFile('wb', suffix=filename)
            filename = file.name
            with open(self.BASE_PNG_FILENAME, 'rb') as f:
                file.write(f.read())
            file.flush()
        else:
            filename = self.BASE_PNG_FILENAME
            file = contextlib.nullcontext()
        with file:
            return_code, stdout, stderr = oxipng.oxipng(filename, options, optimize)
            self.assertGreater(len(stdout), 0)


if __name__ == "__main__":
    unittest.main()
