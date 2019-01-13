from __future__ import division, print_function

# Insipred by: https://stackoverflow.com/a/21786287/1804173


class Style(object):
    normal = 0
    bold = 1
    faint = 2
    italic = 3
    underline = 4
    slow_blink = 5
    rapid_blink = 6
    reverse = 7


class FG(object):
    black = 30
    red = 31
    green = 32
    yellow = 33
    blue = 34
    magenta = 35
    cyan = 36
    white = 37


class BG(object):
    black = 40
    red = 41
    green = 42
    yellow = 43
    blue = 44
    magenta = 45
    cyan = 46
    white = 47


def color(fg=None, bg=None, style=None):
    """
    Returns an ANSI color code. If no arguments are specified,
    the reset code is returned.
    """
    fmt_list = [style, fg, bg]
    fmt_list = [str(x) for x in fmt_list if x is not None]
    if len(fmt_list) == 0:
        fmt = "0"
    else:
        fmt = ";".join(fmt_list)
    return "\x1b[{}m".format(fmt)
