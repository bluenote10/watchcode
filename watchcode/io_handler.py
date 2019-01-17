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


class LaunchInfo(object):
    def __init__(self, trigger, commands, clear_screen, config_reloaded):
        self.trigger = trigger
        self.commands = commands
        self.clear_screen = clear_screen
        self.config_reloaded = config_reloaded


class IOHandler(object):
    """
    Helper class to handle asynchronous IO (running tasks, logging, event queuing).
    """

    def __init__(self, working_dir):
        self.working_dir = working_dir
        self.thread = None
        self.queued = None
        self.lock = threading.Lock()
        self.hidden_messages = []

    def _thread_func(self, launch_info):
        exec_infos = []

        if launch_info.clear_screen:
            self._clear_screen()

        print(" * Trigger: {}".format(launch_info.trigger))

        for command in launch_info.commands:
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

    def _log_event_stdout(self, matches, event):
        print(self._log_msg(matches, event))
        sys.stdout.flush()

    def _log_event_hidden(self, matches, event):
        self.hidden_messages.append(self._log_msg(matches, event))

    """
    def trigger(self, matches, event, commands, log_all, queue_trigger, clear_screen):
        with self.lock:
            # If we have no build running already...
            if self.thread is None:
                if matches:
                    if clear_screen:
                        self._clear_screen()
                    self._log_event_stdout(matches, event)
                    self.thread = threading.Thread(target=self._thread_func, args=(commands, clear_screen))
                    self.thread.start()
                else:
                    if log_all:
                        self._log_event_stdout(matches, event)

            # If we have a build in progress...
            else:
                if matches:
                    self._log_event_hidden(matches, event)
                    if queue_trigger:
                        self.queued = commands
                else:
                    if log_all:
                        self._log_event_hidden(matches, event)
    """

    def trigger(self, launch_info, queue_trigger):
        with self.lock:
            # If we have no build running already...
            if self.thread is None:
                #self._log_event_stdout(matches, event)
                self.thread = threading.Thread(target=self._thread_func, args=(launch_info,))
                self.thread.start()

            # If we have a build in progress...
            else:
                #self._log_event_hidden(matches, event)
                if queue_trigger:
                    self.queued = launch_info

    def on_thread_finished(self, exec_infos):
        with self.lock:
            print(" * Task summary:")
            all_good = True
            for exec_info in exec_infos:
                if exec_info.retcode == 0:
                    return_color = FG.green
                else:
                    return_color = FG.red
                    all_good = False
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

            if all_good:
                snd_file = os.path.join(os.path.dirname(__file__), "sounds", "456581__bumpelsnake__nameit5.wav")
            else:
                snd_file = os.path.join(os.path.dirname(__file__), "sounds", "377017__elmasmalo1__notification-pop.wav")
            p = subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-hide_banner", snd_file], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            p.wait()

            # Reset the thread state
            self.thread = None

            # Relaunch and reset queue state
            if self.queued is not None:
                launch_info = self.queued
                self.thread = threading.Thread(target=self._thread_func, args=(launch_info,))
                self.thread.start()
                self.queued = None

            sys.stdout.flush()

    @staticmethod
    def _log_msg(matches, event):
        if matches:
            col = FG.green
        else:
            col = FG.red
        return " * Event: {}{:<15s}{}{:s}{}".format(
            color(FG.white, style=Style.bold),
            event.type,
            color(col, style=Style.bold),
            event.path,
            color(),
        )

    @staticmethod
    def _clear_screen():
        if os.name == 'nt':
            os.system("cls")
        else:
            # Trying this approach to avoid losing scrollback:
            # https://askubuntu.com/a/997893/161463
            sys.stdout.write('\33[H\33[2J')
