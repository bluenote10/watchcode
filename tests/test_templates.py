from __future__ import division, print_function

import watchcode.templates as templates
import watchcode.config as config

import pytest

import os
import argparse


def test_available_templates():
    available_templates = templates.get_available_templates()
    assert len(available_templates) == 4


def test_get_template():
    t1_file, t1 = templates.get_template("nim")
    t2_file, t2 = templates.get_template("nim_min")
    assert t1_file.endswith("full.yaml")
    assert t2_file.endswith("minimal.yaml")
    assert os.path.exists(t1_file)
    assert os.path.exists(t2_file)


def test_render_template(tmpdir):
    with pytest.raises(argparse.ArgumentTypeError) as e:
        templates.render_template("non-existing")
        assert "Unknown template" in e

    with tmpdir.as_cwd():
        for name in templates.get_available_templates():
            template_string = templates.render_template(name)
            with open(config.DEFAULT_CONFIG_FILENAME, "w") as f:
                f.write(template_string)
            config.load_config(".", config.Overrides())

