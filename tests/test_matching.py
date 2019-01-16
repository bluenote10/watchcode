from __future__ import division, print_function

from watchcode.matching import matcher_fnmatch, matcher_re, matcher_gitlike


def test_fnmatch():

    def matches(path, pattern, is_dir=False):
        assert matcher_fnmatch(path, pattern, is_dir)

    def differs(path, pattern, is_dir=False):
        assert not matcher_fnmatch(path, pattern, is_dir)

    matches("test.py", "*.py")
    differs("test.py", "*.txt")
    matches("./.test.py", "*.py")
    differs("./.test.py", "*.txt")

    differs("test.pyyy", "*.py")

    # don't match on directories
    differs(".", "*", is_dir=True)
    differs("./subdirectory", "*", is_dir=True)


def test_re():

    def matches(path, pattern):
        assert matcher_re(path, pattern, None)

    def differs(path, pattern):
        assert not matcher_re(path, pattern, None)

    matches("test.py", r".*\.py")
    differs("test.py", r".*\.txt")
    matches("./test.py", r".*\.py")
    differs("./test.py", r".*\.txt")

    # Because we use re.search and not re.match...
    # Is this the preferred behavior?
    matches("test.pyyy", r".*\.py")
    differs("test.pyyy", r".*\.py$")


def test_gitlike():

    def matches(path, pattern, is_dir=False):
        assert matcher_gitlike(path, pattern, is_dir)

    def differs(path, pattern, is_dir=False):
        assert not matcher_gitlike(path, pattern, is_dir)

    matches("./test.py", "*.py")

    matches("./.idea", ".idea/", is_dir=True)
