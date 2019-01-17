from __future__ import division, print_function

import os
from watchcode.matching import matcher_fnmatch, matcher_re, matcher_gitlike, is_gitignore


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


def verify_gitignore_rules(matches, differs):
    matches("*.log", "./test.log")
    matches("*.log", "./.log")
    matches("*.log", "./sub/.hidden.log")
    differs("*.log", "./test.log.suffix")

    matches("/*.log", "./test.log")
    matches("/*.log", "./.log")
    differs("/*.log", "./sub/.hidden.log")
    differs("/*.log", "./test.log.suffix")

    differs("/sub/*.log", "./test.log")
    differs("/sub/*.log", "./.log")
    matches("/sub/*.log", "./sub/.hidden.log")
    differs("/sub/*.log", "./other/sub/test.log")

    matches("cache/", "./cache/test")
    matches("cache/", "./cache/sub/test")
    matches("cache/", "./sub/cache/test")
    differs("cache/", "./cache")

    matches("/cache/", "./cache/test")
    matches("/cache/", "./cache/sub/test")
    differs("/cache/", "./sub/cache/test")
    differs("/cache/", "./cache")

    matches("", "./.git/lock")


def test_gitlike(tmpdir):
    with tmpdir.as_cwd():
        os.system("git init")

    def reference(path, pattern, is_dir):
        with tmpdir.as_cwd():
            with open(".gitignore", "w") as f:
                f.write(pattern)
            #res = os.system("git ")
            return is_gitignore(path)

    def matches(pattern, path, is_dir=False):
        assert matcher_gitlike(path, pattern, is_dir)

    def differs(pattern, path, is_dir=False):
        assert not matcher_gitlike(path, pattern, is_dir)

    verify_gitignore_rules(matches, differs)


def test_is_gitignore(tmpdir):

    def set_gitignore(pattern):
        with open(".gitignore", "w") as f:
            f.write(pattern)

    def matches(pattern, path):
        set_gitignore(pattern)
        assert is_gitignore(path), \
            "assert pattern '{}' matches to path '{}'".format(pattern, path)

    def differs(pattern, path):
        set_gitignore(pattern)
        assert not is_gitignore(path), \
            "assert pattern '{}' does not match to path '{}'".format(pattern, path)

    with tmpdir.as_cwd():
        os.system("git init")
        verify_gitignore_rules(matches, differs)
