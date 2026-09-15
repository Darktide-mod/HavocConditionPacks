"""Import compiled animation state machines (.state_machine)"""

from typing import Literal

from bpy.types import Context, Operator

from .. import resource_manager as rm
from ..import_base import ImportBaseV2
from ..murmur.rainbow_table import IDString32, IDString64
from ..stingray.animation_state_machine_resource import (
    AnimationStateMachineResourceDT,
    AnimationStateMachineResourceVT1,
    AnimationStateMachineResourceVT2,
)


class AnimationStateMachineImporterVT1(ImportBaseV2):
    file_type = rm.StingrayFileType.state_machine
    game = rm.StingrayGame.VT1
    resource: AnimationStateMachineResourceVT1

    def parse(self) -> AnimationStateMachineResourceVT1:  # noqa: D102
        return AnimationStateMachineResourceVT1(self.cursor)

    def load(self, slot_name: IDString32 | None = None) -> set[Literal["FINISHED", "CANCELLED"]]:  # noqa: D102
        set_animations_list(self.operator, self.context, self.resource)
        return {"FINISHED"}

    @classmethod
    def try_parse(
        cls,
        operator: Operator,
        context: Context,
        name: str | IDString64 | None = None,
        path: str | None = None,
    ) -> AnimationStateMachineResourceVT1 | None:
        """Safely try to parse the resource. Return None if it fails."""
        try:
            importer = cls(operator, context, name, path)
        except Exception as e:
            operator.report(
                {"WARNING"}, f"Could not import VT1 animation state machine resource: {e}"
            )
            return None
        else:
            return importer.resource


class AnimationStateMachineImporterVT2(ImportBaseV2):
    file_type = rm.StingrayFileType.state_machine
    game = rm.StingrayGame.VT2
    resource: AnimationStateMachineResourceVT2

    def parse(self) -> AnimationStateMachineResourceVT2:  # noqa: D102
        return AnimationStateMachineResourceVT2(self.cursor)

    def load(self, slot_name: IDString32 | None = None) -> set[Literal["FINISHED", "CANCELLED"]]:  # noqa: D102
        set_animations_list(self.operator, self.context, self.resource)
        return {"FINISHED"}

    @classmethod
    def try_parse(
        cls,
        operator: Operator,
        context: Context,
        name: str | IDString64 | None = None,
        path: str | None = None,
    ) -> AnimationStateMachineResourceVT2 | None:
        """Safely try to parse the resource. Return None if it fails."""
        try:
            importer = cls(operator, context, name, path)
        except Exception as e:
            operator.report(
                {"WARNING"}, f"Could not import VT2 animation state machine resource: {e}"
            )
            return None
        else:
            return importer.resource


class AnimationStateMachineImporterDT(ImportBaseV2):
    file_type = rm.StingrayFileType.state_machine
    game = rm.StingrayGame.DT
    resource: AnimationStateMachineResourceDT

    def parse(self) -> AnimationStateMachineResourceDT:  # noqa: D102
        return AnimationStateMachineResourceDT(self.cursor)

    def load(self, slot_name: IDString32 | None = None) -> set[Literal["FINISHED", "CANCELLED"]]:  # noqa: D102
        set_animations_list(self.operator, self.context, self.resource)
        return {"FINISHED"}

    @classmethod
    def try_parse(
        cls,
        operator: Operator,
        context: Context,
        name: str | IDString64 | None = None,
        path: str | None = None,
    ) -> AnimationStateMachineResourceDT | None:
        """Safely try to parse the resource. Return None if it fails."""
        try:
            importer = cls(operator, context, name, path)
        except Exception as e:
            operator.report(
                {"WARNING"}, f"Could not import DT animation state machine resource: {e}"
            )
            return None
        else:
            return importer.resource


def dump_animation_list(
    resource: AnimationStateMachineResourceVT1 | AnimationStateMachineResourceVT2,
) -> list[IDString64]:
    """Return a list of animations this state machine references."""
    result: set[IDString64] = set()
    for layer in resource.layers:
        for state in layer.states:
            for animation in state.animations:
                result.add(animation)
    return list(result)


def set_animations_list(
    operator: Operator,
    context: Context,
    resource: AnimationStateMachineResourceVT1 | AnimationStateMachineResourceVT2,
) -> None:
    """Set the animations list of the active object."""
    # get current object
    obj = context.active_object
    if obj is None:
        raise RuntimeError("No active object")

    # get animations
    animations_list = dump_animation_list(resource)

    # clear anim list
    obj.anim_list.clear()

    # add anims to RNA
    anims = [(anim.lookup(), str(anim)) for anim in animations_list]
    # sort by lookup str
    anims = sorted(anims, key=lambda x: x[0])
    for anim in anims:
        new_item = obj.anim_list.add()
        new_item.name = anim[0]
        new_item.idstring64 = anim[1]

    operator.report({"INFO"}, f"Applied {len(anims)} animations to {obj.name}")
