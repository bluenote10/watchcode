from __future__ import division, print_function

from watchcode.matching import matcher_fnmatch


def test_fnmatch():

    def matches(path, pattern):
        assert matcher_fnmatch(path, pattern, None)

    def differs(path, pattern):
        assert not matcher_fnmatch(path, pattern, None)

    matches("test.py", "*.py")
    differs("test.py", "*.txt")

