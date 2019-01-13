from __future__ import division, print_function

import os
import sys
import subprocess
import threading
import time

from colors import color, FG, BG, Style


class ExecInfo(object):
    def __init__(self, command, runtime, retcode):
        self.command = command
        self.runtime = runtime
        self.retcode = retcode


class IOHandler(object):
    """
    Helper class to handle asynchronous IO (running tasks, logging, event queuing).
    """

    def __init__(self, working_dir):
        self.working_dir = working_dir
        self.thread = None
        self.queued = None
        self.lock = threading.Lock()

    def _thread_func(self, commands):
        sys.stdout.flush()
        exec_infos = []

        for command in commands:
            print(" * Running: {}{}{}".format(
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

        self.on_thread_finished(exec_infos)
        return

    def trigger_commands(self, commands, queue_trigger):
        with self.lock:
            if self.thread is None:
                self.thread = threading.Thread(target=self._thread_func, args=(commands,))
                self.thread.start()
            elif queue_trigger:
                self.queued = commands

    def on_thread_finished(self, exec_infos):
        with self.lock:
            for exec_info in exec_infos:
                print(" * Complete: {}{}{} took {}{:.1f}{} sec and returned {}{}{}.".format(
                    color(FG.blue, style=Style.bold),
                    exec_info.command,
                    color(),
                    color(FG.yellow, style=Style.bold),
                    exec_info.runtime,
                    color(),
                    color(FG.white, style=Style.bold),
                    exec_info.retcode,
                    color(),
                ))

            self.thread = None

            if self.queued is not None:
                commands = self.queued
                self.thread = threading.Thread(target=self._thread_func, args=(commands,))
                self.thread.start()
                self.queued = None
