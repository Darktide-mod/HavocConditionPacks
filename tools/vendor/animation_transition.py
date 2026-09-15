"""stingray::AnimationTransition, stingray::AnimationTransitionSwitch, stingray::AnimationTransitionSwitchExit"""

from .. import deserializing as d
from ..import_base import Parser
from ..murmur.rainbow_table import IDString32
from .generic_structures import Array


class AnimationTransitionSwitchExit(Parser):
    """stingray::AnimationTransitionSwitchExit"""

    blend_settings_index: int
    interval_start: float
    interval_end: float
    exclude_start: bool
    exclude_end: bool

    def __init__(self, c: d.Cursor) -> None:
        self.blend_settings_index = c.ReadU32()
        self.interval_start = c.ReadF32()
        self.interval_end = c.ReadF32()
        self.exclude_start = c.ReadBool()
        self.exclude_end = c.ReadBool()


class AnimationTransitionSwitch(Parser):
    """stingray::AnimationTransitionSwitch"""

    bytecode: int
    exits: list[AnimationTransitionSwitchExit]

    def __init__(self, c: d.Cursor) -> None:
        self.bytecode = c.ReadU32()
        self.exits = Array(AnimationTransitionSwitchExit, c)


class AnimationTransition(Parser):
    """stingray::AnimationTransition"""

    event: IDString32
    index: int
    is_conditional_transition: bool

    def __init__(self, c: d.Cursor) -> None:
        self.event = c.ReadIDString32()
        self.index = c.ReadU32()
        self.is_conditional_transition = c.ReadBool()
