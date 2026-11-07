from .checks import hex_problem, result


def verify_input(value):
    problem = hex_problem(value.data_hex) or hex_problem(value.key_hex)
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    data, key = bytes.fromhex(input_value.data_hex), bytes.fromhex(input_value.key_hex)
    expected = bytes(byte ^ key[index % len(key)] for index, byte in enumerate(data)).hex()
    if output_value.data_hex != expected:
        return result(False, "the xor is not the data xor the repeated key")
    return result(True, "the xor is right", bytes=len(data))
