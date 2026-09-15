"""stingray::AnimationLayer"""

from ..deserializing import Cursor
from .animation_state import AnimationStateDT, AnimationStateVT1, AnimationStateVT2
from .base import Parser
from .generic_structures import Array


class AnimationLayerVT1(Parser):
    """stingray::AnimationLayer"""

    states: list[AnimationStateVT1]
    default_state: int

    def __init__(self, c: Cursor) -> None:
        self.states = Array(AnimationStateVT1, c)
        self.default_state = c.ReadU32()


class AnimationLayerVT2(Parser):
    """stingray::AnimationLayer"""

    states: list[AnimationStateVT2]
    default_state: int  # uint32

    def __init__(self, c: Cursor) -> None:
        self.states = Array(AnimationStateVT2, c)
        self.default_state = c.ReadU32()


class AnimationLayerDT(Parser):
    states: list[AnimationStateDT]
    default_state: int  # uint32

    def __init__(self, c: Cursor) -> None:
        self.states = Array(AnimationStateDT, c)
        self.default_state = c.ReadU32()
