"""stingray::AnimationState"""

from enum import Enum

from mathutils import Vector

from ..deserializing import Cursor
from ..murmur.rainbow_table import IDString32, IDString64
from .animation_blend_settings import AnimationBlendSettingsVT2
from .animation_blender import BlendType, BoneMode
from .animation_transition import AnimationTransition, AnimationTransitionSwitch
from .base import Parser
from .generic_structures import Array


class MarkerType(Enum):
    """stingray::AnimationState::Marker::Type"""

    DISABLE_COLLISION = 0
    DISABLE_RAYCASTING = 1
    DISABLE_RESPONSE = 2
    DISABLE_SCENE_QUERIES = 3
    SWEEP = 4
    TRIGGER = 5
    N_SHAPE_FLAGS = 6


class Marker(Parser):
    """stingray::AnimationState::Marker"""

    time: float
    name: IDString32
    type: MarkerType

    def __init__(self, c: Cursor) -> None:
        self.time = c.ReadF32()
        self.name = c.ReadIDString32()
        self.type = MarkerType(c.ReadU32())


class AnimationStateType(Enum):
    """stingray::AnimationState::StateType"""

    REGULAR_STATE = 0
    EMPTY_STATE = 1
    MIX_STATE = 2
    TIME_STATE = 3
    RAGDOLL_STATE = 4


class RandomizationType(Enum):
    """stingray::AnimationState::RandomizationType"""

    RANDOMIZE_ON_ENTRY = 0
    RANDOMIZE_EVERY_LOOP = 1
    RANDOMIZE_EVERY_LOOP_DONT_REPEAT = 2


class ExitEvent(Parser):
    """stingray::AnimationState::ExitEvent"""

    name: IDString32
    blend_time: float

    def __init__(self, c: Cursor) -> None:
        self.name = c.ReadIDString32()
        self.blend_time = c.ReadF32()


class UnkStruct1(Parser):
    unk1: IDString32
    unk2: int
    unk3: float
    unk4: int
    unk5: IDString32

    def __init__(self, c: Cursor) -> None:
        self.unk1 = c.ReadIDString32()
        self.unk2 = c.ReadU32()
        self.unk3 = c.ReadF32()
        self.unk4 = c.ReadU32()
        self.unk5 = c.ReadIDString32()


class UnkStruct2(Parser):
    unk1: int
    unk2: int
    unk3: int

    def __init__(self, c: Cursor) -> None:
        self.unk1 = c.ReadU32()
        self.unk2 = c.ReadU32()
        self.unk3 = c.ReadU32()


class AnimationStateVT1(Parser):
    """stingray::AnimationState"""

    name: IDString64
    state_type: AnimationStateType
    animations: list[IDString64]
    probabilities: list[float]
    randomization_type: RandomizationType
    loop_animation: bool
    blend_type: BlendType

    unk1: list[UnkStruct1]
    unk2: list[UnkStruct2]
    unk3: int
    unk4: int

    bytecode: list[int]  # some floats, some ints?
    weights: list[int]

    unk5: int
    unk6: int

    bone_anim_mode: BoneMode
    blend_set: int
    constraints: list[int]

    unk7: int
    muted_layers_mask: int
    ragdoll: int

    def __init__(self, c: Cursor) -> None:
        self.name = c.ReadIDString64()
        self.state_type = AnimationStateType(c.ReadU32())
        self.animations = c.ReadIDString64Array()
        self.probabilities = c.ReadF32Array()
        self.randomization_type = RandomizationType(c.ReadU32())
        self.loop_animation = c.ReadBool()
        self.blend_type = BlendType(c.ReadU32())

        self.unk1 = Array(UnkStruct1, c)
        self.unk2 = Array(UnkStruct2, c)
        self.unk3 = c.ReadU32()
        self.unk4 = c.ReadU32()

        self.bytecode = c.ReadU32Array()
        self.weights = c.ReadU32Array()

        self.unk5 = c.ReadU32()
        self.unk6 = c.ReadU32()

        self.bone_anim_mode = BoneMode(c.ReadU32())
        self.blend_set = c.ReadU32()
        self.constraints = c.ReadU32Array()

        self.unk7 = c.ReadU32()

        self.muted_layers_mask = c.ReadU32()
        self.ragdoll = c.ReadU32()


