"""stingray::Ragdoll"""

from ..deserializing import Cursor
from ..murmur.rainbow_table import IDString32
from .base import Parser


class Ragdoll(Parser):
    """stingray::Ragdoll"""

    dynamic_actors: list[IDString32]
    keyframed_actors: list[IDString32]

    def __init__(self, c: Cursor) -> None:
        self.dynamic_actors = c.ReadIDString32Array()
        self.keyframed_actors = c.ReadIDString32Array()
