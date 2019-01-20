from __future__ import division, print_function

import functools
import os
import sys
import yaml


import matching

from schema import Schema, And, Use, Optional, SchemaError

DEFAULT_CONFIG_FILENAME = ".watchcode.yaml"


def map_dict_values(d, func):
    """ Syntax convenience """
    return {k: func(v) for k, v in d.items()}


class KN(object):
    """ Central place to store config key names for better refactoring """
    filesets = "filesets"
    include = "include"
    exclude = "exclude"
    exclude_gitignore = "exclude_gitignore"
    match_mode = "match_mode"

    tasks = "tasks"
    commands = "commands"
    clear_screen = "clear_screen"
    queue_events = "queue_events"

    targets = "targets"
    fileset = "fileset"
    task = "task"

    default_target = "default_target"
    log = "log"


class FileSet(object):
    def __init__(self, patterns_incl, patterns_excl, match_mode, exclude_gitignore):
        self.patterns_incl = patterns_incl
        self.patterns_excl = patterns_excl
        self.exclude_gitignore = exclude_gitignore

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

    def matches(self, event):
        # TODO return an object that stores which of the
        # three cases was applied, with additional infos

        # TODO this function should be move to matching module

        matches = False
        for pattern in self.patterns_incl:
            if self.matcher(pattern, event):
                matches = True
                break

        if matches:
            for pattern in self.patterns_excl:
                if self.matcher(pattern, event):
                    matches = False
                    break

        if matches:
            if self.exclude_gitignore:
                if matching.is_gitignore(event.path):
                    matches = False

        #if matches:
        #    import IPython; IPython.embed()
        return matches

    @staticmethod
    def validate(data):
        schema = Schema({
            "include": [str],
            "exclude": [str],
            "exclude_gitignore": bool,
            "match_mode": str,
        })
        validated = schema.validate(data)
        return FileSet(
            patterns_incl=validated["include"],
            patterns_excl=validated["exclude"],
            match_mode=validated["match_mode"],
            exclude_gitignore=validated["exclude_gitignore"],
        )


class Task(object):
    def __init__(self, fileset, commands, clear_screen, queue_events):
        self.fileset = fileset
        self.commands = commands
        self.clear_screen = clear_screen
        self.queue_events = queue_events

    @staticmethod
    def validate(data):
        schema = Schema({
            "fileset": str,
            "commands": [str],
            "clear_screen": bool,
            "queue_events": bool,
        })
        validated = schema.validate(data)
        return Task(
            fileset=validated["fileset"],
            commands=validated["commands"],
            clear_screen=validated["clear_screen"],
            queue_events=validated["queue_events"],
        )


class Config(object):
    def __init__(self, tasks, default_tasks, log):
        self.tasks = tasks
        self.default_task = default_tasks
        self.log = log

    def get_target(self, override_target):
        if override_target is not None:
            target_name = override_target
        else:
            target_name = self.default_task

        if target_name not in self.tasks:
            raise ConfigError("Target name '{}' is not defined.".format(target_name))

        return self.tasks[target_name]

    @staticmethod
    def validate(data):
        schema = Schema({
            "filesets": {str: Use(FileSet.validate)},
            "tasks": {str: Use(Task.validate)},
            "default_task": str,
            "log": bool,
        })  # name="Config"
        #  upcoming schema version will support giving names to schemas
        # => better error messages?
        validated = schema.validate(data)

        # TODO: conversion
        if validated["default_task"] not in validated["tasks"]:
            raise SchemaError(
                "The value of 'default_task' ('{}') does not exist as a key in 'tasks' ({}).".format(
                    validated["default_task"],
                    ", ".join(["'{}'".format(x) for x in sorted(validated["tasks"].keys())]),
                )
            )

        return Config(
            tasks=validated["tasks"],
            default_tasks=validated["default_task"],
            log=validated["log"],
        )


class ConfigError(Exception):
    pass


class CheckerStr(object):
    name = "string"

    @staticmethod
    def check(x):
        return isinstance(x, str), x


class CheckerBool(object):
    name = "bool"

    @staticmethod
    def check(x):
        return isinstance(x, bool), x


