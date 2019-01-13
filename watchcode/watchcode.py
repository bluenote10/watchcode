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


class FileSet(object):
    def __init__(self, patterns_incl, patterns_excl, match_mode):
        self.patterns_incl = patterns_incl
        self.patterns_excl = patterns_excl

        self.match_mode = match_mode
        if self.match_mode == "unix":
            self.matcher = FileSet.match_fnmatch
        else:
            print("Unknown match mode: '{}'".format(match_mode))
            sys.exit(1)

    def matches(self, src_path, dest_path, event_type, is_directory):

        matches = False
        for pattern in self.patterns_incl:
            if self.matcher(src_path, pattern):
                matches = True
                break
            if dest_path is not None and self.matcher(dest_path, pattern):
                matches = True
                break

        if matches:
            for pattern in self.patterns_excl:
                if self.matcher(src_path, pattern):
                    matches = False
                    break

        return matches

    @staticmethod
    def match_fnmatch(path, pattern):
        return fnmatch.fnmatchcase(path, pattern)


class Task(object):
    def __init__(self, commands, clear_screen):
        self.commands = commands
        self.clear_screen = clear_screen

    def run(self):
        for command in self.commands:
            # TODO: set cwd
            status = subprocess.Popen(command, shell=True).wait()


class Target(object):
    def __init__(self, fileset, task):
        self.fileset = fileset
        self.task = task


class Config(object):
    def __init__(self, targets, default_target):
        self.targets = targets
        self.default_target = default_target


def safe_key_extract(data, key, what):
    if not isinstance(data, dict):
        print("Error: {} must be a dictionary, but got: {}".format(what, data))
        sys.exit(0)
    if not key in data:
        print("Error: {} must contain key '{}'.".format(what, key))
        sys.exit(0)
    else:
        return data[key]


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
    clear_screen = safe_key_extract(task_data, "ClearScreen", "Task")

    if commands is None:
        commands = []

    if not isinstance(commands, list):
        print("Error: Commands must be a list, but got: {}".format(commands))
        sys.exit(0)
    if not isinstance(clear_screen, bool):
        print("Error: Clear screen must be a bool, but got: {}".format(clear_screen))
        sys.exit(0)

    return Task(commands, clear_screen)


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
        print(target_name, target)
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

    return Config(targets, default_target)


class EventHandler(FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self, working_dir, fileset, task, show_all_events):
        self.io_handler = IOHandler(working_dir)

        self.fileset = fileset
        self.task = task
        self.show_all_events = show_all_events

    def on_any_event(self, event):
        super(EventHandler, self).on_any_event(event)

        # Extract event information
        event_type = event.event_type
        src_path = event.src_path
        dest_path = event.dest_path if event_type == "moved" else None
        is_directory = event.is_directory

        matches = self.fileset.matches(src_path, dest_path, event_type, is_directory)

        if matches or self.show_all_events:
            print(" * Event: {:<10}     File: {:<60s}     Match: {}".format(
                event_type,
                src_path,
                "yes" if matches else "no",
            ))

        # TODO if matches reload config.
        # But we should reload _before_ triggering commands, right?

        if matches:
            #self.task.run()
            self.io_handler.trigger_commands(self.task.commands, True)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "target",
        default="default",
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
    parser.add_argument(
        "--clear",
        default=False,
        action="store_true",
        help="Print all file change events, including non-matching events for debugging.",
    )
    parser.add_argument(
        "--show-all-events",
        default=False,
        action="store_true",
        help="Print all file change events, including non-matching events for debugging.",
    )
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    working_dir = args.dir

    config = load_config(working_dir)

    target = config.targets["Default"]

    event_handler = EventHandler(working_dir, target.fileset, target.task, args.show_all_events)

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
