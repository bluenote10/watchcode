from __future__ import division, print_function

from watchcode.trigger import FileEvent


def test_file_event():

    def event(path):
        return FileEvent(path, "modified", is_dir=False)

    assert event(".watchcode.yaml").is_config_file
    assert event("./.watchcode.yaml").is_config_file
    assert not event("./sub/.watchcode.yaml").is_config_file

