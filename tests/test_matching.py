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
    """
    Defines the rules supported by gitlike matching. This block is
    executed both with real gitignore matcher (to verify it as a
    ground truth) and the reduced gitlike matching implementation.

    References:
    - https://git-scm.com/docs/gitignore
    - https://www.atlassian.com/git/tutorials/saving-changes/gitignore
    """
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

    # special handling of `.git`
    matches("", "./.git/lock")
    matches("", "./test/.git/lock")

    # note that a plain name matches both file and directories
    matches("foo", "./foo", is_dir=False)
    matches("foo", "./foo", is_dir=True)
    matches("foo", "./foo/test")
    matches("foo", "./sub/foo", is_dir=False)
    matches("foo", "./sub/foo", is_dir=True)
    matches("foo", "./sub/foo/test")

    # check for path sequences
    matches("foo/bar", "./foo/bar")
    matches("foo/bar", "./foo/bar/content")
    differs("foo/bar", "./foo")
    differs("foo/bar", "./bar")
    differs("foo/bar", "./sub/foo")
    differs("foo/bar", "./sub/bar")
    #matches("foo/bar", "./sub/foo/bar")     # suprising, fails
    #matches("foo/bar", "./sub/foo/bar/content")
    #matches("**/foo/bar", "./sub/foo/bar")  # requires ** instead
    #matches("**/foo/bar", "./sub/foo/bar/content")

    differs("foo/bar/", "./foo/bar")
    matches("foo/bar/", "./foo/bar", is_dir=True)
    matches("foo/bar/", "./foo/bar/content")
    differs("foo/bar/", "./foo")
    differs("foo/bar/", "./bar")
    differs("foo/bar/", "./sub/foo")
    differs("foo/bar/", "./sub/bar")
    #matches("foo/bar/", "./sub/foo/bar")     # suprising, fails
    #matches("foo/bar/", "./sub/foo/bar/content")
    #matches("**/foo/bar/", "./sub/foo/bar")  # requires ** instead
    #matches("**/foo/bar/", "./sub/foo/bar/content")

    # wildcards in dirs
    differs("*/", "./x")
    matches("*/", "./x", is_dir=True)
    matches("*/", "./sub/a")
    matches("*/", "./sub/sub/a")

    differs("a*/", "./a")
    matches("a*/", "./a", is_dir=True)
    matches("a*/", "./a/file")
    differs("a*/", "./b/a")
    matches("a*/", "./b/a", is_dir=True)
    matches("a*/", "./b/a/file")

    differs("*/*.log", "./test.log")
    matches("*/*.log", "./sub/test.log")
    matches("*/*.log", "./sub/test.log/a")
    #matches("*/*.log", "./another/sub/test.log")       # requires ** again
    #matches("**/*/*.log", "./another/sub/test.log")

    # checks with leading dots
    differs("./test", "test")       # apparently prefixing with . is not supported
    differs("./test", "./test")     # apparently prefixing with . is not supported
    matches("...", "...")           # apparently treated as a (part of the) filename
    matches(".../*", ".../x")
    matches(".*", ".hidden")


def test_gitlike(tmpdir):
    matches, differs = define_matches_and_differs(matcher_gitlike)
    verify_gitignore_rules(matches, differs)


def test_is_gitignore(tmpdir):

    def fix_path(path):
        # Test are written assuming os.sep is '/' => convert for Windows
        return path.replace("/", os.sep)

    def set_gitignore(pattern):
        with open(".gitignore", "w") as f:
            f.write(pattern)

    def matches(pattern, path, is_dir=False):
        path = fix_path(path)
        if is_dir:
            path = path + os.sep
        set_gitignore(pattern)
        assert is_gitignore(path), \
            "pattern '{}' must match path '{}'".format(pattern, path)

    def differs(pattern, path, is_dir=False):
        path = fix_path(path)
        if is_dir:
            path = path + os.sep
        set_gitignore(pattern)
        assert not is_gitignore(path), \
            "pattern '{}' must NOT match path '{}'".format(pattern, path)

    with tmpdir.as_cwd():
        os.system("git init --quiet")
        verify_gitignore_rules(matches, differs)
