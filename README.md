# watchcode

Generic tool to solve the **modify** + **re-run** problem. 
Cross-language, cross-build-system, cross-test-framework. 
Powered by Python / [watchdog](https://github.com/gorakhargosh/watchdog).

Features:

- Simple YAML file format to specify **which files** to monitor and **what task** to run.
- Different file matching styles (gitlike, regex, fnmatch).
- Within git repositories, matching can follow existing gitignore rules.
- Configurable event debouncing to account for editor peculiarities.
- Optional task success audio feedback*.
- Optional task success system notifications*.

[*] useful when working in single screen / full screen scenarios.

Setting up flawless file monitoring manually can be tricky: 
Sometimes trigger rules are too narrow / too broad, or editors might confuse watchers by unexpected ways to write files.
Watchcode's flexible matching features make it easy to get the right behavior.
Watchcode is written in Python, but can be used for any task from simple shell scripts, over dynamic languages, up to more complex build systems like CMake/Maven.


## Installation

For users familiar with Python:

```sh
pip install watchcode
```

Not familiar with Python? Here's the gist:

- Get & install virtualenv/pip (e.g. `sudo apt install virtualenv`).
- Create a virtualenv (e.g. `virtualenv ~/.virtualenvs/my_venv`).
- Activate virtualenv (e.g. `. ~/.virtualenvs/my_venv/bin/activate`).
- Ready to `pip install watchcode`...


## Demo


## Usage

Run `watchcode` in a directory that has a `.watchcode.yaml`.

To create a `.watchcode.yaml` either
- run `watchcode --init-config` to get a generic `.watchcode.yaml` or
- run `watchcode --init-config <LANGUAGE>` to get a basic config for a certain language.

A basic `.watchcode.yaml` for TDD in Python would for instance look like this:

```yaml
filesets:
  default:
    include:
      - "*.py"
      - "/*.yaml"
    exclude:
    exclude_gitignore: true
    match_mode: "gitlike"

tasks:
  default:
    fileset: default
    commands:
      - "py.test"

default_task: default
```

Notes:
- A fileset defines which and how files are monitored. 
  The config can have multiple filesets. 
  In the example there's only a single fileset called `default`, 
  which triggers on changes to Python files and top-level YAML files unless they are gitignored.
- A task references a filesets via its name and specifies a list of commands to run.
  Again, the config can have multiple tasks. 
  The example only has a single task called `default`, which runs `py.test`.
- The `default_task` setting references the currently active task.


## License

This project is licensed under the terms of the MIT license.
