# *-* encoding: utf-8
from __future__ import division, print_function

import logging
import datetime
import os
import sys
import subprocess
import threading
import time

from .colors import color, FG, BG, Style
from .config import ConfigError

logger = logging.getLogger(__name__)


class StoppableThread(threading.Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self):
        super(StoppableThread, self).__init__()
        self._stop_event = threading.Event()

    def stop(self):
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()


class Debouncer(object):
    def __init__(self):
        self.lock = threading.Lock()

        self.status = None
        self.thread = None
        self.queued = None
        self.trigger_time = None

        # We cannot bind func/debounce_time to the thread function,
        # because otherwise we couldn't update the func anymore during
        # waiting.
        self.func = None
        self.debounce_time = None

    def _thread_func(self):
        while True:
            # Note the sleep based implementation has the drawback that something
            # like this would behave a bit unexpected:
            #
            #     debouncer.trigger(f, 1.0)
            #     time.sleep(0.001)
            #     debouncer.trigger(f, 0.001)
            #
            # After the first trigger we would sleep for an entire second, and even
            # though the second trigger updates self.debounce_time, we cannot stop
            # the ongoing sleep. Do we want to support this?
            trigger_time_debounced = self.trigger_time + datetime.timedelta(seconds=self.debounce_time)
            # print("trigger time:           {}".format(self.trigger_time))
            # print("trigger time debounced: {}".format(trigger_time_debounced))
            now = datetime.datetime.now()
            time_to_sleep = (trigger_time_debounced - now).total_seconds()
            # print("time to sleep: {}".format(time_to_sleep))
            if time_to_sleep > 0:
                time.sleep(time_to_sleep)
            else:
                break
        with self.lock:
            self.status = "running"
        logger.info(u"Task [---]: debounce wait finished, starting task")
        self.func()
        logger.info("Task [▴▴▴]: finished")
        with self.lock:
            if self.queued is None:
                self.status = None
                self.thread = None
            else:
                logger.info("Task [▾▾▾]: starting thread (from queued trigger)")
                # unwrap / unset queued args
                (func, debounce_time) = self.queued
                self.queued = None
                # update trigger
                self.trigger_time = datetime.datetime.now()
                # update args
                self.func = func
                self.debounce_time = debounce_time
                # change status
                self.status = "waiting"
                self.thread = self._start_thread()

    def trigger(self, func, debounce_time, enqueue):
        with self.lock:
            if self.status is None:
                logger.info(u"Task [▾▾▾]: starting thread")
                # update trigger
                self.trigger_time = datetime.datetime.now()
                # update args
                self.func = func
                self.debounce_time = debounce_time
                # change status
                self.status = "waiting"
                self.thread = self._start_thread()
            elif self.status == "waiting":
                logger.info(u"Task [---]: debouncing event")
                # update trigger
                self.trigger_time = datetime.datetime.now()
                # update args
                self.func = func
                self.debounce_time = debounce_time
                # no status change
            elif self.status == "running":
                # update args (delayed)
                if enqueue:
                    self.queued = (func, debounce_time)
                    logger.info("Task [---]: still in progress => queuing trigger")
                else:
                    logger.info("Task [---]: still in progress => discarding trigger")

    def _start_thread(self):
        thread = threading.Thread(target=self._thread_func)
        thread.start()
        return thread


class ExecInfo(object):
    def __init__(self, command, runtime, retcode):
        self.command = command
        self.runtime = runtime
        self.retcode = retcode


class LaunchInfo(object):
    def __init__(self, old_config, trigger, config_factory, on_task_finished):
        self.old_config = old_config
        self.trigger = trigger
        self.config_factory = config_factory
        self.on_task_finished = on_task_finished


class IOHandler(object):
    """
    Helper class to handle asynchronous IO (running tasks, logging, event queuing).
    """

    def __init__(self, working_dir):
        self.working_dir = working_dir
        self.debouncer = Debouncer()

    def trigger(self, launch_info):
        self.debouncer.trigger(
            lambda: self._run_task(launch_info),
            0.2,    # TODO make configurable
            launch_info.old_config.task.queue_events,
        )

    def _run_task(self, launch_info):
        exec_infos = []
        old_config = launch_info.old_config

        if old_config.task.clear_screen:
            self._clear_screen()

        print(" * Trigger: {}".format(launch_info.trigger))

        try:
            config = launch_info.config_factory.load_config()
        except ConfigError as e:
            print(" * {}Error reloading config{}:\n{}".format(
                color(FG.red),
                color(),
                e,
            ))
            # Note: No config available, fallback to old config...
            if old_config.sound:
                self._notify_sound(success=False)
            if old_config.notifications:
                messages = ["Error reloading config:\n{}".format(e)]
                self._notify_display(success=False, messages=messages)
            return

        for command in config.task.commands:
            # additional newline to separate from task output
            print(" * Running: {}{}{}\n".format(
                color(FG.blue, style=Style.bold),
                command,
                color()
            ))
            sys.stdout.flush()

            t1 = time.time()
            proc = subprocess.Popen(command, shell=True, cwd=self.working_dir)
            retcode = proc.wait()
            t2 = time.time()
            exec_infos.append(ExecInfo(command, t2 - t1, retcode))

        success = self._report_task_result(exec_infos)
        if config.sound:
            self._notify_sound(success)
        if config.notifications:
            messages = [
                "'{}' took {:.1f} sec and returned {}.".format(e.command, e.runtime, e.retcode)
                for e in exec_infos
            ]
            self._notify_display(success, messages)

        # Return re-loaded config to monitoring thread
        launch_info.on_task_finished(config)

    def _report_task_result(self, exec_infos):
        # additional newline to separate from task output
        print("\n * Task summary:")
        success = True
        for exec_info in exec_infos:
            if exec_info.retcode == 0:
                return_color = FG.green
            else:
                return_color = FG.red
                success = False
            print("   {}{}{} took {}{:.1f}{} sec and returned {}{}{}.".format(
                color(FG.blue, style=Style.bold),
                exec_info.command,
                color(),
                color(FG.yellow, style=Style.bold),
                exec_info.runtime,
                color(),
                color(return_color, style=Style.bold),
                exec_info.retcode,
                color(),
            ))
        print(" * Monitoring '{}' for changes... [Press <CTRL>+C to exit, <ENTER> to re-run]".format(self.working_dir))
        sys.stdout.flush()
        return success

    @staticmethod
    def _notify_sound(success):
        # TODO: make configurable
        file_positive = "456581__bumpelsnake__nameit5.wav"
        file_negative = "377017__elmasmalo1__notification-pop.wav"
        if success:
            snd_file = os.path.join(os.path.dirname(__file__), "sounds", file_positive)
        else:
            snd_file = os.path.join(os.path.dirname(__file__), "sounds", file_negative)
        try:
            p = subprocess.Popen(
                ["ffplay", "-nodisp", "-autoexit", "-hide_banner", snd_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            p.wait()
        except Exception as e:
            print(" * Failed to play sound notification:\n{}".format(e))

    @staticmethod
    def _notify_display(success, messages):
        if success:
            title = "SUCCESS"
        else:
            title = "FAILURE"
        try:
            p = subprocess.Popen(
                ["notify-send", title, "\n".join(messages)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            p.wait()
        except Exception as e:
            print(" * Failed to send notification:\n{}".format(e))

    @staticmethod
    def _clear_screen():
        if os.name == 'nt':
            os.system("cls")
        else:
            # Trying this approach to avoid losing scrollback:
            # https://askubuntu.com/a/997893/161463
            sys.stdout.write('\33[H\33[2J')
