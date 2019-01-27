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

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import matching
from . import templates
from .io_handler import LaunchInfo, IOHandler
from .config import Overrides, ConfigError, ConfigFactory, DEFAULT_CONFIG_FILENAME
from .trigger import InitialTrigger, ManualTrigger, FileEvent
from .colors import color, FG

logger = logging.getLogger(__name__)


def parse_args():
    template_names = ", ".join(templates.get_available_templates())

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "task",
        default=None,
        nargs='?',
        help="Run a specific tasj. By default, uses the default task setting "
             "from the YAML config. If an explicit task is specified, the value "
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
        type=templates.render_template,
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


def extract_overrides(args):
    return Overrides(
        task_name=args.task,
    )


class EventHandler(FileSystemEventHandler):
    """ Watchcode's main event handler """

    def __init__(self, working_dir, config_factory):
        self.working_dir = working_dir
        self.config_factory = config_factory

        self.config = self.initial_config_load()

        self.io_handler = IOHandler(working_dir)

    def initial_config_load(self):
        try:
            print(" * Loading config")
            return self.config_factory.load_config()
        except ConfigError as e:
            print(" * {}Error reloading config{}:\n{}".format(
                color(FG.red),
                color(),
                str(e),
            ))
            sys.exit(1)

    def on_any_event(self, event):
        """
        Overrides EventHandler.on_any_event for general notifications.
        The implementation convert the raw event into our own simplified
        representation, which converts 'moved' event two separate events
        in order to avoid special handling for event.dest_path.
        """
        super(EventHandler, self).on_any_event(event)

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
            self.on_any_single_event(event)

    def on_any_single_event(self, event):
        """
        Actual event handler.
        """
        matches = matching.does_match(self.config.task.fileset, event)

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
                clear_screen=self.config.task.clear_screen,
                queue_events=self.config.task.queue_events,
                trigger=event,
                config_factory=self.config_factory,
                on_task_finished=self.on_task_finished,
            )
            self.io_handler.trigger(launch_info)

    def on_task_finished(self, config):
        """
        Callback for finished build.
        """
        self.config = config

    def on_manual_trigger(self, is_initial=False):
        """
        Interface for external triggers.
        """
        if is_initial:
            trigger = InitialTrigger()
        else:
            trigger = ManualTrigger()

        launch_info = LaunchInfo(
            clear_screen=self.config.task.clear_screen,
            queue_events=self.config.task.queue_events,
            trigger=trigger,
            config_factory=self.config_factory,
            on_task_finished=self.on_task_finished,
        )
        self.io_handler.trigger(launch_info)


def main():
    args = parse_args()
    overrides = extract_overrides(args)
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

    config_factory = ConfigFactory(working_dir, overrides)
    event_handler = EventHandler(working_dir, config_factory)
    event_handler.on_manual_trigger(is_initial=True)

    observer = Observer()
    observer.schedule(event_handler, working_dir, recursive=True)
    observer.start()  # TODO: catch OSError here? Thrown e.g. on wrong file permissions
    try:
        while True:
            time.sleep(1000)
        # TODO: make this optional
        # while True:
        #     input_value = six.moves.input()
        #     if input_value == "":
        #         event_handler.on_manual_trigger()
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
