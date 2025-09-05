"""Data models for world elements."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LocationTag(Enum):
    INVENTORY = "INVENTORY"
    CURRENT_ROOM = "CURRENT_ROOM"


class StateTag(Enum):
    MET = "met"
    HELPED = "helped"


class CommandCategory(Enum):
    SYSTEM = "system"
    BASICS = "basics"
    ACTIONS = "actions"


class Room(BaseModel):
    names: list[str]
    description: str
    items: list[str] = Field(default_factory=list)  # noqa
    exits: dict[str, dict[str, Any]] = Field(default_factory=dict)  # noqa
    occupants: list[str] = Field(default_factory=list)  # noqa

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
    names: list[str]
    description: str | None = None
    state: str | StateTag | None = None
    states: dict[str, dict[str, Any]] = Field(default_factory=dict)  # noqa

    model_config = ConfigDict(extra="forbid")

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)


class DialogOption(BaseModel):
    id: str
    prompt: str | None = None
    next: str | None = None
    effect: dict[str, Any] | None = None


class DialogNode(BaseModel):
    text: str | None = None
    options: list[DialogOption] = Field(default_factory=list)
    effect: dict[str, Any] | None = None


class Npc(BaseModel):
    names: list[str]
    state: str | StateTag | None = None
    states: dict[str, dict[str, Any]] = Field(default_factory=dict)  # noqa
    meet: dict[str, Any] = Field(default_factory=dict)  # noqa
    dialog: dict[str, DialogNode] = Field(default_factory=dict)  # noqa

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
    preconditions: dict[str, Any] | None = None
    effect: dict[str, Any] | None = None
    duration: int | None = None
    messages: dict[str, str] = Field(default_factory=dict)  # noqa

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
    "CommandCategory",
    "Room",
    "Item",
    "DialogOption",
    "DialogNode",
    "Npc",
    "Action",
]
