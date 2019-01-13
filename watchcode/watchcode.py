#!/usr/bin/env python
"""
Generic tool to watch for code changes and continuously execute commands.
"""

from __future__ import division, print_function

import argparse
import os
import sys
import time
import subprocess

import yaml

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import fnmatch
import re

#from watchcode.io_handler import IOHandler
from io_handler import IOHandler


DEFAULT_CONFIG_FILENAME = ".watchcode.yaml"


def is_config_file(path):
    #if path is None:
    #    return False
    path_components = os.path.split(path)
    # TODO: requires case insensitive matching for Windows
    return len(path_components) == 2 and path_components[1] == DEFAULT_CONFIG_FILENAME


class FileSet(object):
    def __init__(self, patterns_incl, patterns_excl, match_mode):
        self.patterns_incl = patterns_incl
        self.patterns_excl = patterns_excl

        self.match_mode = match_mode
        if self.match_mode == "fnmatch":
            self.matcher = FileSet.match_fnmatch
        else:
            print("Unknown match mode: '{}'".format(match_mode))
            sys.exit(1)

    def matches(self, path, event_type, is_directory):

        matches = False
        for pattern in self.patterns_incl:
            if self.matcher(path, pattern):
                matches = True
                break

        if matches:
            for pattern in self.patterns_excl:
                if self.matcher(path, pattern):
                    matches = False
                    break

        return matches

    @staticmethod
    def match_fnmatch(path, pattern):
        basename = os.path.basename(path)
        return fnmatch.fnmatchcase(basename, pattern)


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
    def __init__(self, targets, default_target, show_all_events):
        self.targets = targets
        self.default_target = default_target
        self.show_all_events = show_all_events

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
    patterns_incl = safe_key_extract(fileset_data, "Include", "File set")
    patterns_excl = safe_key_extract(fileset_data, "Exclude", "File set")
    match_mode = safe_key_extract(fileset_data, "MatchMode", "File set")

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
    commands = safe_key_extract(task_data, "Commands", "Task")
    clear_screen = safe_key_extract(task_data, "ClearScreen", "Task", InstanceCheckerBool)
    queue_events = safe_key_extract(task_data, "QueueEvents", "Task", InstanceCheckerBool)

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

    filesets_dict = safe_key_extract(config_data, "FileSets", "Config")
    tasks_dict = safe_key_extract(config_data, "Tasks", "Config")
    targets_dict = safe_key_extract(config_data, "Targets", "Config")

    targets = {}

    for target_name, target in targets_dict.items():
        fileset_name = safe_key_extract(target, "FileSet", "Target")
        task_name = safe_key_extract(target, "Task", "Target")

        if fileset_name not in filesets_dict:
            print("Error: File set '{}' is not defined.".format(fileset_name))
            sys.exit(1)
        if task_name not in tasks_dict:
            print("Error: Task '{}' is not defined.".format(task_name))
            sys.exit(1)

        fileset = parse_fileset(filesets_dict[fileset_name])
        task = parse_task(tasks_dict[task_name])

        targets[target_name] = Target(fileset, task)

    default_target = safe_key_extract(config_data, "DefaultTarget", "Config")
    show_all_events = safe_key_extract(config_data, "ShowAllEvents", "Config", InstanceCheckerBool)

    return Config(targets, default_target, show_all_events)


class Event(object):
    def __init__(self, path, type, is_dir):
        self.path = path
        self.type = type
        self.is_dir = is_dir


class EventHandler(FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self, working_dir, override_target):
        self.working_dir = working_dir
        self.override_target = override_target

        self.io_handler = IOHandler(working_dir)

        self.config = None
        self.target = None
        self.load_config()

        #config = load_config(working_dir)
        #target = config.targets["Default"]

        #self.fileset = fileset
        #self.task = task
        #self.show_all_events = show_all_events

    def load_config(self):
        # TODO error handling
        self.config = load_config(self.working_dir)
        self.target = self.config.get_target(self.override_target)

    def on_any_event(self, event):
        super(EventHandler, self).on_any_event(event)

        # Convert into simplified representation to avoid special handling of dest_path
        if event.event_type == "moved":
            events = [
                Event(event.src_path, event.event_type + "_from", event.is_directory),
                Event(event.dest_path, event.event_type + "_to", event.is_directory),
            ]
        else:
            events = [
                Event(event.src_path, event.event_type, event.is_directory),
            ]

        for event in events:
            self.handle_event(event)

    def handle_event(self, event):

        # First attempt to reload config (in cases where we have none)
        if is_config_file(event.path):
            print(" * Reloading config") # TODO we must not log here... during builds...
            self.load_config()

        if self.target is None or self.config is None:
            return

        matches = self.target.fileset.matches(event.path, event.type, event.is_dir)

        self.io_handler.trigger(
            matches, event,
            commands=self.target.task.commands,
            log_all=self.config.show_all_events,
            queue_trigger=self.target.task.queue_events,
            clear_screen=self.target.task.clear_screen,
        )


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        default=None,
        nargs='?',
        help="Run a specific target. By default, uses the default target setting "
             "from the YAML config. If an explicit target is specified, the value "
             "in the config is ignored.",
    )
    parser.add_argument(
        "--dir",
        default=".",
        help="Working directory to run in, defaults to the current directory.",
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    working_dir = args.dir
    print(" * Monitoring '{}' for changes... [Press CTRL+C to exit]".format(working_dir))

    event_handler = EventHandler(working_dir, override_target=args.target)

    observer = Observer()
    observer.schedule(event_handler, working_dir, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1000)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
