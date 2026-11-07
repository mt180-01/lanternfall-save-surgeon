"""Checks shared by the tool verifiers. Pure functions of their arguments and the files on disk."""

import re
from pathlib import Path

from .lanternfall import SaveError, parse

NAME = re.compile(r"^(saves|edited)/[A-Za-z0-9_-]+\.sav$")


def result(valid, message, *, score=None, **details):
    return {
        "valid": valid,
        "score": float(valid) if score is None else score,
        "message": message,
        "details": details,
    }


def path_problem(path, folders):
    match = NAME.fullmatch(path)
    if not match or match.group(1) not in folders:
        return "path must be " + " or ".join(f"{folder}/<name>.sav" for folder in folders)
    return None


def hex_problem(text):
    if not text or len(text) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", text):
        return "hex must be one or more bytes of two hexadecimal digits each, with no spaces"
    return None


def read_save(workspace, path):
    """The parsed save at ``path`` in the workspace; raises SaveError if it is missing or malformed."""
    file = Path(workspace) / path
    if not file.is_file():
        raise SaveError(f"{path} does not exist")
    return parse(file.read_bytes())
