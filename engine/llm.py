"""LLM backends for command interpretation."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING, Dict, List

import requests

from .interfaces import LLMBackend
from .persistence import LogEntry

if TYPE_CHECKING:  # pragma: no cover - used for type checking only
    from .language import LanguageManager
    from .world import World


class NoOpLLM(LLMBackend):
    """Backend that returns the command unchanged."""

    def interpret(self, command: str) -> str:
        return command


class OllamaLLM(LLMBackend):
    """LLM backend using a local Ollama server."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 30,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.base_url = base_url or os.getenv(
            "OLLAMA_BASE_URL", "http://localhost:11434"
        )
        self.timeout = timeout
        self.world: World | None = None
        self.language: LanguageManager | None = None
        self.log: List[LogEntry] | None = None

    def set_context(
        self,
        world: World,
        language: LanguageManager,
        log: List[LogEntry],
    ) -> None:
        """Provide world, language manager and log for prompt building."""

        self.world = world
        self.language = language
        self.log = log

    def interpret(self, command: str) -> str:  # pragma: no cover - network call
        if not self.world or not self.language:
            return command
        messages = self._build_messages(command)
        try:
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages},
                timeout=self.timeout,
            )
            data = response.json()
            content = data.get("message", {}).get("content", "")
            parsed = json.loads(content)
            verb = parsed.get("verb")
            obj = parsed.get("object")
            if verb and obj:
                return f"{verb} {obj}".strip()
            return verb or command
        except Exception:
            return command

    def _build_messages(self, command: str) -> List[Dict[str, str]]:
        assert self.world and self.language
        world = self.world
        lm = self.language
        log = self.log or []
        allowed_verbs = sorted(lm.commands.keys())
        nouns: List[str] = []
        for item in world.items.values():
            nouns.extend(item.names)
        for npc in world.npcs.values():
            nouns.extend(npc.names)
        room = world.describe_room_header(lm.messages)
        visible = world.describe_visibility(lm.messages) or ""
        inventory_names = [
            world.items[item_id].names[0]
            for item_id in world.inventory
            if item_id in world.items
        ]
        item_states = {
            world.items[item_id].names[0]: str(state)
            for item_id, state in world.item_states.items()
            if item_id in world.items
        }
        npc_states = {
            world.npcs[npc_id].names[0]: str(state)
            for npc_id, state in world.npc_states.items()
            if npc_id in world.npcs
        }
        recent_log = [entry.command for entry in log]
        context = (
            f"Room: {room}\n"
            f"Visible: {visible}\n"
            f"Inventory: {', '.join(inventory_names) if inventory_names else 'empty'}\n"
            f"Item states: {item_states}\n"
            f"NPC states: {npc_states}\n"
            f"Log: {recent_log}"
        )
        system_prompt = (
            "You map player input to game commands.\n"
            f"Allowed verbs: {', '.join(allowed_verbs)}\n"
            f"Known nouns: {', '.join(nouns)}\n"
            f"Context:\n{context}\n"
            "Respond with JSON {\"verb\": \"<verb>\", \"object\": \"<noun>\"} and nothing else."
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
        ]


__all__ = ["NoOpLLM", "OllamaLLM"]
