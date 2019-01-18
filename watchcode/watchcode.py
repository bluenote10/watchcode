#!/usr/bin/env python
# *-* encoding: utf-8
"""
Generic tool to watch for code changes and continuously execute commands.
"""

from __future__ import division, print_function

import argparse
import os
import logging
import sys
import time
import six
import subprocess

import yaml

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

import fnmatch
import re

#from watchcode.io_handler import IOHandler
from . import templates
from .io_handler import LaunchInfo, IOHandler
from .config import FileSet, Task, Target, load_config, DEFAULT_CONFIG_FILENAME
from .trigger import InitialTrigger, ManualTrigger, FileEvent

logger = logging.getLogger(__name__)


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
                FileEvent(event.src_path, event.event_type + "_from", event.is_directory),
                FileEvent(event.dest_path, event.event_type + "_to", event.is_directory),
            ]
        else:
            events = [
                FileEvent(event.src_path, event.event_type, event.is_directory),
            ]

        for event in events:
            self.handle_event(event)

    def handle_event(self, event):

        # First attempt to reload config (in cases where we have none)
        config_reloaded = False
        if event.is_config_file:
            logger.info("Reloading config...")
            print(" * Reloading config") # TODO we must not log here... during builds...
            self.load_config()
            config_reloaded = True
            # Hm, what if we return early, actually impossible, still not so nice
            # to communicate the config_reloaded via the trigger below?

        if self.target is None or self.config is None:
            return

        matches = self.target.fileset.matches(event)

        # There is one exception we should make for logging: We should not log
        # changes to '.watchcode.log' otherwise a log event would trigger yet
        # another change, creating a log loop.
        if event.basename != ".watchcode.log":
            logger.info(u"Event: {:<60s} {:<12} {}".format(
                event.path_normalized,
                event.type,
                u"✓" if matches else u"○",
            ))

        if matches:
            launch_info = LaunchInfo(
                trigger=event,
                commands=self.target.task.commands,
                clear_screen=self.target.task.clear_screen,
                config_reloaded=config_reloaded,
            )
            self.io_handler.trigger(
                launch_info, queue_trigger=self.target.task.queue_events,
            )

    def on_manual_trigger(self, is_initial=False):
        if is_initial:
            trigger = InitialTrigger()
        else:
            trigger = ManualTrigger()

        if self.target is None or self.config is None:
            return

        launch_info = LaunchInfo(
            trigger=trigger,
            commands=self.target.task.commands,
            clear_screen=self.target.task.clear_screen,
            config_reloaded=False,
        )
        self.io_handler.trigger(
            launch_info, queue_trigger=self.target.task.queue_events,
        )


def parse_args():
    template_names = ", ".join(
        sorted(templates.get_available_templates().keys())
    )

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
    parser.add_argument(
        "--init-config",
        metavar="<TEMPLATE>",
        help="Create a new '.watchcode.yaml' config in the current working directory "
             "from a preset. Available templates: {}".format(template_names),
        type=templates.validate_template,
    )
    parser.add_argument(
        "--log",
        action="store_true",
        help="Enable debug logging to file '.watchcode.log'.",
    )
    args = parser.parse_args()

    if args.log:
        log_file = os.path.join(args.dir, '.watchcode.log')
        #formatter = logging.Formatter(
        #    fmt='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
        #    datefmt='%H:%M:%S')
        #stream_handler = logging.FileHandler(log_file, mode='w')
        #stream_handler.setFormatter(formatter)
        #logger.setLevel(logging.INFO)
        #logger.addHandler(handler)
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s.%(msecs)03d | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S',
            filename=log_file,
            filemode="w",
        )
    return args


def main():
    args = parse_args()
    working_dir = args.dir

    if args.init_config is not None:
        config_path = os.path.join(working_dir, DEFAULT_CONFIG_FILENAME)
        if os.path.exists(config_path):
            print("Config file '{}' already exists. Remove file first "
                  "if you want a new config.".format(config_path))
            sys.exit(1)
        else:
            print(" * Creating config file '{}'.".format(config_path))
            with open(config_path, "w") as f:
                f.write(args.init_config)

    # TODO: Should we actually run the task once initially?
    # But then the above message would not make sense and we would never get a chance to
    # print the CTRL+C message. Well after a build, if no new one is scheduled...
    # Note that this would affect the "triggering events" semantics, because this initial
    # build would not have an explicit trigger. Maybe we simply have to use multiple types.

    event_handler = EventHandler(working_dir, override_target=args.target)
    event_handler.on_manual_trigger(is_initial=True)

    observer = Observer()
    observer.schedule(event_handler, working_dir, recursive=True)
    observer.start()  # TODO: catch OSError here? Thrown e.g. on wrong file permissions
    try:
        while True:
            time.sleep(1000)
        #while True:
        #    input_value = six.moves.input()
        #    if input_value == "":
        #        event_handler.on_manual_trigger()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
