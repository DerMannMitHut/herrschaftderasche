"""Core game loop orchestrator."""

from __future__ import annotations

from pathlib import Path

import yaml

from engine import integrity, parser, world

from .commands import CommandProcessor
from .interfaces import IOBackend, LLMBackend
from .io import ConsoleIO
from .language import LanguageManager
from .llm import SUGGEST_PREFIX, UNKNOWN_TOKEN, NoOpLLM
from .persistence import SaveManager
from .world_model import StateTag


class Game:
    def __init__(
        self,
        world_data_path: str,
        language: str,
        io_backend: IOBackend | None = None,
        llm_backend: LLMBackend | None = None,
        debug: bool = False,
        *,
        force_language: bool = False,
    ) -> None:
        data_path = Path(world_data_path)
        self.data_dir = data_path.parent.parent
        self.debug = debug
        self.io = io_backend or ConsoleIO()
        self.llm = llm_backend or NoOpLLM()
        self.save_manager = SaveManager(self.data_dir)

        try:
            save_data = self.save_manager.load()
        except (FileNotFoundError, yaml.YAMLError) as exc:
            self.io.output(f"ERROR: Failed to load save file: {exc}")
            raise SystemExit from exc

        self._show_intro = not save_data
        if save_data and not force_language:
            self._language = str(save_data.get("language", language))
        else:
            self._language = language
        generic_path = self.data_dir / "generic" / "world.yaml"
        lang_world_path = self.data_dir / self._language / f"world.{self._language}.yaml"

        try:
            self.world = world.World.from_files(generic_path, lang_world_path, debug=debug)
        except FileNotFoundError as exc:
            self.io.output(f"ERROR: Missing world file: {exc}")
            raise SystemExit from exc
        except yaml.YAMLError as exc:
            self.io.output(f"ERROR: Invalid world file: {exc}")
            raise SystemExit from exc

        try:
            warnings = integrity.check_translations(self._language, self.data_dir)
        except (FileNotFoundError, yaml.YAMLError) as exc:
            self.io.output(f"ERROR: Failed to load translations: {exc}")
            raise SystemExit from exc
        for msg in warnings:
            self.io.output(f"WARNING: {msg}")

        errors = integrity.validate_world_structure(self.world)
        if save_data:
            errors.extend(integrity.validate_save(save_data, self.world))

        if errors:
            for msg in errors:
                self.io.output(f"ERROR: {msg}")
            raise SystemExit("Integrity check failed")

        log_data = save_data.get("log") if save_data else None
        if save_data:
            self.world.load_state(self.save_manager.save_path)
            self.save_manager.cleanup()

        self.language_manager = LanguageManager(self.data_dir, self._language, self.io, debug=debug)
        self.command_processor = CommandProcessor(
            self.world,
            self.language_manager,
            self.save_manager,
            self._check_end,
            self._check_npc_event,
            self.stop,
            self._update_world,
            self.io,
            log=log_data,
        )
        self.llm.set_context(self.world, self.language_manager, self.command_processor.log)
        self.running = True
        inv = list(self.world.inventory)
        self.world.debug(f"game_init language {self._language} current {self.world.current} inventory {inv}")

    @property
    def language(self) -> str:
        return self.language_manager.language

    def _update_world(self, new_world: world.World) -> None:
        self.world = new_world

    def stop(self) -> None:
        self.running = False

    def _check_end(self) -> None:
        ending = self.world.check_endings()
        if ending:
            self.io.output("")
            self.io.output(ending)
            self.running = False
            self.world.debug(f"ending_reached text '{ending[:40] + ('...' if len(ending) > 40 else '')}'")

    def _check_npc_event(self) -> None:
        room = self.world.rooms[self.world.current]
        for npc_id in list(room.occupants):
            npc = self.world.npcs.get(npc_id)
            if not npc:
                continue
            meet = npc.get("meet", {})
            pre = meet.get("preconditions")
            state = self.world.npc_state(npc_id)
            if pre and not self.world.check_preconditions(pre):
                continue
            if state == "unknown":
                text = meet.get("text")
                if text:
                    self.io.output(text)
                self.world.meet_npc(npc_id)
            else:
                state_key = state.value if isinstance(state, StateTag) else state
                text = npc.get("states", {}).get(state_key, {}).get("text")
                if text:
                    self.io.output(text)

    def run(self) -> None:
        if self._show_intro and self.world.intro:
            self.io.output(self.world.intro)
        # Show current time at game start
        ts = self.world.format_time()
        msg = self.language_manager.messages.get("time", "{time}").format(time=ts)
        self.io.output(msg)
        header = self.world.describe_room_header(self.language_manager.messages)
        self.io.output(header)
        event_outs: list[str] = []
        original_output = self.io.output
        try:
            self.io.output = lambda text: event_outs.append(text)
            self._check_npc_event()
        finally:
            self.io.output = original_output
        if event_outs:
            self.io.output("")
            for line in event_outs:
                self.io.output(line)
        visible = self.world.describe_visibility(self.language_manager.messages)
        if visible:
            self.io.output("")
            self.io.output(visible)
        if self.command_processor._dialog_npc:
            self.io.output("")
            self.command_processor.list_dialog_options()
        self._check_end()
        try:
            while self.running:
                user_input = self.io.get_input()
                if self.debug:
                    self.world.debug(f"input={user_input}")
                normalized = parser.parse(user_input)
                if self.command_processor.execute(normalized):
                    continue
                mapped = self.llm.interpret(user_input)
                if mapped == UNKNOWN_TOKEN:
                    self.io.output(self.language_manager.messages["unknown_command"])
                    continue
                if mapped.startswith(f"{SUGGEST_PREFIX} "):
                    suggestion = mapped[len(SUGGEST_PREFIX) + 1 :].strip()
                    msg_tpl = self.language_manager.messages.get("llm_suggest", "Try: {command}")
                    self.io.output(msg_tpl.format(command=suggestion))
                    continue
                mapped_norm = parser.parse(mapped)
                if not self.command_processor.execute(mapped_norm):
                    self.io.output(self.language_manager.messages["unknown_command"])
        except (EOFError, KeyboardInterrupt):
            self.io.output(self.language_manager.messages["farewell"])
        finally:
            self.save_manager.save(
                self.world,
                self.language_manager.language,
                self.command_processor.log,
            )


def run(
    world_data_path: str,
    language: str = "en",
    io_backend: IOBackend | None = None,
    llm_backend: LLMBackend | None = None,
    debug: bool = False,
    *,
    force_language: bool = False,
) -> None:
    Game(
        world_data_path,
        language,
        io_backend=io_backend,
        llm_backend=llm_backend,
        debug=debug,
        force_language=force_language,
    ).run()
