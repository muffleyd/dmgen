MONITOR2_X = 0  # -1920
MONITOR2_Y = 0


def main():
    import tkinter
    root = tkinter.Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    return width, height



def main_linux_x():
    import subprocess
    output = subprocess.Popen('xrandr | grep "\\*" | cut -d" " -f4',shell=True, stdout=subprocess.PIPE).communicate()[0]
    if isinstance(output, bytes):
        output = output.decode('utf-8')
    main_monitor = output.split('\n')[0]
    width, height = main_monitor.split('x')
    return int(width), int(height)


# untested
def main_mac():
    import AppKit
    return [(screen.frame().size.width, screen.frame().size.height)
            for screen in AppKit.NSScreen.screens()][0]


def main_win():
    import ctypes
    user32 = ctypes.windll.user32
    return (user32.GetSystemMetrics(0), user32.GetSystemMetrics(1),
            user32.GetSystemMetrics(76), user32.GetSystemMetrics(77))


def main():
    import sys
    global WIDTH, HEIGHT, MONITOR2_X, MONITOR2_Y
    mapping = {
        'linux': main_linux_x,
        'win32': main_win,
        'darwin': main_mac
    }
    if function := mapping.get(sys.platform):
        functions = [function, main]
    else:
        functions = [main_win, main_mac, main_linux_x, main]
    result = None
    for function in functions:
        try:
            result = function()
        except:
            continue
        else:
            break
    if not result:
        raise Exception('Could not determine monitor resolution.')
    WIDTH, HEIGHT = result[:2]
    if len(result) == 4:
        MONITOR2_X, MONITOR2_Y = result[2:4]


main()
