from __future__ import division, print_function

import os
from watchcode.trigger import FileEvent
from watchcode.matching import matcher_fnmatch, matcher_re, matcher_gitlike, is_gitignore


def define_matches_and_differs(func):

    def matches(pattern, path, is_dir=False):
        event = FileEvent(path, "modified", is_dir)
        assert func(pattern, event), \
            "pattern '{}' must match path: '{}'".format(pattern, path)

    def differs(pattern, path, is_dir=False):
        event = FileEvent(path, "modified", is_dir)
        assert not func(pattern, event), \
            "pattern '{}' must NOT match path: '{}'".format(pattern, path)

    return matches, differs


def test_fnmatch():

    matches, differs = define_matches_and_differs(matcher_fnmatch)

    matches("*.py", "test.py")
    differs("*.xx", "test.py", )
    matches("*.py", "./.test.py")
    differs("*.txt", "./.test.py")

    differs("*.py", "test.pyyy")

    # don't match on directories
    differs("*", ".", is_dir=True)
    differs("*", "./subdirectory", is_dir=True)


def test_re():

    matches, differs = define_matches_and_differs(matcher_re)

    matches(r".*\.py", "test.py")
    differs(r".*\.txt", "test.py")
    matches(r".*\.py", "./test.py")
    differs(r".*\.txt", "./test.py")

    # Because we use re.search and not re.match...
    # Is this the preferred behavior?
    matches(r".*\.py", "test.pyyy")
    differs(r".*\.py$", "test.pyyy")


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
        os.system("git init --quiet")

    def reference(path, pattern, is_dir):
        with tmpdir.as_cwd():
            with open(".gitignore", "w") as f:
                f.write(pattern)
            #res = os.system("git ")
            return is_gitignore(path)

    matches, differs = define_matches_and_differs(matcher_gitlike)
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
