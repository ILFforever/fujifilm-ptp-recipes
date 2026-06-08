"""
Reference snippets for Fujifilm custom recipe slots over USB PTP.

This is not a complete program. It intentionally avoids choosing a USB library.
Use it as a constants and encoding reference when building a real implementation.
"""

import struct
import unicodedata


FUJI_VENDOR_ID = 0x04CB
PTP_INTERFACE_CLASS = 0x06
MASS_STORAGE_INTERFACE_CLASS = 0x08

CONTAINER_COMMAND = 1
CONTAINER_DATA = 2
CONTAINER_RESPONSE = 3

GET_DEVICE_INFO = 0x1001
OPEN_SESSION = 0x1002
CLOSE_SESSION = 0x1003
GET_DEVICE_PROP_VALUE = 0x1015
SET_DEVICE_PROP_VALUE = 0x1016

RESPONSE_OK = 0x2001
RESPONSE_GENERAL_ERROR = 0x2002
RESPONSE_SESSION_NOT_OPEN = 0x2003
RESPONSE_DR_REJECTED_UNDER_PRIORITY = 0x201C
RESPONSE_SESSION_ALREADY_OPEN = 0x201E

FUJI_SLOT_SELECTOR = 0xD18C
FUJI_PRESET_NAME = 0xD18D
PRESET_BLOCK_START = 0xD18E
PRESET_BLOCK_END = 0xD1A5

PROPERTY = {
    "Dynamic Range": 0xD190,
    "Dynamic Range Priority": 0xD191,
    "Film Simulation": 0xD192,
    "Mono WC": 0xD193,
    "Mono MG": 0xD194,
    "Grain Effect": 0xD195,
    "Color Chrome": 0xD196,
    "Color Chrome FX Blue": 0xD197,
    "Smooth Skin": 0xD198,
    "White Balance": 0xD199,
    "WB Shift Red": 0xD19A,
    "WB Shift Blue": 0xD19B,
    "Color Temperature": 0xD19C,
    "Highlight Tone": 0xD19D,
    "Shadow Tone": 0xD19E,
    "Color": 0xD19F,
    "Sharpness": 0xD1A0,
    "High ISO NR": 0xD1A1,
    "Clarity": 0xD1A2,
}

SIGNED_PROPERTIES = {
    PROPERTY["Mono WC"],
    PROPERTY["Mono MG"],
    PROPERTY["WB Shift Red"],
    PROPERTY["WB Shift Blue"],
    PROPERTY["Highlight Tone"],
    PROPERTY["Shadow Tone"],
    PROPERTY["Color"],
    PROPERTY["Sharpness"],
    PROPERTY["Clarity"],
}

MONO_FILM_SIM_CODES = {6, 7, 8, 9, 10, 12, 13, 14, 15}

COLOR_ONLY_PROPERTIES = {
    PROPERTY["Color Chrome"],
    PROPERTY["Color Chrome FX Blue"],
    PROPERTY["Color"],
    PROPERTY["WB Shift Red"],
    PROPERTY["WB Shift Blue"],
}


def u16(value: int) -> bytes:
    return struct.pack("<H", value & 0xFFFF)


def i16(value: int) -> bytes:
    return struct.pack("<h", value)


def command_packet(code: int, tx_id: int, params=()) -> bytes:
    payload = b"".join(struct.pack("<I", p) for p in params)
    length = 12 + len(payload)
    return struct.pack("<IHHI", length, CONTAINER_COMMAND, code, tx_id) + payload


def data_packet(code: int, tx_id: int, payload: bytes) -> bytes:
    length = 12 + len(payload)
    return struct.pack("<IHHI", length, CONTAINER_DATA, code, tx_id) + payload


def ptp_string(text: str) -> bytes:
    if not text:
        return b"\x00"
    code_units = text.encode("utf-16le")
    char_count_including_null = (len(code_units) // 2) + 1
    if char_count_including_null > 255:
        raise ValueError("PTP string too long")
    return bytes([char_count_including_null]) + code_units + b"\x00\x00"


SAFE_NAME_CHARS = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "abcdefghijklmnopqrstuvwxyz"
    "0123456789 "
    "!\"#$%&'()*+,-./:;<=>?@[]\\^_{}|~"
)


def sanitize_preset_name(raw: str, fallback: str = "Untitled") -> str:
    folded = unicodedata.normalize("NFD", raw)
    out = []
    last_space = False
    for ch in folded:
        if unicodedata.category(ch) == "Mn":
            continue
        if ch in {"\u02bc", "\u2018", "\u2019", "\u201b"}:
            ch = "'"
        if ch not in SAFE_NAME_CHARS:
            ch = " "
        if ch == " ":
            if not last_space:
                out.append(ch)
            last_space = True
        else:
            out.append(ch)
            last_space = False
    safe = "".join(out).strip()[:25].rstrip()
    return safe or fallback


def scaled_dial_to_wire(dial: float) -> int:
    """For Highlight, Shadow, Color, Sharpness, Clarity, Mono WC, Mono MG."""
    return round(dial * 10)


HIGH_ISO_NR_DIAL_TO_WIRE = {
    -4: 32768,
    -3: 28672,
    -2: 16384,
    -1: 12288,
    0: 8192,
    1: 4096,
    2: 0,
    3: 24576,
    4: 20480,
}


def high_iso_nr_to_wire(dial: int) -> int:
    return HIGH_ISO_NR_DIAL_TO_WIRE.get(dial, 8192)


def grain_to_wire(label: str) -> int:
    return {
        "Weak Small": 2,
        "Strong Small": 3,
        "Weak Large": 4,
        "Strong Large": 5,
    }.get(label, 1)


def off_weak_strong_to_wire(label: str) -> int:
    return {"Weak": 2, "Strong": 3}.get(label, 1)


def dynamic_range_priority_to_wire(label: str) -> int:
    return {
        "Weak": 1,
        "Strong": 2,
        "Auto": 32768,
    }.get(label, 0)


def property_payload(prop_code: int, value: int) -> bytes:
    return i16(value) if prop_code in SIGNED_PROPERTIES else u16(value)


def wb_shift_to_wire(dial: int) -> int:
    if dial < -9 or dial > 9:
        raise ValueError("WB shift must be in the camera dial range -9..+9")
    return dial


def read_slot_sequence(slot_number: int):
    """
    Pseudocode:

    send OPEN_SESSION
    send GET_DEVICE_INFO
    send SET_DEVICE_PROP_VALUE FUJI_SLOT_SELECTOR with u16(slot_number)
    send GET_DEVICE_PROP_VALUE FUJI_PRESET_NAME
    for code in range(PRESET_BLOCK_START, PRESET_BLOCK_END + 1):
        send GET_DEVICE_PROP_VALUE code
    send CLOSE_SESSION
    """
    raise NotImplementedError


def write_slot_sequence(slot_number: int, raw_props: dict[int, int], name: str):
    """
    Pseudocode:

    send OPEN_SESSION
    send GET_DEVICE_INFO
    send SET_DEVICE_PROP_VALUE FUJI_SLOT_SELECTOR with u16(slot_number)
    send GET_DEVICE_INFO

    if Film Simulation is present, write it first.
    if Dynamic Range Priority is not Off, skip Dynamic Range 0xD190.
    write remaining props, skipping invalid dependent props.
    write FUJI_PRESET_NAME with ptp_string(sanitize_preset_name(name))

    send CLOSE_SESSION
    """
    raise NotImplementedError
