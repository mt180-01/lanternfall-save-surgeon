from .checks import hex_problem, result
from .lanternfall import crc32


def verify_input(value):
    problem = hex_problem(value.data_hex)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    expected = crc32(bytes.fromhex(input_value.data_hex))
    if output_value.crc32 != expected or output_value.little_endian_hex != expected.to_bytes(4, "little").hex():
        return result(False, f"the CRC-32 should be {expected:#010x}")
    return result(True, "the CRC-32 is right", crc32=expected)
