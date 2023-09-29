MONITOR2_X = 0  # -1920
MONITOR2_Y = 0


def main():
    import tkinter
    root = tkinter.Tk()
    width = root.winfo_screenwidth()
    height = root.winfo_screenheight()
    return width, height


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


try:
    WIDTH, HEIGHT, MONITOR2_X, MONITOR2_Y = main_win()
except:
    try:
        WIDTH, HEIGHT = main_mac()
    except:
        WIDTH, HEIGHT = main()
