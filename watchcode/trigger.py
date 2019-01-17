from __future__ import division, print_function

import abc
import os
import six

from .colors import color, Style, FG
from .config import DEFAULT_CONFIG_FILENAME


@six.add_metaclass(abc.ABCMeta)
class Trigger:
    def instance_of(self, cls):
        return isinstance(self, cls)


class InitialTrigger(Trigger):
    def __str__(self):
        return "Initial trigger"


class ManualTrigger(Trigger):
    def __str__(self):
        return "Manual trigger"


class FileEvent(Trigger):
    def __init__(self, path, type, is_dir):
        self.path = path
        self.type = type
        self.is_dir = is_dir

    @property
    def path_normalized(self):
        if self.is_dir:
            if len(self.path) > 0 and self.path[-1] != os.sep:
                return self.path + os.sep
            else:
                return self.path
        else:
            return self.path

    def __str__(self):
        return "{}{} {}[{}]{}".format(
            color(FG.green, style=Style.bold),
            self.path,
            color(FG.white, style=Style.bold),
            self.type,
            color()
        )

    @property
    def is_config_file(self):
        path_components = os.path.split(self.path)
        # TODO: requires case insensitive matching for Windows
        return len(path_components) == 2 and path_components[1] == DEFAULT_CONFIG_FILENAME
