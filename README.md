# watchcode [![Build Status](https://travis-ci.org/bluenote10/watchcode.svg?branch=master)](https://travis-ci.org/bluenote10/watchcode) [![Build status](https://ci.appveyor.com/api/projects/status/robm64ar9dufb5g0?svg=true)](https://ci.appveyor.com/project/bluenote10/watchcode) [![license](https://img.shields.io/github/license/mashape/apistatus.svg)](LICENSE)

Generic tool to solve the **modify** + **re-run** problem. 
Cross-platform, cross-language, cross-build-system. 
Powered by Python / [watchdog](https://github.com/gorakhargosh/watchdog).

![demo](/../examples/examples/python.gif)

### Features

- Simple YAML file format to specify **which files** to monitor and **what task** to run.
- Different file matching styles (gitlike, regex, fnmatch).
- Within git repositories, trigger rules can leverage existing gitignore rules.
- Trigger debouncing to account for editor peculiarities.
- Config auto-reloading, i.e., any config change (trigger rules / commands) gets picked up automatically — no restarts required.
- Optional task success audio feedback*.
- Optional task success system notifications*.

[*] useful when working in single screen / full screen scenarios.

### Why watchcode?

Many build tools offer watch + run functionality, 
but they solve the problem only for a particular language/framework, 
and the quality/features are sometimes lacking.
I'm jumping between languages a lot, and I wanted a solution that works everywhere.
Watchcode is written in Python, but can be used for any task from simple shell scripts, over dynamic languages, up to more complex build systems like CMake/Maven.

Note that setting up file monitoring generically can be tricky: 
Sometimes trigger rules are too narrow / too broad, or editors might confuse watchers by unexpected ways to write files.
Watchcode's makes it easy to get the right behavior by offering flexible matching schemes and leveraging existing gitignore rules.


## Installation

For users familiar with Python (I'll probably upload to PyPI soon):

```sh
pip install git+https://github.com/bluenote10/watchcode
```

Not familiar with Python? Here's the gist:

- Get & install virtualenv/pip (e.g. `sudo apt install virtualenv`).
- Create a virtualenv (e.g. `virtualenv ~/.virtualenvs/my_venv`).
- Activate virtualenv (e.g. `. ~/.virtualenvs/my_venv/bin/activate`).
- Ready to `pip install watchcode`...


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
