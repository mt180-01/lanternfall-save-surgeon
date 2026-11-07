# Lanternfall Save Surgeon

A `nanoagent.plugin/v0001` plugin that checks whether an agent can reverse-engineer a binary file format and
edit a file in it without breaking it.

Lanternfall is a fictional game. The agent gets five `.sav` files and a read-only `inspect` command that prints
gold, level and inventory. There is no tool for writing a save: it has only generic byte tools. The format has a
magic number, little-endian fields, varint-prefixed strings, an inventory of type-length-value records, a CRC-32
checksum and an XOR mask keyed by the player's name. The task: set current gold to 999,999, add one Ember Key,
change nothing else.

The traps: gold appears twice (current gold and lifetime earnings) and only current gold changes; editing the
bytes without recomputing the checksum fails; 1,000,000 is over the game's cap; one save already holds an Ember
Key; one is already at the cap; one has an empty inventory; one has a multi-byte name; unknown record types must
be kept byte for byte.

## Tools

| Tool | Does | Code |
|---|---|---|
| `list_saves` | Lists the `.sav` files in `saves/` or `edited/`; the first listing of `saves/` creates the five saves | `src/plugin/list_saves.py` |
| `inspect_save` | The game's read-only inspect command: player, level, gold, lifetime gold, inventory, checksum validity | `src/plugin/inspect_save.py` |
| `read_hex` | Reads a range of bytes from a save as hexadecimal text | `src/plugin/byte_tools.py` |
| `crc32_hex` | The standard CRC-32 of some bytes | `src/plugin/byte_tools.py` |
| `xor_hex` | Xors some bytes with a repeating key | `src/plugin/byte_tools.py` |
| `write_hex` | Writes bytes to a file in `edited/`; it does not know the format | `src/plugin/byte_tools.py` |
| `original_save` | The reference: the original fields of a save (never offered to the agent) | `src/plugin/original_save.py` |

### Tasks

| Task | Does | Runner |
|---|---|---|
| `edit-lanternfall-save` | Sets a save's gold to 999,999 and adds one Ember Key, changing nothing else | `agent`, with `list_saves`, `inspect_save`, `read_hex`, `crc32_hex`, `xor_hex`, `write_hex`; reference `original_save` |

The verifier (`verifier/`) is plain Python and calls no model. Its own strict parser
(`verifier/lanternfall.py`, with a pure-Python CRC-32) loads the edited file and checks the checksum, the new
current gold and the cap, that lifetime gold, name, version, level, playtime and zone are unchanged, that every
other inventory record is byte-identical and in order, that exactly one Ember Key record holds the old quantity
plus one, and that the original save is untouched.

## Layout

```text
.
├── nanoagent.yaml   # manifest (a slimconfig ManifestConfig): id, runtime, permissions, tools, tasks
├── contract.py      # each tool's and task's typed input and output: slimconfig Output classes
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .gitignore
├── .env             # environment variable NAMEs this plugin needs, never values
├── src/plugin/      # the MCP server: __main__.py, its IMPLEMENTATIONS, the save format and the tools
├── tests/
├── ui/              # how the page draws the outputs: renderers.js and renderers.css
├── product/         # the product page a catalog shows: product.yaml and icon.svg
└── verifier/        # deterministic verifier package
```

## Develop and run

```bash
uv sync --extra dev
uv run pytest
uv run ruff check .
```

Publishing checks every plugin rule: push the plugin to a public GitHub
repository and submit it on RUSH Lab.
