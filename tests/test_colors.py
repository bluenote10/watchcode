from __future__ import division, print_function

import watchcode.colors as colors


def test_color():
    assert colors.color() == "\033[0m"
    assert colors.color(30, 40, 0) == "\033[0;30;40m"
    