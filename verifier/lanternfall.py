"""The reference parser for Lanternfall saves: strict, and independent of the plugin's own reader.

    magic "LNTN" | version u16 | player name (varint length + UTF-8) | payload length u32 | CRC-32 u32 | payload

The payload is masked by xor with the player's name bytes, repeated; the CRC-32 is of the payload before masking.
The plaintext payload is level u16 | playtime u32 | gold u32 | zone u8 | lifetime gold u32 | records | end record,
and a record is type u8 | length u16 | value. All integers are little-endian.
"""

MAGIC = b"LNTN"
GOLD_CAP = 999_999
ITEM = 0x01
END = 0xFF
EMBER_KEY = "Ember Key"


class SaveError(Exception):
    """The bytes are not a well-formed Lanternfall save."""


def make_table():
    table = []
    for number in range(256):
        for _ in range(8):
            number = (number >> 1) ^ 0xEDB88320 if number & 1 else number >> 1
        table.append(number)
    return table


TABLE = make_table()


def crc32(data):
    crc = 0xFFFFFFFF
    for byte in data:
        crc = TABLE[(crc ^ byte) & 0xFF] ^ (crc >> 8)
    return crc ^ 0xFFFFFFFF


def number(data, position, size):
    if position + size > len(data):
        raise SaveError("the file ends inside a field")
    return int.from_bytes(data[position : position + size], "little")


def varint(data, position):
    value = shift = count = 0
    while True:
        if position + count >= len(data):
            raise SaveError("the file ends inside a varint")
        byte = data[position + count]
        count += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            break
        shift += 7
    if count > 1 and data[position + count - 1] == 0:
        raise SaveError("a varint is not in its shortest form")
    return value, position + count


def unmask(masked, player):
    key = player.encode("utf-8")
    return bytes(byte ^ key[index % len(key)] for index, byte in enumerate(masked))


def item_of(value):
    """(name, quantity) of an item record's value."""
    length, position = varint(value, 0)
    if len(value) != position + length + 2:
        raise SaveError("an item record does not end after its quantity")
    try:
        name = value[position : position + length].decode("utf-8")
    except UnicodeDecodeError as error:
        raise SaveError("an item name is not UTF-8") from error
    return name, number(value, position + length, 2)


def parse(data):
    if data[:4] != MAGIC:
        raise SaveError("not a Lanternfall save: the magic is missing")
    version = number(data, 4, 2)
    length, position = varint(data, 6)
    if position + length > len(data):
        raise SaveError("the player name runs past the end of the file")
    try:
        player = data[position : position + length].decode("utf-8")
    except UnicodeDecodeError as error:
        raise SaveError("the player name is not UTF-8") from error
    position += length
    size, stored = number(data, position, 4), number(data, position + 4, 4)
    masked = data[position + 8 :]
    if not player or len(masked) != size:
        raise SaveError(f"the payload is {len(masked)} bytes but the header says {size}")
    payload = unmask(masked, player)
    if len(payload) < 15:
        raise SaveError("the payload is shorter than its fixed fields")
    records, at = [], 15
    while True:
        kind, count = number(payload, at, 1), number(payload, at + 1, 2)
        at += 3
        if kind == END:
            break
        if at + count > len(payload):
            raise SaveError("a record runs past the payload")
        records.append((kind, payload[at : at + count]))
        at += count
    if at != len(payload) or count != 0:
        raise SaveError("the payload does not end at the end record")
    computed = crc32(payload)
    return {
        "player": player,
        "version": version,
        "level": number(payload, 0, 2),
        "playtime_seconds": number(payload, 2, 4),
        "gold": number(payload, 6, 4),
        "zone": number(payload, 10, 1),
        "lifetime_gold": number(payload, 11, 4),
        "records": records,
        "stored_crc": stored,
        "computed_crc": computed,
        "crc_ok": stored == computed,
    }