class CheckerDict(object):
    name = "dict"

    @staticmethod
    def check(x):
        return isinstance(x, dict), x


class CheckerListOfStr(object):
    name = "list of strings"

    @staticmethod
    def check(x):
        # The YAML parser returns None when lists are unspecified in the YAML.
        # It's more convenient to convert that into empty lists.
        if x is None:
            return True, []
        else:
            if not isinstance(x, list):
                return False, x
            else:
                all_str = all([isinstance(element, str) for element in x])
                return all_str, x


class SafeKeyExtractor(object):

    def __init__(self, data, what):
        self.data = data
        self.what = what

    def __call__(self, key, checker):
        if not isinstance(self.data, dict):
            print("Error: {} must be a dictionary, but got: {}".format(self.what, self.data))
            sys.exit(0)
        if key not in self.data:
            print("Error: {} must contain key '{}'.".format(self.what, key))
            sys.exit(0)
        else:
            value = self.data[key]
            is_valid, value_validated = checker.check(value)
            if not is_valid:
                raise ConfigError("{} must contain key '{}' with a value of type {}, but got: {}".format(
                    self.what, key, checker.name, value,
                ))
            return value_validated


def parse_fileset(data):
    extractor = SafeKeyExtractor(data, "File set")
    patterns_incl = extractor(KN.include, CheckerListOfStr)
    patterns_excl = extractor(KN.exclude, CheckerListOfStr)
    match_mode = extractor(KN.match_mode, CheckerStr)   # TODO convert here
    exclude_gitignore = extractor(KN.exclude_gitignore, CheckerBool)

    return FileSet(
        patterns_incl=patterns_incl,
        patterns_excl=patterns_excl,
        match_mode=match_mode,
        exclude_gitignore=exclude_gitignore,
    )


def parse_task(data, filesets):
    extractor = SafeKeyExtractor(data, "Task")

    fileset = extractor(KN.fileset, CheckerStr)
    commands = extractor(KN.commands, CheckerListOfStr)
    clear_screen = extractor(KN.clear_screen, CheckerBool)
    queue_events = extractor(KN.queue_events, CheckerBool)

    # Lookup fileset in filesets dict
    if fileset not in filesets:
        raise ConfigError("Fileset '{}' does not exist. Detected file sets: {}".format(
            fileset,
            ", ".join(["'{}'".format(x) for x in sorted(filesets.keys())])
        ))

    fileset = filesets[fileset]

    return Task(fileset, commands, clear_screen, queue_events)


def parse_config(data):
    extractor = SafeKeyExtractor(data, "Config")

    filesets_dict = extractor(KN.filesets, CheckerDict)
    tasks_dict = extractor(KN.tasks, CheckerDict)
    default_task = extractor("default_task", CheckerStr)
    log = extractor(KN.log, CheckerBool)

    # subparsers including consistency check
    filesets = map_dict_values(filesets_dict, parse_fileset)
    tasks = map_dict_values(tasks_dict, functools.partial(parse_task, filesets=filesets))

    return Config(tasks, default_task, log)


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

    """
    schema = Schema({
        #'name': And(str, len),
        #'age':  And(Use(int), lambda n: 18 <= n <= 99),
        #Optional('gender'): And(str, Use(str.lower), lambda s: s in ('squid', 'kid'))
        "filesets": Schema({str: Use(FileSet.validate)}),
        "targets": object,
        "tasks": object,

        "default_target": str,
        "log": bool,
    })
    data = [{'name': 'Sue', 'age': '28', 'gender': 'Squid'},{'name': 'Sam', 'age': '42'},{'name': 'Sacha', 'age': '20', 'gender': 'KID'}]
    validated = schema.validate(config_data)
    print(validated)
    #import IPython; IPython.embed()
    """

    schema = Schema(Use(Config.validate))
    validated = schema.validate(config_data)
    print(validated)
    """
    try:
        validated = schema.validate(config_data)
    print(validated)
    except Exception as e:
        import IPython; IPython.embed()
    """
    #sys.exit(0)

    return parse_config(config_data)

