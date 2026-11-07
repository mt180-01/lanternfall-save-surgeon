from .checks import path_problem, read_save, result
from .lanternfall import ITEM, SaveError, item_of


def verify_input(value):
    problem = path_problem(value.path, ("saves", "edited"))
    return result(False, problem) if problem else result(True, "input is valid")


def verify_output(input_value, output_value, workspace):
    try:
        save = read_save(workspace, input_value.path)
        items = [item_of(value) for kind, value in save["records"] if kind == ITEM]
    except SaveError as error:
        return result(False, f"{input_value.path} cannot be read by the reference parser: {error}")
    shown = {
        "player": output_value.player,
        "level": output_value.level,
        "gold": output_value.gold,
        "lifetime_gold": output_value.lifetime_gold,
        "checksum_ok": output_value.checksum_ok,
        "items": [(item.name, item.quantity) for item in output_value.items],
        "other_records": len(output_value.other_records),
    }
    actual = {
        "player": save["player"],
        "level": save["level"],
        "gold": save["gold"],
        "lifetime_gold": save["lifetime_gold"],
        "checksum_ok": save["crc_ok"],
        "items": items,
        "other_records": sum(1 for kind, _ in save["records"] if kind != ITEM),
    }
    wrong = sorted(name for name in actual if shown[name] != actual[name])
    if wrong:
        return result(False, f"inspect disagrees with the reference parser on {', '.join(wrong)}")
    return result(True, "inspect agrees with the reference parser")
