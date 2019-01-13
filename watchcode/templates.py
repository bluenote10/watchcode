from __future__ import division, print_function

import argparse
import os
import glob


"""
class Template(object):
    def __init__(self, name, path):
        self.name = name
        self.path = path
"""

def get_available_templates():
    file_pattern = os.path.join(os.path.dirname(__file__), "templates", "*.yaml")

    files = glob.glob(file_pattern)
    available_templates = {
        os.path.basename(f)[:-5]: f
        for f in files
    }

    return available_templates


"""
def get_available_templates_names():
    file_pattern = os.path.join(os.path.dirname(__file__), "templates", "*.yaml")

    files = glob.glob(file_pattern)
    available_templates = [os.path.basename(f)[:-5] for f in files]

    return [t.name for t in get_available_templates()]
"""


def validate_template(name):
    available_templates = get_available_templates()
    if name in available_templates:
        with open(available_templates[name]) as f:
            return f.read()
    else:
        raise argparse.ArgumentTypeError(
            "Template name '{}' does not exist".format(name)
        )
