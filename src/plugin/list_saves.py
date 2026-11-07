from __future__ import annotations

import hashlib
from pathlib import Path

from contract import FileInfo, Folder, ListInput, ListOutput
from plugin.savefile import encode
from plugin.saves import SAVES


def list_saves(given: ListInput, workspace: Path) -> ListOutput:
    folder = workspace / given.folder.value
    if given.folder is Folder.SAVES:
        folder.mkdir(exist_ok=True)
        for slot, save in SAVES.items():
            (folder / f"slot{slot}.sav").write_bytes(encode(save))
    files = sorted(folder.glob("*.sav")) if folder.is_dir() else []
    return ListOutput(
        files=[
            FileInfo(path=f"{given.folder.value}/{file.name}", size=file.stat().st_size, sha256=hashlib.sha256(file.read_bytes()).hexdigest())
            for file in files
        ]
    )
