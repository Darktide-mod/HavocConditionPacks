"""stingray::AnimationBlendSettings"""

from ..deserializing import Cursor
from ..import_base import Parser
from ..murmur.rainbow_table import IDString32


class AnimationBlendSettingsVT2(Parser):
    """stingray::AnimationBlendSettings"""

    to: int
    blend: int
    mode: int
    on_beat: IDString32
    unk1: int
    unk2: int
    unk3: int

    def __init__(self, c: Cursor) -> None:
        self.to = c.ReadU32()
        self.blend = c.ReadU32()
        self.mode = c.ReadU32()
        self.on_beat = c.ReadIDString32()
        self.unk1 = c.ReadU32()
        self.unk2 = c.ReadU32()
        self.unk3 = c.ReadU32()
