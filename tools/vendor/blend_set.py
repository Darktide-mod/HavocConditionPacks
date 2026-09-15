"""stingray::BlendSet"""

from ..deserializing import Cursor
from .base import Parser


class BlendSet(Parser):
    """stingray::BlendSet"""

    bone_weights: list[float]

    unk_arr: list[int]
    unk_bool: bool

    def __init__(self, c: Cursor) -> None:
        self.bone_weights = c.ReadF32Array()
        self.unk_arr = c.ReadU32Array()
        self.unk_bool = c.ReadBool()