class AnimationStateVT2(Parser):
    """
    stingray::AnimationState

    stingray::AnimationState::serialize
    """

    name: IDString64

    name2: IDString64  # ?
    name3: IDString64  # ?

    state_type: AnimationStateType
    animations: list[IDString64]
    probabilities: list[float]
    randomization_type: RandomizationType
    loop_animation: bool
    blend_type: BlendType
    transitions: list[AnimationTransition]
    blend_settings: list[AnimationBlendSettingsVT2]
    switches: list[AnimationTransitionSwitch]
    timeline: list[Marker]

    unk1: int
    unk2_arr: list[Vector]

    exit_event: ExitEvent
    bytecode: list[int]
    weights: list[int]

    unk3: int

    speed: float  # float?

    unk4: int

    # RootDriving: RootMode
    # BoneAnimMode: BoneMode
    blend_set: int
    contraints: list[int]

    unk6: int

    # TimeVariable: int
    muted_layers_mask: int
    ragdoll: int

    def __init__(self, c: Cursor) -> None:
        self.name = c.ReadIDString64()
        self.name2 = c.ReadIDString64()
        self.name3 = c.ReadIDString64()
        self.state_type = AnimationStateType(c.ReadU32())
        self.animations = c.ReadIDString64Array()
        self.probabilities = c.ReadF32Array()
        self.randomization_type = RandomizationType(c.ReadU32())
        self.loop_animation = c.ReadBool()
        self.blend_type = BlendType(c.ReadU32())
        self.transitions = Array(AnimationTransition, c)
        self.blend_settings = Array(AnimationBlendSettingsVT2, c)
        self.switches = Array(AnimationTransitionSwitch, c)
        self.timeline = Array(Marker, c)
        self.unk1 = c.ReadU32()
        self.unk2_arr = c.ReadVec3Array()
        self.exit_event = ExitEvent(c)
        self.bytecode = c.ReadU32Array()
        self.weights = c.ReadU32Array()
        self.unk3 = c.ReadU32()
        self.speed = c.ReadF32()
        self.unk4 = c.ReadU32()
        self.blend_set = c.ReadU32()
        self.contraints = c.ReadU32Array()
        self.unk6 = c.ReadU32()
        self.muted_layers_mask = c.ReadU32()
        self.ragdoll = c.ReadU32()


class AnimationStateDT(Parser):
    name: IDString64
    name2: IDString64  # ?
    name3: IDString64  # ?
    state_type: AnimationStateType
    animations: list[IDString64]
    probabilities: list[float]
    randomization_type: RandomizationType
    loop_animation: bool
    blend_type: BlendType
    transitions: list[AnimationTransition]
    blend_settings: list[AnimationBlendSettingsVT2]
    switches: list[AnimationTransitionSwitch]
    unk1: int
    unk2: int
    timeline: list[Marker]
    unk3: int
    unk4: int
    unk5: list[int]
    unk6: list[int]
    unk7: int
    unk8: int
    unk9: int
    unk10: int
    unk11: list[int]
    unk12: int
    unk13: int
    unk14: int

    def __init__(self, c: Cursor) -> None:
        self.name = c.ReadIDString64()
        self.name2 = c.ReadIDString64()
        self.name3 = c.ReadIDString64()
        self.state_type = AnimationStateType(c.ReadU32())
        self.animations = c.ReadIDString64Array()
        self.probabilities = c.ReadF32Array()
        self.randomization_type = RandomizationType(c.ReadU32())
        self.loop_animation = c.ReadBool()
        self.blend_type = BlendType(c.ReadU32())
        self.transitions = Array(AnimationTransition, c)
        self.blend_settings = Array(AnimationBlendSettingsVT2, c)
        self.switches = Array(AnimationTransitionSwitch, c)
        self.unk1 = c.ReadU32()
        self.unk2 = c.ReadU32()
        self.timeline = Array(Marker, c)
        self.unk3 = c.ReadU32()
        self.unk4 = c.ReadU32()
        self.unk5 = c.ReadU32Array()
        self.unk6 = c.ReadU32Array()
        self.unk7 = c.ReadU32()
        self.unk8 = c.ReadU32()
        self.unk9 = c.ReadU32()
        self.unk10 = c.ReadU32()
        self.unk11 = c.ReadU32Array()
        self.unk12 = c.ReadU32()
        self.unk13 = c.ReadU32()
        self.unk14 = c.ReadU32()
