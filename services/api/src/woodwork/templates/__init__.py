"""Versioned trusted geometry templates; input cannot select arbitrary code."""
import json
from importlib.resources import files


def default_project_spec() -> dict:
    """Return a fresh, editable reference specification for the installed template."""
    return json.loads(files(__package__).joinpath("bookcase-default.json").read_text(encoding="utf-8"))
