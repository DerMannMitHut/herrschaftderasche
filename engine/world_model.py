"""Data models for world elements."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class LocationTag(Enum):
    INVENTORY = "INVENTORY"
    CURRENT_ROOM = "CURRENT_ROOM"


class StateTag(Enum):
    MET = "met"
    HELPED = "helped"


@dataclass
class Room:
    names: List[str] = field(default_factory=list)
    description: str = ""
    items: List[str] = field(default_factory=list)
    exits: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    occupants: List[str] = field(default_factory=list)

    def get(self, key: str, default: Any = None) -> Any:  # pragma: no cover - compat
        return getattr(self, key, default)

    def setdefault(self, key: str, default: Any) -> Any:  # pragma: no cover - compat
        value = getattr(self, key, None)
        if value is None:
            setattr(self, key, default)
            return default
        return value

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - compat
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:  # pragma: no cover - compat
        setattr(self, key, value)


@dataclass
class Item:
    names: List[str] = field(default_factory=list)
    description: str = ""
    state: Optional[str | StateTag] = None
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:  # pragma: no cover - compat
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - compat
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:  # pragma: no cover - compat
        setattr(self, key, value)


@dataclass
class Npc:
    names: List[str] = field(default_factory=list)
    state: Optional[str | StateTag] = None
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    meet: Dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:  # pragma: no cover - compat
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - compat
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:  # pragma: no cover - compat
        setattr(self, key, value)


@dataclass
class Action:
    trigger: Optional[str] = None
    item: Optional[str] = None
    target_item: Optional[str] = None
    target_npc: Optional[str] = None
    preconditions: Optional[list[Dict[str, Any]]] = None
    effect: Optional[list[Dict[str, Any]]] = None
    messages: Dict[str, str] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:  # pragma: no cover - compat
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:  # pragma: no cover - compat
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:  # pragma: no cover - compat
        setattr(self, key, value)


__all__ = [
    "LocationTag",
    "StateTag",
    "Room",
    "Item",
    "Npc",
    "Action",
]
