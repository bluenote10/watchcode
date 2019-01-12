#!/usr/bin/env python

from __future__ import division, print_function

import os
import sys
import time
import logging
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

#import pyyaml
import yaml
import fnmatch


class FileSet(object):
    def __init__(self, patterns):
        # TODO: Add patterns exclude list
        self.patterns = patterns


class Task(object):
    def __init__(self, commands):
        self.commands = commands


class Target(object):
    def __init__(self, fileset, task):
        self.fileset = fileset
        self.task = task


def load_config():
    if not os.path.exists(".watchcode.yaml"):
        print("Could not find '.watchcode.yaml'")
        sys.exit(1)

    try:
        with open(".watchcode.yaml") as f:
            config = yaml.load(f)
    except IOError as e:
        print("Could not read '.watchcode.yaml', Error: {}".format(str(e)))
        sys.exit(1)

    fileset_dict = config["FileSets"]
    task_dict = config["Tasks"]
    target_dict = config["Targets"]

    targets = {}

    for target_name, target in target_dict.items():
        print(target_name, target)
        fileset_name = target["FileSet"]
        task_name = target["Task"]

        patterns = fileset_dict[fileset_name]
        commands = task_dict[task_name]

        target = Target(
            fileset=FileSet(patterns),
            task=Task(commands)
        )

        targets[target_name] = target

    return targets


class EventHandler(FileSystemEventHandler):
    """Logs all the events captured."""

    def __init__(self, patterns, commands):
        self.patterns = patterns
        self.commands = commands

    def on_any_event(self, event):
        super(EventHandler, self).on_any_event(event)
        #print(event.event_type)

        event_type = event.event_type
        is_directory = event.is_directory
        src_path = event.src_path
        if event_type == "moved":
            dest_path = event.dest_path
        else:
            dest_path = None

        matches = False
        for pattern in self.patterns:
            if fnmatch.fnmatchcase(src_path, pattern):
                matches = True
                break
            if dest_path is not None and fnmatch.fnmatchcase(dest_path, pattern):
                matches = True
                break

        if matches:
            msg = "yes"
        else:
            msg = "no"

        print(" * Event: {:<10}     File: {:<60s}     Match: {}".format(
            event_type,
            src_path,
            msg,
        ))
        #import IPython; IPython.embed()


if __name__ == "__main__":

    targets = load_config()

    #import IPython; IPython.embed()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S')
    path = sys.argv[1] if len(sys.argv) > 1 else '.'

    target = targets["Default"]
    patterns = target.fileset.patterns
    commands = target.task.commands

    event_handler = EventHandler(patterns, commands)

    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
