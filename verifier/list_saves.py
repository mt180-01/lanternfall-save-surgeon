import hashlib
from pathlib import Path

from .checks import result
from .lanternfall import SaveError, parse


def verify_input(value):
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    folder = input_value.folder.value
    paths = [file.path for file in output_value.files]
    if paths != sorted(paths) or any(path.rpartition("/")[0] != folder for path in paths):
        return result(False, f"files must be listed by path, all in {folder}/")
    for file in output_value.files:
        path = Path(workspace) / file.path
        if not path.is_file():
            return result(False, f"{file.path} is listed but does not exist")
        data = path.read_bytes()
        if file.size != len(data) or file.sha256 != hashlib.sha256(data).hexdigest():
            return result(False, f"{file.path}: the size or hash differs from the file on disk")
    if folder == "saves":
        if paths != [f"saves/slot{slot}.sav" for slot in range(1, 6)]:
            return result(False, "saves/ must hold exactly slot1.sav to slot5.sav")
        try:
            if not all(parse((Path(workspace) / path).read_bytes())["crc_ok"] for path in paths):
                return result(False, "a listed save fails its own checksum")
        except SaveError as error:
            return result(False, f"a listed save is malformed: {error}")
    return result(True, "the listing is exact", files=len(paths))
