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

    def __call__(self, key, checker, default=None):
        self.checked_keys.add(key)
        if not isinstance(self.data, dict):
            raise ConfigError("{} must be a dictionary, but got: {}".format(
                self.what.title(), self.data
            ))
        else:
            if key in self.data:
                value = self.data[key]
            elif default is not None:
                value = default
            else:
                raise ConfigError("{} must contain key '{}'.".format(
                    self.what.title(), key
                ))
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
        matcher = extractor("match_mode", CheckerMatchMode(), default="gitlike")
        exclude_gitignore = extractor("exclude_gitignore", CheckerBool(), default=True)

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
        clear_screen = extractor("clear_screen", CheckerBool(), default=True)
        queue_events = extractor("queue_events", CheckerBool(), default=False)

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
    def __init__(self, task_name=None, log=None, sound=None, notifications=None):
        self.task_name = task_name
        self.log = log
        self.sound = sound
        self.notifications = notifications


class Config(object):
    def __init__(self, overrides, tasks, default_task, log, sound, notifications):
        self.overrides = overrides

        def with_override(value, override_value):
            if override_value is None:
                return value
            else:
                return override_value

        self.tasks = tasks

        self.default_task = with_override(default_task, overrides.task_name)
        self.log = with_override(log, overrides.log)
        self.sound = with_override(sound, overrides.sound)
        self.notifications = with_override(notifications, overrides.notifications)

        self.task = self.get_task_validated()

    def get_task_validated(self):
        if self.default_task not in self.tasks:
            raise ConfigError("Task name '{}' is not defined.".format(self.default_task))
        return self.tasks[self.default_task]

    @staticmethod
    def validate(data, overrides):
        extractor = SafeKeyExtractor(data, "config")

        filesets_dict = extractor("filesets", CheckerDict())
        tasks_dict = extractor("tasks", CheckerDict())
        default_task = extractor("default_task", CheckerStr())
        log = extractor("log", CheckerBool(), default=True)
        sound = extractor("sound", CheckerBool(), default=False)
        notifications = extractor("notifications", CheckerBool(), default=False)

        # subparsers including consistency check
        filesets = map_dict_values(filesets_dict, FileSet.validate)
        tasks = map_dict_values(tasks_dict, functools.partial(Task.validate, filesets=filesets))

        extractor.verify_no_extra_keys()
        return Config(
            overrides=overrides,
            tasks=tasks,
            default_task=default_task,
            log=log,
            sound=sound,
            notifications=notifications,
        )


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
    except (IOError, yaml.YAMLError) as e:
        raise ConfigError("Could not read/parse '{}':\n{}".format(
            DEFAULT_CONFIG_FILENAME, str(e)
        ))

    return Config.validate(config_data, overrides)


class ConfigFactory(object):
    def __init__(self, working_directory, overrides):
        self.working_directory = working_directory
        self.overrides = overrides

    def load_config(self):
        return load_config(self.working_directory, self.overrides)
