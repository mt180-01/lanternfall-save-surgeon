from pathlib import Path

from .checks import path_problem, result


def verify_input(value):
    problem = path_problem(value.path, ("saves", "edited"))
    if problem:
        return result(False, problem)
    if value.offset < 0 or not 1 <= value.length <= 2048:
        return result(False, "offset must be 0 or more and length between 1 and 2048")
    return result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    path = Path(workspace) / input_value.path
    if not path.is_file():
        return result(False, f"{input_value.path} does not exist")
    data = path.read_bytes()
    window = data[input_value.offset : input_value.offset + input_value.length]
    if output_value.total_size != len(data) or output_value.offset != input_value.offset:
        return result(False, "total_size or offset differs from the file")
    if len(window) != input_value.length or output_value.data_hex != window.hex():
        return result(False, "the hex is not the file's bytes at that offset")
    return result(True, "the bytes are exact", length=len(window))
