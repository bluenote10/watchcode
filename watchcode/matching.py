from __future__ import division, print_function

import fnmatch
import os
import re

import subprocess


def matcher_fnmatch(path, pattern, is_dir):
    if is_dir:
        return False
    basename = os.path.basename(path)
    return fnmatch.fnmatchcase(basename, pattern)


def matcher_re(path, pattern, is_dir):
    m = re.search(pattern, path)
    return m is not None


def matcher_gitlike(path, pattern, is_dir):
    if is_dir and path[-1] != os.path.sep:
        path = path + os.path.sep

    #comps = path.split(os.sep)

    basename = os.path.basename(path)
    filename_match = fnmatch.fnmatchcase(basename, pattern)
    return filename_match or pattern in path


def is_gitignore(path):

    # `git check-ignore` does not return an ignore status for
    # files under `.git` itself. We need special handling for
    # that:
    comps = path.split(os.sep)
    if len(comps) >= 2 and comps[1] == ".git":
        return True

    try:
        p = subprocess.Popen(
            ["git", "check-ignore", path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError:
        warning = "Cannot execute 'git check-ignore'."
        # TODO communicate warning

    outs, errs = p.communicate()
    ret = p.returncode

    if ret == 0:
        return True
    elif ret == 1 and errs == "":
        return False
    else:
        # return code 128 is "fatal error"
        warning = "'git check-ignore' returned unexpected return code ({})".format(ret)
        if errs != "":
            warning += " with error: {}".format(errs)
        else:
            warning += "."
        # TODO communicate warning