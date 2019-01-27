from __future__ import division, print_function

import pytest
from watchcode.config import *


CONFIG_VALID = """\
filesets:
  default:
    include:
      - ".watchcode.yaml"
      - "*.py"
      - "*"
    exclude:
      - ".watchcode.log"
    exclude_gitignore: true
    match_mode: "fnmatch"

tasks:
  default:
    fileset: default
    commands:
      - "py.test"
    clear_screen: true
    queue_events: false

  other:
    fileset: default
    commands:
      - "other"
    clear_screen: true
    queue_events: false

default_task: default
log: false
sound: true
"""

CONFIG_VALID_MIN = """\
filesets:
  default:
    include:
      - ".watchcode.yaml"
    exclude:

tasks:
  default:
    fileset: default
    commands:
      - "py.test"

default_task: default
"""

CONFIG_INVALID_DEFAULT_TASK = """\
filesets:
  default:
    include:
      - ".watchcode.yaml"
    exclude:

tasks:
  default:
    fileset: default
    commands:
      - "py.test"

default_task: non-existing
"""

CONFIG_INVALID_MATCH_MODE = """\
filesets:
  default:
    include:
      - ".watchcode.yaml"
    exclude:
    match_mode: non-existing

tasks:
  default:
    fileset: default
    commands:
      - "py.test"

default_task: default
"""


def load_test_config(tmpdir, config_string, overrides=None):
    if overrides is None:
        overrides = Overrides()
    with tmpdir.as_cwd():
        with open(DEFAULT_CONFIG_FILENAME, "w") as f:
            f.write(config_string)
        return load_config(".", overrides)


def test_fileset_validate():

    def ref_data():
        return {
            "include": ["*"],
            "exclude": None,
            "match_mode": "gitlike",
            "exclude_gitignore": True,
        }

    validated = FileSet.validate(ref_data())
    assert isinstance(validated, FileSet)

    data = ref_data()
    data["extra_key"] = "some"
    with pytest.raises(ConfigError) as e:
        validated = FileSet.validate(data)
    assert "Fileset contains unexpected key" in str(e)
    assert "'extra_key'" in str(e)


def test_config_overrides(tmpdir):
    overrides = Overrides(task_name="other")
    c1 = load_test_config(tmpdir, CONFIG_VALID)
    c2 = load_test_config(tmpdir, CONFIG_VALID, overrides)

    assert c1.task.commands[0] == "py.test"
    assert c2.task.commands[0] == "other"


def test_load_config(tmpdir):
    with tmpdir.as_cwd():

        # non-existing confing
        with pytest.raises(ConfigError) as e:
            load_config(".", Overrides())
            assert "Could not find" in e

        # malformed config
        with open(DEFAULT_CONFIG_FILENAME, "w") as f:
            f.write("'")
        with pytest.raises(ConfigError) as e:
            load_config(".", Overrides())
            assert "Could not read/parse" in e

        # TODO: add test with where working_dir is not "."

    c = load_test_config(tmpdir, CONFIG_VALID)
    c = load_test_config(tmpdir, CONFIG_VALID_MIN)
    with pytest.raises(ConfigError):
        load_test_config(tmpdir, CONFIG_INVALID_DEFAULT_TASK)
    with pytest.raises(ConfigError):
        load_test_config(tmpdir, CONFIG_INVALID_MATCH_MODE)
