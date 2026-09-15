"""stingray::AnimationStateMachineResource"""

from mathutils import Vector

from ..deserializing import Cursor
from ..murmur.rainbow_table import IDString32
from .animation_layer import AnimationLayerDT, AnimationLayerVT1, AnimationLayerVT2
from .base import Parser
from .blend_set import BlendSet
from .generic_structures import Array
from .ragdoll import Ragdoll
from .resource_header import DTHeader


class AnimationStateMachineResourceVT1(Parser):
    """stingray::AnimationStateMachineResource"""

    layers: list[AnimationLayerVT1]
    event_names: list[IDString32]
    variable_names: list[IDString32]
    variables: list[float]  # all floats?

    unk1_count: int
    unk1_arr: list[list[float]]

    constraint_targets: list[IDString32]
    constraint_target_positions: list[Vector]  # vec3
    constraints: bytes
    ragdolls: list[Ragdoll]

    def __init__(self, c: Cursor) -> None:
        self.layers = Array(AnimationLayerVT1, c)
        self.event_names = c.ReadIDString32Array()
        self.variable_names = c.ReadIDString32Array()
        self.variables = c.ReadF32Array()

        self.unk1_count = c.ReadU32()
        self.unk1_arr = [c.ReadF32Array() for _ in range(self.unk1_count)]

        self.constraint_targets = c.ReadIDString32Array()
        self.constraint_target_positions = c.ReadVec3Array()
        self.constraints = c.ReadByteArray()
        self.ragdolls = Array(Ragdoll, c)

        if c.more():
            raise ValueError(
                f"Finished deserializing at offset {c.tell()}, but file length is {len(c)}"
            )


class UnkStructOf7(Parser):
    unk1: int
    unk2: int
    unk3: int
    unk4: int
    unk5: int
    unk6: int
    unk7: float  # usually 0xBF800000 which is -1.0

    def __init__(self, c: Cursor) -> None:
        self.unk1 = c.ReadU32()
        self.unk2 = c.ReadU32()
        self.unk3 = c.ReadU32()
        self.unk4 = c.ReadU32()
        self.unk5 = c.ReadU32()
        self.unk6 = c.ReadU32()
        self.unk7 = c.ReadF32()


class AnimationStateMachineResourceVT2(Parser):
    """
    stingray::AnimationStateMachineResource

    stingray::AnimationStateMachineResource::serialize
    """

    layers: list[AnimationLayerVT2]
    event_names: list[IDString32]
    variable_names: list[IDString32]
    variables: list[float]

    unk1_arr: list[float]  # 2float

    blend_sets: list[BlendSet]
    constraint_targets: list[IDString32]
    constraint_target_positions: list[Vector]  # list[Vec3]
    constraints: bytes
    ragdolls: list[Ragdoll]

    unk3_arr: list[UnkStructOf7]
    unk4: float
    # ResourceName: IDString64

    def __init__(self, c: Cursor) -> None:
        self.layers = Array(AnimationLayerVT2, c)
        self.event_names = c.ReadIDString32Array()
        self.variable_names = c.ReadIDString32Array()
        self.variables = c.ReadF32Array()
        self.unk1_arr = []
        count = c.ReadU32()
        for _ in range(count):
            self.unk1_arr.append(c.ReadF32())
            self.unk1_arr.append(c.ReadF32())

        self.blend_sets = Array(BlendSet, c)
        self.constraint_targets = c.ReadIDString32Array()
        self.constraint_target_positions = c.ReadVec3Array()
        self.constraints = c.ReadByteArray()
        self.ragdolls = Array(Ragdoll, c)
        self.unk3_arr = Array(UnkStructOf7, c)
        self.unk4 = c.ReadF32()

        if c.more():
            raise ValueError(
                f"Finished deserializing at offset {c.tell()}, but file length is {len(c)}"
            )


class AnimationStateMachineResourceDT(Parser):
    """Slight changes in DT"""

    layers: list[AnimationLayerDT]
    event_names: list[IDString32]
    variable_names: list[IDString32]
    variables: list[float]

    unk2: list[float]  # tuple[float, float]?

    blend_sets: list[BlendSet]
    constraint_targets: list[IDString32]
    constraint_target_positions: list[Vector]  # list[Vec3]
    constraints: bytes
    ragdolls: list[Ragdoll]

    unk3_arr: list[UnkStructOf7]
    unk4: float
    # ResourceName: IDString64

    def __init__(self, c: Cursor) -> None:
        _header = DTHeader(c)

        self.layers = Array(AnimationLayerDT, c)
        self.event_names = c.ReadIDString32Array()
        self.variable_names = c.ReadIDString32Array()
        self.variables = c.ReadF32Array()
        self.unk2 = []
        count = c.ReadU32()
        for _ in range(count):
            self.unk2.append(c.ReadF32())
            self.unk2.append(c.ReadF32())
        self.blend_sets = Array(BlendSet, c)
        self.constraint_targets = c.ReadIDString32Array()
        self.constraint_target_positions = c.ReadVec3Array()
        self.constraints = c.ReadByteArray()
        self.ragdolls = Array(Ragdoll, c)
        self.unk3_arr = Array(UnkStructOf7, c)
        self.unk4 = c.ReadF32()

        if c.more():
            raise ValueError(
                f"Finished deserializing at offset {c.tell()}, but file length is {len(c)}"
            )
