"""Pure C-01 P1/L1 request-file-path grammar; no filesystem authority.

The original string is inspected without normalization, trimming or I/O.
Passing this check does not qualify a root, target, handle or filesystem.
"""
from __future__ import annotations

import re


_PATH = re.compile(r'[A-Za-z]:\\[^\\/:<>"|?*\x00-\x1f\x7f]+(?:\\[^\\/:<>"|?*\x00-\x1f\x7f]+)*')
_ASCII_UPPER = str.maketrans("abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
_RESERVED = {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"} | {
    prefix + number for prefix in ("COM", "LPT") for number in "123456789¹²³"
}


def is_drive_request_file_path(value: object) -> bool:
    """Return only a grammar verdict, never a repaired path or an I/O grant."""
    if not isinstance(value, str) or _PATH.fullmatch(value) is None:
        return False
    for component in value[3:].split("\\"):
        if component.endswith((".", " ")):
            return False
        stem = component.split(".", 1)[0].rstrip(" ").translate(_ASCII_UPPER)
        if stem in _RESERVED:
            return False
    return True
