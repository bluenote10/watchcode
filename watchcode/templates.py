from __future__ import division, print_function

import argparse
import os


class Template(object):
    def __init__(self, includes, excludes, commands):
        self.includes = includes
        self.excludes = excludes
        self.commands = commands


TEMPLATES = {
    "generic": Template(
        includes=["*"],
        excludes=[],
        commands=["echo 'Running task...'"],
    ),
    "python": Template(
        includes=["*.py"],
        excludes=["*.pyc", "__pycache__"],
        commands=["py.test"],
    ),
    "cmake": Template(
        includes=["*.c", "*.cpp", "*.c++", "*.h", "*.hpp", "*.h++"],
        excludes=["*.so"],
        commands=["mkdir -p build && cmake .. && make"],
    ),
    "node": Template(
        includes=["*.js", "*.ts", "*.html", "*.css"],
        excludes=[],
        commands=["npm start"],
    ),
    "nim": Template(
        includes=["*.nim"],
        excludes=[],
        commands=["nim -r c src/main.nim"],
    ),
}


def make_indented_yaml_list(l, indentation):
    join_str = "\n" + (" " * indentation)
    return join_str.join([
        '- "{}"'.format(x) for x in l
    ])


def get_available_templates():
    available_templates = list(TEMPLATES.keys())
    available_templates += [
        template_name + "_min" for template_name in list(TEMPLATES.keys())
    ]
    available_templates = sorted(available_templates)

    return available_templates


def get_template(template_name):
    if template_name.endswith("_min"):
        template_file = "minimal.yaml"
        template = TEMPLATES[template_name[:-4]]
    else:
        template_file = "full.yaml"
        template = TEMPLATES[template_name]
    return (
        os.path.join(os.path.dirname(__file__), "templates", template_file),
        template,
    )


def render_template(name):
    # Note this function raises argparse.ArgumentTypeError because we use it
    # directly in the argparsing.
    if name == "":
        name = "generic"

    try:
        template_file, template = get_template(name)
    except KeyError:
        raise argparse.ArgumentTypeError(
            "Unknown template name '{}'.".format(name)
        )

    try:
        with open(template_file) as f:
            content = f.read()
    except IOError as e:
        raise argparse.ArgumentTypeError(
            "Failed to load template file '{}':\n{}".format(template_file, str(e))
        )

    try:
        content_rendered = content.format(
            includes=make_indented_yaml_list(template.includes, 6),
            excludes=make_indented_yaml_list(template.excludes, 6),
            commands=make_indented_yaml_list(template.commands, 6),
        )
        return content_rendered
    except (KeyError, IndexError) as e:
        raise argparse.ArgumentTypeError(
            "Failed to render template '{}' does not exist:\n{}".format(name, str(e))
        )
