from __future__ import division, print_function

import fnmatch
import os
import re


def matcher_fnmatch(path, pattern, is_dir):
    basename = os.path.basename(path)
    return fnmatch.fnmatchcase(basename, pattern)


def matcher_re(path, pattern, is_dir):
    m = re.search(pattern, path)
    return m is not None


def matcher_gitlike(path, pattern, is_dir):
    if is_dir and path[-1] != os.path.sep:
        path = path + os.path.sep

    #components = os.path.split(path)

    basename = os.path.basename(path)
    filename_match = fnmatch.fnmatchcase(basename, pattern)
    return filename_match or pattern in path

