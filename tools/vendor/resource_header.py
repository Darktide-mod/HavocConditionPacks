"""Generic Darktide resource header"""

from ..deserializing import Cursor
from ..murmur.rainbow_table import IDString64
from .base import Parser


class DTHeader(Parser):
    """Found at the beginning of most (all?) resource files"""

    resource_type: IDString64
    name: IDString64
    unk1: int
    unk2: int
    unk3: int
    unk4: bool
    resource_len: int
    unk5: bool
    stream_name_len: int

    def __init__(self, c: Cursor) -> None:
        self.resource_type = c.ReadIDString64()
        self.name = c.ReadIDString64()
        self.unk1 = c.ReadU32()
        self.unk2 = c.ReadU32()
        self.unk3 = c.ReadU32()
        self.unk4 = c.ReadBool()
        self.resource_len = c.ReadU32()
        self.unk5 = c.ReadBool()
        self.stream_name_len = c.ReadU32()
