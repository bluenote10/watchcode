from __future__ import division, print_function

import pytest
from watchcode.config import *


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
