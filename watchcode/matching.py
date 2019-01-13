from __future__ import division, print_function

import fnmatch
import os
import re


def matcher_fnmatch(path, pattern, is_dir):
    basename = os.path.basename(path)
    return fnmatch.fnmatchcase(basename, pattern)
