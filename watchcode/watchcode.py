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
from config import FileSet, Task, Target, load_config, DEFAULT_CONFIG_FILENAME


def is_config_file(path):
    # TODO: move into event class?
    path_components = os.path.split(path)
    # TODO: requires case insensitive matching for Windows
    return len(path_components) == 2 and path_components[1] == DEFAULT_CONFIG_FILENAME


class Event(object):
    def __init__(self, path, type, is_dir):
        self.path = path
        self.type = type
        self.is_dir = is_dir


class EventHandler(FileSystemEventHandler):
    """ Watchcode's main event handler """

    def __init__(self, working_dir, override_target):
        self.working_dir = working_dir
        self.override_target = override_target

        self.io_handler = IOHandler(working_dir)

        self.config = None
        self.target = None
        self.load_config()

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
            log_all=self.config.log_all_events,
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
