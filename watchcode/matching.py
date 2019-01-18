from __future__ import division, print_function

import fnmatch
import os
import re

import subprocess


def matcher_fnmatch(pattern, event):
    if event.is_dir:
        return False
    basename = os.path.basename(event.path)
    return fnmatch.fnmatchcase(basename, pattern)


def matcher_re(pattern, event):
    m = re.search(pattern, event.path)
    return m is not None


def matcher_gitlike(pattern, event):
    GITIGNORE_SEP = "/"

    pattern_is_absolute = pattern.startswith(GITIGNORE_SEP)
    pattern_components = pattern.split(GITIGNORE_SEP)

    if len(pattern_components) >= 2 and pattern_components[-1] == "":
        file_pattern = pattern_components[-2]
    else:
        file_pattern = pattern_components[-1]

    filename_match = fnmatch.fnmatchcase(event.basename, file_pattern)
    return filename_match or pattern in event.path_normalized


def is_gitignore(path):
    # TODO: needs working directory?

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