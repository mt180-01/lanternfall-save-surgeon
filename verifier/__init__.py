"""The deterministic verifier: each tool's checks live in its own module, on contract instances."""

from contract import Task, Tool

from . import (
    crc32_hex,
    edit_task,
    inspect_save,
    list_saves,
    original_save,
    read_hex,
    write_hex,
    xor_hex,
)

TOOLS = {
    Tool.LIST_SAVES: list_saves,
    Tool.INSPECT_SAVE: inspect_save,
    Tool.READ_HEX: read_hex,
    Tool.CRC32_HEX: crc32_hex,
    Tool.XOR_HEX: xor_hex,
    Tool.WRITE_HEX: write_hex,
    Tool.ORIGINAL_SAVE: original_save,
}

# task -> its output's check, verify_task(arguments, output, reference, workspace)
TASKS = {Task.EDIT_SAVE: edit_task.verify_task}


def verify_input(tool, value):
    return TOOLS[Tool(tool)].verify_input(value)


def verify_output(tool, input_value, output_value, workspace):
    return TOOLS[Tool(tool)].verify_output(input_value, output_value, workspace)


def verify_task(task, arguments, output, reference, workspace):
    return TASKS[Task(task)](arguments, output, reference, workspace)
