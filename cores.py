import os
import sys


def main():
    num = os.cpu_count()
    if not num:
        num = main_backup()
    return num


def main_backup():
    num = 1
    if sys.platform == 'win32':  # windows
        try:
            num = int(os.environ['NUMBER_OF_PROCESSORS'])
        except (ValueError, KeyError):
            pass
    elif sys.platform == 'darwin':  # mac os x
        try:
            num = int(os.popen('sysctl -n hw.ncpu').read())
        except ValueError:
            pass
    else:  # *unix
        try:
            num = os.sysconf('SC_NPROCESSORS_ONLN')
        except (ValueError, OSError, AttributeError):
            pass
    return num


CORES = main()
