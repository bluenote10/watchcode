from __future__ import division, print_function

import functools
import os
import yaml

from .matching import AVAILABLE_MATCH_MODES

DEFAULT_CONFIG_FILENAME = ".watchcode.yaml"


# -----------------------------------------------------------------------------
# Validation utilities
# -----------------------------------------------------------------------------

def map_dict_values(d, func):
    """ Syntax convenience """
    return {k: func(v) for k, v in d.items()}


class ConfigError(Exception):
    pass


class CheckerStr(object):
    # must be ...
    name = "a string"

    def __call__(self, x):
        return isinstance(x, str), x


class CheckerBool(object):
    # must be ...
    name = "a bool"

    def __call__(self, x):
        return isinstance(x, bool), x


class CheckerDict(object):
    # must be ...
    name = "a dictionary"

    def __call__(self, x):
        return isinstance(x, dict), x


class CheckerListOfStr(object):
    # must be ...
    name = "a list of strings"

    def __call__(self, x):
        # The YAML parser returns None when lists are unspecified in the YAML.
        # It's more convenient to convert that into empty lists.
        if x is None:
            return True, []
        else:
            if not isinstance(x, list):
                return False, x
            else:
                all_str = all([
                    isinstance(element, str) for element in x
                ])
                return all_str, x


class CheckerMatchMode(object):
    # must be ...
    name = "either {}".format(AVAILABLE_MATCH_MODES.keys())

    def __call__(self, x):
        if x not in AVAILABLE_MATCH_MODES:
            return False, x
        else:
            return True, AVAILABLE_MATCH_MODES[x]


class SafeKeyExtractor(object):

    def __init__(self, data, what):
        self.data = data
        self.what = what
        self.checked_keys = set()

    def __call__(self, key, checker):
        self.checked_keys.add(key)
        if not isinstance(self.data, dict):
            raise ConfigError("{} must be a dictionary, but got: {}".format(
                self.what.title(), self.data
            ))
        if key not in self.data:
            raise ConfigError("{} must contain key '{}'.".format(
                self.what.title(), key
            ))
        else:
            value = self.data[key]
            is_valid, value_validated = checker(value)
            if not is_valid:
                raise ConfigError("Key '{}' of {} must be {}, but got: {}".format(
                    key, self.what, checker.name, value,
                ))
            return value_validated

    def verify_no_extra_keys(self):
        existing_keys = set(self.data.keys())
        extra_keys = existing_keys - self.checked_keys
        if len(extra_keys) > 0:
            raise ConfigError("{} contains unexpected key{}: {}.".format(
                self.what.title(),
                "s" if len(extra_keys) > 1 else "",
                list(extra_keys),
            ))


# -----------------------------------------------------------------------------
# Main config entities
# -----------------------------------------------------------------------------

class FileSet(object):
    def __init__(self, patterns_incl, patterns_excl, matcher, exclude_gitignore):
        self.patterns_incl = patterns_incl
        self.patterns_excl = patterns_excl
        self.matcher = matcher
        self.exclude_gitignore = exclude_gitignore

    @staticmethod
    def validate(data):
        extractor = SafeKeyExtractor(data, "fileset")

        patterns_incl = extractor("include", CheckerListOfStr())
        patterns_excl = extractor("exclude", CheckerListOfStr())
        matcher = extractor("match_mode", CheckerMatchMode())
        exclude_gitignore = extractor("exclude_gitignore", CheckerBool())

        extractor.verify_no_extra_keys()
        return FileSet(
            patterns_incl=patterns_incl,
            patterns_excl=patterns_excl,
            matcher=matcher,
            exclude_gitignore=exclude_gitignore,
        )


class Task(object):
    def __init__(self, fileset, commands, clear_screen, queue_events):
        self.fileset = fileset
        self.commands = commands
        self.clear_screen = clear_screen
        self.queue_events = queue_events

    @staticmethod
    def validate(data, filesets):
        extractor = SafeKeyExtractor(data, "task")

        fileset = extractor("fileset", CheckerStr())
        commands = extractor("commands", CheckerListOfStr())
        clear_screen = extractor("clear_screen", CheckerBool())
        queue_events = extractor("queue_events", CheckerBool())

        # Lookup fileset in filesets dict
        if fileset not in filesets:
            raise ConfigError("Fileset '{}' does not exist. Detected file sets: {}".format(
                fileset,
                ", ".join(["'{}'".format(x) for x in sorted(filesets.keys())])
            ))

        fileset = filesets[fileset]

        extractor.verify_no_extra_keys()
        return Task(fileset, commands, clear_screen, queue_events)


class Overrides(object):
    def __init__(self, task):
        self.task = task


class Config(object):
    def __init__(self, overrides, tasks, default_tasks, log):
        self.overrides = overrides
        self.tasks = tasks
        self.default_task = default_tasks
        self.log = log

    @property
    def task(self):
        if self.overrides.task is not None:
            task_name = self.overrides.task
        else:
            task_name = self.default_task

        if task_name not in self.tasks:
            raise ConfigError("Task name '{}' is not defined.".format(task_name))

        return self.tasks[task_name]

    @staticmethod
    def validate(data, overrides):
        extractor = SafeKeyExtractor(data, "config")

        filesets_dict = extractor("filesets", CheckerDict())
        tasks_dict = extractor("tasks", CheckerDict())
        default_task = extractor("default_task", CheckerStr())
        log = extractor("log", CheckerBool())

        # subparsers including consistency check
        filesets = map_dict_values(filesets_dict, FileSet.validate)
        tasks = map_dict_values(tasks_dict, functools.partial(Task.validate, filesets=filesets))

        extractor.verify_no_extra_keys()
        return Config(overrides, tasks, default_task, log)


def load_config(working_directory, overrides):
    """
    Main entry point for config loading.
    """
    config_path = os.path.join(working_directory, DEFAULT_CONFIG_FILENAME)

    if not os.path.exists(config_path):
        raise ConfigError("Could not find '{}'".format(DEFAULT_CONFIG_FILENAME))

    try:
        with open(config_path) as f:
            config_data = yaml.load(f)
    except IOError as e:
        raise ConfigError("Could not read/parse '{}', Error: {}".format(
            DEFAULT_CONFIG_FILENAME, str(e)
        ))

    return Config.validate(config_data, overrides)
