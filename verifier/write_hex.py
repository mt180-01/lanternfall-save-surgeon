import hashlib
from pathlib import Path

from .checks import hex_problem, path_problem, result


def verify_input(value):
    problem = path_problem(value.path, ("edited",)) or hex_problem(value.data_hex)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    path = Path(workspace) / input_value.path
    if output_value.path != input_value.path or not path.is_file():
        return result(False, "the file was not written where it was asked")
    data = path.read_bytes()
    if data != bytes.fromhex(input_value.data_hex):
        return result(False, "the file does not hold exactly the bytes given")
    if output_value.size != len(data) or output_value.sha256 != hashlib.sha256(data).hexdigest():
        return result(False, "the reported size or hash differs from the file")
    return result(True, "the file is written", size=len(data))
