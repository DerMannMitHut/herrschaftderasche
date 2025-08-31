"""Data models for world elements."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field


class LocationTag(Enum):
    INVENTORY = "INVENTORY"
    CURRENT_ROOM = "CURRENT_ROOM"


class StateTag(Enum):
    MET = "met"
    HELPED = "helped"


class Room(BaseModel):
    names: List[str]
    description: str
    items: List[str] = Field(default_factory=list) # noqa
    exits: Dict[str, Dict[str, Any]] = Field(default_factory=dict) # noqa
    occupants: List[str] = Field(default_factory=list) # noqa

    model_config = ConfigDict(extra="forbid")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def setdefault(self, key: str, default: Any) -> Any:
        value = getattr(self, key, None)
        if value is None:
            setattr(self, key, default)
            return default
        return value

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class Item(BaseModel):
    names: List[str]
    description: str | None = None
    state: str | StateTag | None = None
    states: Dict[str, Dict[str, Any]] = Field(default_factory=dict) # noqa

    model_config = ConfigDict(extra="forbid")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class Npc(BaseModel):
    names: List[str]
    state: str | StateTag | None = None
    states: Dict[str, Dict[str, Any]] = Field(default_factory=dict) # noqa
    meet: Dict[str, Any] = Field(default_factory=dict) # noqa

    model_config = ConfigDict(extra="forbid")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class Action(BaseModel):
    trigger: str
    item: str
    target_item: str | None = None
    target_npc: str | None = None
    preconditions: Dict[str, Any] | None = None
    effect: Dict[str, Any] | None = None
    messages: Dict[str, str] = Field(default_factory=dict) # noqa

    model_config = ConfigDict(extra="forbid")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


__all__ = [
    "LocationTag",
    "StateTag",
    "Room",
    "Item",
    "Npc",
    "Action",
]
