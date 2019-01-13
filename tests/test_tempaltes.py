from __future__ import division, print_function

import watchcode.templates as templates


def test_available_templates():
    available_templates = templates.get_available_templates()
    assert "python" in available_templates
    assert "nim" in available_templates

