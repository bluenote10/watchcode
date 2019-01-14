from __future__ import division, print_function

import os
import sys
import yaml

import matching


DEFAULT_CONFIG_FILENAME = ".watchcode.yaml"


class KN(object):
    """ Central place to store config key names for better refactoring """
    filesets = "filesets"
    include = "include"
    exclude = "exclude"
    match_mode = "match_mode"

    tasks = "tasks"
    commands = "commands"
    clear_screen = "clear_screen"
    queue_events = "queue_events"

    targets = "targets"
    fileset = "fileset"
    task = "task"

    default_target = "default_target"
    log_all_events = "log_all_events"


class FileSet(object):
    def __init__(self, patterns_incl, patterns_excl, match_mode):
        self.patterns_incl = patterns_incl
        self.patterns_excl = patterns_excl

        self.match_mode = match_mode
        if self.match_mode == "fnmatch":
            self.matcher = matching.matcher_fnmatch
        elif self.match_mode == "re":
            self.matcher = matching.matcher_re
        elif self.match_mode == "gitlike":
            self.matcher = matching.matcher_gitlike
        else:
            print("Unknown match mode: '{}'".format(match_mode))
            sys.exit(1)

    def matches(self, path, event_type, is_dir):

        matches = False
        for pattern in self.patterns_incl:
            if self.matcher(path, pattern, is_dir):
                matches = True
                break

        if matches:
            for pattern in self.patterns_excl:
                if self.matcher(path, pattern, is_dir):
                    matches = False
                    break

        return matches


class Task(object):
    def __init__(self, commands, clear_screen, queue_events):
        self.commands = commands
        self.clear_screen = clear_screen
        self.queue_events = queue_events


class Target(object):
    """ A Target combines a FileSet with a Task """
    def __init__(self, fileset, task):
        self.fileset = fileset
        self.task = task


class Config(object):
    def __init__(self, targets, default_target, log_all_events):
        self.targets = targets
        self.default_target = default_target
        self.log_all_events = log_all_events

    def get_target(self, override_target):
        if override_target is not None:
            target_name = override_target
        else:
            target_name = self.default_target

        if target_name not in self.targets:
            raise ConfigError("Target name '{}' is not defined.".format(target_name))

        return self.targets[target_name]


class ConfigError(Exception):
    pass


def verify_instance(x, type):
    if not isinstance(x, type):
        raise ValueError("wrong type")

"""
def instance_bool(x):
    return isinstance(x, bool)


def instance_list(x):
    return isinstance(x, list)


def instance_dict(x):
    return isinstance(x, dict)
"""

class InstanceCheckerBool(object):
    name = "bool"

    @staticmethod
    def check(x):
        return isinstance(x, bool)


def safe_key_extract(data, key, what, instance_checker=None):
    if not isinstance(data, dict):
        print("Error: {} must be a dictionary, but got: {}".format(what, data))
        sys.exit(0)
    if not key in data:
        print("Error: {} must contain key '{}'.".format(what, key))
        sys.exit(0)
    else:
        value = data[key]
        if instance_checker is not None:
            if not instance_checker.check(value):
                raise ConfigError("{} must contain key '{}' with a value of type {}, but got: {}".format(
                    what, key, instance_checker.name, data,
                ))
        return value


def parse_fileset(fileset_data):
    patterns_incl = safe_key_extract(fileset_data, KN.include, "File set")
    patterns_excl = safe_key_extract(fileset_data, KN.exclude, "File set")
    match_mode = safe_key_extract(fileset_data, KN.match_mode, "File set")

    # When the incl/excl lists are empty, the yaml parser returns None.
    # We want empty lists in these cases.
    if patterns_incl is None:
        patterns_incl = []
    if patterns_excl is None:
        patterns_excl = []

    # TODO check integrity of match mode here or just later?
    return FileSet(
        patterns_incl=patterns_incl,
        patterns_excl=patterns_excl,
        match_mode=match_mode,
    )


def parse_task(task_data):
    commands = safe_key_extract(task_data, KN.commands, "Task")
    clear_screen = safe_key_extract(task_data, KN.clear_screen, "Task", InstanceCheckerBool)
    queue_events = safe_key_extract(task_data, KN.queue_events, "Task", InstanceCheckerBool)

    if commands is None:
        commands = []

    # TODO use checker
    if not isinstance(commands, list):
        print("Error: Commands must be a list, but got: {}".format(commands))
        sys.exit(0)

    return Task(commands, clear_screen, queue_events)


def load_config(working_directory):
    config_path = os.path.join(working_directory, DEFAULT_CONFIG_FILENAME)

    if not os.path.exists(config_path):
        print("Could not find '{}'".format(DEFAULT_CONFIG_FILENAME))
        sys.exit(1)

    try:
        with open(config_path) as f:
            config_data = yaml.load(f)
    except IOError as e:
        print("Could not read/parse '{}', Error: {}".format(
            DEFAULT_CONFIG_FILENAME, str(e)
        ))
        sys.exit(1)

    filesets_dict = safe_key_extract(config_data, KN.filesets, "Config")
    tasks_dict = safe_key_extract(config_data, KN.tasks, "Config")
    targets_dict = safe_key_extract(config_data, KN.targets, "Config")

    targets = {}

    for target_name, target in targets_dict.items():
        fileset_name = safe_key_extract(target, KN.fileset, "Target")
        task_name = safe_key_extract(target, KN.task, "Target")

        if fileset_name not in filesets_dict:
            print("Error: File set '{}' is not defined.".format(fileset_name))
            sys.exit(1)
        if task_name not in tasks_dict:
            print("Error: Task '{}' is not defined.".format(task_name))
            sys.exit(1)

        fileset = parse_fileset(filesets_dict[fileset_name])
        task = parse_task(tasks_dict[task_name])

        targets[target_name] = Target(fileset, task)

    default_target = safe_key_extract(config_data, KN.default_target, "Config")
    log_all_events = safe_key_extract(config_data, KN.log_all_events, "Config", InstanceCheckerBool)

    return Config(targets, default_target, log_all_events)

