import os

class DirEntry:
    def __init__(self, path, is_dir=False):
        self.path = path
        self.name = os.path.split(path)[1]
        self._is_dir = is_dir

    def is_dir(self):
        return self._is_dir
