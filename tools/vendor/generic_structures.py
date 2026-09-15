"""Generic data structures."""

from collections.abc import Callable
from typing import TypeVar

from ..deserializing import Cursor
from .base import Parser

T = TypeVar("T", bound=Parser)


def Array(data_type: Callable[[Cursor], T], c: Cursor) -> list[T]:  # noqa: N802
    """Generic Stingray-style array. Read a u32 `count` then read that many of type `data_type`."""  # noqa: D401
    count = c.ReadU32()
    result = [data_type(c) for _ in range(count)]
    return result
