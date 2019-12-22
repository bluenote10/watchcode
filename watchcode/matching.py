from __future__ import division, print_function

import fnmatch
import logging
import os
import re

import subprocess

logger = logging.getLogger(__name__)


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

    if pattern.startswith(GITIGNORE_SEP):
        pattern_is_absolute = True
        pattern = pattern[1:]
    else:
        pattern_is_absolute = False

    if pattern.startswith("**"):
        match_anywhere = True
        pattern = pattern[2:]
    else:
        match_anywhere = False

    if pattern.endswith(GITIGNORE_SEP):
        match_dir_only = True
        pattern = pattern[:-1]
    else:
        match_dir_only = False

    pattern_comps = pattern.split(GITIGNORE_SEP)
    evt_comps = event.components
    evt_comps_is_dir = event.components_is_dir

    if ".git" in evt_comps:
        return True

    def match(evt_comp, evt_comp_is_dir, pattern):
        if fnmatch.fnmatch(evt_comp, pattern):
            if match_dir_only:
                return evt_comp_is_dir
            else:
                return True
        else:
            return False

    if len(pattern_comps) == 1:
        # matching a single pattern

        if pattern_is_absolute:
            return match(evt_comps[0], evt_comps_is_dir[0], pattern)
        else:
            for i, c in enumerate(event.components):
                if match(c, evt_comps_is_dir[i], pattern):
                    return True
            return False

    else:
        # print(evt_comps, pattern_comps)
        i = 0
        while True:
            # print(i, evt_comps[i], pattern_comps[i])
            try:
                current_comp_matches = fnmatch.fnmatch(evt_comps[i], pattern_comps[i])
            except IndexError:
                current_comp_matches = False
            if not current_comp_matches:
                return False
            i += 1
            if i >= len(evt_comps) and i >= len(pattern_comps):
                if match_dir_only:
                    return evt_comps_is_dir[i-1]
                else:
                    return True
            elif i >= len(evt_comps):
                # Pattern is longer than event path => no match.
                return False
            elif i >= len(pattern_comps):
                # Event path is longer than pattern => match.
                # Note that match_dir_only is automatically satisfied, because
                return True

    # TODO: add `match_anywhere` implementation


def is_gitignore(path):
    # TODO: needs working directory?

    # `git check-ignore` does not return an ignore status for
    # files under `.git` itself. We need special handling for
    # that. Note that git even ignores other `.git` folders
    # in subpaths.
    comps = path.split(os.sep)
    if ".git" in comps:
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


def does_match(fileset, event):
    # TODO return an object that stores which of the
    # three cases was applied, with additional infos

    matches = False
    for pattern in fileset.patterns_incl:
        if fileset.matcher(pattern, event):
            matches = True
            break

    if matches:
        for pattern in fileset.patterns_excl:
            if fileset.matcher(pattern, event):
                matches = False
                break

    if matches:
        if fileset.exclude_gitignore:
            if is_gitignore(event.path):
                matches = False

    return matches


AVAILABLE_MATCH_MODES = {
    "fnmatch": matcher_fnmatch,
    "re": matcher_re,
    "gitlike": matcher_gitlike,
}
