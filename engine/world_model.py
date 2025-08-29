from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Item:
    names: List[str]
    description: Optional[str] = None
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    state: Optional[str] = None


@dataclass
class Room:
    names: List[str]
    description: str
    exits: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    items: List[str] = field(default_factory=list)


@dataclass
class Npc:
    names: List[str]
    states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    state: Optional[str] = None
    meet: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Action:
    trigger: str
    item: Optional[str] = None
    target_item: Optional[str] = None
    target_npc: Optional[str] = None
    preconditions: Optional[Dict[str, Any]] = None
    effect: Dict[str, Any] = field(default_factory=dict)
    messages: Dict[str, str] = field(default_factory=dict)
