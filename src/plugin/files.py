"""Where the tools may read and write inside the workspace."""

from __future__ import annotations

import re
from pathlib import Path

from contract import Folder

NAME = re.compile(r"^[A-Za-z0-9_-]+\.sav$")


def resolve(workspace: Path, path: str, folders: tuple[Folder, ...]) -> Path:
    """The file ``path`` names: ``<folder>/<name>.sav`` of one of ``folders``, inside the workspace."""
    parts = Path(path).parts
    if len(parts) != 2 or parts[0] not in {folder.value for folder in folders} or not NAME.fullmatch(parts[1]):
        allowed = " or ".join(f"{folder.value}/<name>.sav" for folder in folders)
        raise ValueError(f"path must be {allowed}, inside the plugin workspace")
    return workspace.resolve() / parts[0] / parts[1]


def parse_hex(text: str) -> bytes:
    if not text or len(text) % 2 or not re.fullmatch(r"[0-9a-fA-F]+", text):
        raise ValueError("hex must be one or more bytes of two hexadecimal digits each, with no spaces")
    return bytes.fromhex(text)
