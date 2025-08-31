"""LLM backends for command interpretation."""

from __future__ import annotations

import json
import os
from contextlib import suppress
from typing import TYPE_CHECKING

import requests
import yaml

from .interfaces import LLMBackend
from .persistence import LogEntry

if TYPE_CHECKING:  # pragma: no cover - used for type checking only
    from .language import LanguageManager
    from .world import World


class NoOpLLM(LLMBackend):
    """Backend that returns the command unchanged."""

    def interpret(self, command: str) -> str:
        return command

    def set_context(self, world, language, log) -> None:  # noqa: ARG002 - noop
        """Accept context but intentionally do nothing."""
        return None


class OllamaLLM(LLMBackend):
    """LLM backend using a local Ollama server."""

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 30,
        check_model: bool = False,
        min_confidence: float | None = None,
    ) -> None:
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        self.timeout = timeout
        if min_confidence is not None:
            self.min_confidence: float | None = float(min_confidence)
        else:
            env = os.getenv("OLLAMA_MIN_CONF")
            self.min_confidence = float(env) if env else None
        self.world: World | None = None
        self.language: LanguageManager | None = None
        self.log: list[LogEntry] | None = None
        if check_model:
            self._check_model_exists()

    def set_context(
        self,
        world: World,
        language: LanguageManager,
        log: list[LogEntry],
    ) -> None:
        """Provide world, language manager and log for prompt building."""

        self.world = world
        self.language = language
        self.log = log
        if self.world is not None:
            with suppress(Exception):  # pragma: no cover - defensive
                thresh = f", min_conf={self.min_confidence:g}" if isinstance(self.min_confidence, int | float) else ""
                self.world.debug(f"init model={self.model} base_url={self.base_url} timeout={self.timeout}s{thresh}")

    def interpret(self, command: str) -> str:  # pragma: no cover - network call
        if not self.world or not self.language:
            if self.world is not None:
                with suppress(Exception):
                    self.world.debug(f"passthrough (no context) input='{command}'")
            return command
        try:
            with suppress(Exception):
                self.world.debug(f"call input='{command}'")
            messages = self._build_messages(command)
            with suppress(Exception):  # pragma: no cover - best-effort
                system_preview = messages[0]["content"][:160].replace("\n", " ")
                self.world.debug(f"request system='{system_preview}…'")
            post = requests.post
            try:
                import inspect

                sig = inspect.signature(post)
                params = sig.parameters
                payload = {
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {"temperature": 0},
                }
                if "timeout" in params or any(p.kind == p.VAR_KEYWORD for p in params.values()):
                    response = post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                        timeout=self.timeout,
                    )
                elif len(params) >= 3:
                    response = post(
                        f"{self.base_url}/api/chat",
                        payload,
                        self.timeout,
                    )
                else:
                    response = post(  # noqa: S113 - fallback for minimal stubs
                        f"{self.base_url}/api/chat",
                        payload,
                    )
            except Exception:  # pragma: no cover - ultra-defensive
                response = post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {"temperature": 0},
                    },
                )
            data = response.json()
            content = data.get("message", {}).get("content", "")
            error = data.get("error")
            if error:
                self.world.debug(f"response error='{error.replace('\n', ' ')}'")
            self.world.debug(f"response content='{content[:160].replace('\n', ' ')}'")
            parsed = json.loads(content)
            conf_raw = parsed.get("confidence")
            conf: int | None = None
            if conf_raw is not None:
                try:
                    conf = int(conf_raw)
                except (TypeError, ValueError):
                    conf = None
            verb = parsed.get("verb")
            obj = parsed.get("object")
            add = parsed.get("additional")
            if verb and obj:
                parts = [str(verb), str(obj)]
                if isinstance(add, str) and add.strip():
                    parts.append(add.strip())
                result = " ".join(parts).strip()
                with suppress(Exception):
                    self.world.debug(f"mapped result='{result}' confidence={conf}")
                if conf == 2:
                    return result
                if conf == 1:
                    suggestion = self._format_suggestion(str(verb), str(obj), str(add) if add else None)
                    return f"__SUGGEST__ {suggestion or result}"
                if conf == 0:
                    return "__UNKNOWN__"
                return command
            result = verb or command
            with suppress(Exception):
                self.world.debug(f"mapped result='{result}'")
            return result
        except Exception as exc:
            with suppress(Exception):
                self.world.debug(f"error {type(exc).__name__}: {exc}; passthrough='{command}'")
            return command

    def _build_messages(self, command: str) -> list[dict[str, str]]:
        assert self.world and self.language
        world = self.world
        lm = self.language
        log = self.log or []
        allowed_verbs = sorted(lm.commands.keys())
        lang_code = getattr(lm, "language", "en")
        nouns: list[str] = []
        for item in world.items.values():
            nouns.extend(item.names)
        for npc in world.npcs.values():
            nouns.extend(npc.names)
        room = world.describe_room_header(lm.messages)
        visible = world.describe_visibility(lm.messages) or ""
        inventory_names = [world.items[item_id].names[0] for item_id in world.inventory if item_id in world.items]
        item_states = {world.items[item_id].names[0]: str(state) for item_id, state in world.item_states.items() if item_id in world.items}
        npc_states = {world.npcs[npc_id].names[0]: str(state) for npc_id, state in world.npc_states.items() if npc_id in world.npcs}
        recent_log = [entry.command for entry in log]
        context = (
            f"Room: {room}\n"
            f"Visible: {visible}\n"
            f"Inventory: {', '.join(inventory_names) if inventory_names else 'empty'}\n"
            f"Item states: {item_states}\n"
            f"NPC states: {npc_states}\n"
            f"Log: {recent_log}\n"
        )
        system_prompt = (
            "You map player input to game commands. A command consists of a <verb>, and optional 1 or 2 objects. "
            "<confidence> is a value between 0 and 2: 0=unsure, 1=quite sure, 2=totally sure.\n"
            f"Language: {lang_code}.\n"
            f"Allowed verbs: {', '.join(allowed_verbs)}\n"
            f"Known nouns: {', '.join(nouns)}\n"
            f"Guidance:\n{self._language_hints(lang_code)}\n"
            f"Context:\n{context}\n"
            "Respond with JSON "
            '{"confidence": <confidence>, "verb": "<verb>", "object": "<noun1>", "additional": "<noun2>"} and nothing else.\n'
        )
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": command},
        ]

    def _format_suggestion(self, verb: str, obj: str | None, add: str | None) -> str | None:
        """Render a localized suggestion using the first translation for ``verb``.

        Replaces `$a` with ``obj`` and `$b` with ``add`` if present. Falls back
        to a simple "verb obj [add]" string if translation is missing.
        """
        lm = self.language
        if not lm:
            return None
        val = lm.commands.get(verb)
        if not val:
            return None
        phrase = val[0] if isinstance(val, list) else val
        if not isinstance(phrase, str) or not phrase:
            return None
        a = (obj or "").strip()
        b = (add or "").strip()
        text = phrase.replace("$a", a).replace("$b", b)
        text = " ".join(text.split()).strip()
        return text

    def _language_hints(self, lang_code: str) -> str:
        """Return language-specific instructions from data/<lang>/llm.<lang>.yaml.

        Falls back to generic English-like guidance if the file is missing.
        """
        try:
            lm = self.language
            if lm is None or not hasattr(lm, "data_dir"):
                raise FileNotFoundError
            from pathlib import Path

            data_dir = lm.data_dir
            lang = lang_code or "en"
            path = Path(data_dir) / lang / f"llm.{lang}.yaml"
            with open(path, encoding="utf-8") as fh:
                cfg = yaml.safe_load(fh) or {}
            articles = cfg.get("ignore_articles") or []
            contractions = cfg.get("ignore_contractions") or []
            preps = cfg.get("second_object_preps") or []
            notes = cfg.get("notes") or []
            parts: list[str] = []
            if articles:
                parts.append("Ignore articles/determiners when matching nouns (" + ", ".join(articles) + ").")
            if contractions:
                parts.append("Ignore contractions when matching nouns (" + ", ".join(contractions) + ").")
            if preps:
                parts.append("Map these prepositions to the second object (additional): " + ", ".join(preps) + ".")
            if notes:
                parts.extend(str(n) for n in notes)
            if parts:
                return " ".join(parts)
        except Exception:  # pragma: no cover - fallback path
            with suppress(Exception):
                if self.world is not None:
                    self.world.debug("llm hints: fallback to generic guidance")
        return (
            "Ignore articles/determiners (the, a, an) and minor prepositions when matching nouns. "
            "Choose object strings from 'Known nouns'. Treat quoted phrases as one object."
        )

    def _check_model_exists(self) -> None:
        """Check if the configured model exists on the Ollama server.

        On failure, exit the program with a helpful message.
        """
        try:
            resp = requests.get(  # noqa: S113 - explicit timeout provided
                f"{self.base_url}/api/tags",
                timeout=self.timeout,
            )
            data = resp.json() if hasattr(resp, "json") else {}
            models = data.get("models") or []
            names = {str(m.get("name")) for m in models if isinstance(m, dict) and m.get("name")}
            target = self.model
            found = any(n == target or n.split(":", 1)[0] == target for n in names)
            if not found:
                msg = (
                    f"ERROR: LLM model '{self.model}' not found at {self.base_url}.\n"
                    f"Available: {', '.join(sorted(names)) or 'none'}\n"
                    "Install with 'ollama pull <model>' or set OLLAMA_MODEL."
                )
                raise SystemExit(msg)
        except SystemExit:
            raise
        except Exception as exc:  # pragma: no cover - environment-dependent
            raise SystemExit(f"ERROR: Could not verify LLM model '{self.model}' at {self.base_url}: {exc}") from exc


__all__ = ["NoOpLLM", "OllamaLLM"]
