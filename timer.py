from time import monotonic

class Timer:
    def __init__(self, do_print=True, decimals=3, newline=True, before='', after=''):
        self.do_print = do_print
        self.before_print = before
        self.decimals_print = decimals
        self.after_print = after
        self.newline = newline
        self.runtime = None
        self.start = None

    def get_runtime(self):
        if self.runtime is None:
            raise ValueError('timer still running')
        return self.runtime

    def build_print_string(self):
        # Format runtime to decimal length.
        runtime_fstring = f'{self.runtime:.{self.decimals_print}f}'
        # Format the rest of the string.
        return f'{self.before_print}{runtime_fstring}{self.after_print}'

    def print_me(self, newline=True):
        to_print = self.build_print_string()
        if newline:
            print(to_print)
        else:
            print(to_print, end=' ')

    def __repr__(self):
        return str(self.get_runtime())

    def __enter__(self):
        self.runtime = None
        self.start = monotonic()
        return self

    def __exit__(self, *exc):
        self.runtime = monotonic() - self.start
        self.start = None
        if self.do_print:
            self.print_me()
