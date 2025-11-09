import unittest

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
}


class OxipngTest(unittest.TestCase):
    def test_string_to_options(self):
        for option_string, option_dict in option_sets.items():
            self.assertEqual(oxipng.string_to_options(option_string), option_dict, option_string)
    
    def test_options_to_string(self):
        for option_string, option_dict in option_sets.items():
            self.assertEqual(oxipng.options_to_string(option_dict), option_string, option_string)

if __name__ == "__main__":
    unittest.main()
