import time, os

class SafeWrite:
    def __init__(self, path, writemode):
        self._path = path
        self._temp_path = self._path + str(time.time())
        self._mode = writemode

    def __enter__(self):
        self._tmpfile = open(self._temp_path, self._mode)
        return self._tmpfile

    def swap(self):
        'Explicitly closes and renames the temporary file.'
        self._tmpfile.close()
        os.rename(self._temp_path, self._path)

    close = swap

    def __exit__(self, errtype, value, traceback):
        if not errtype:
            self.swap()
