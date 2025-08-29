"""Core game loop orchestrator."""

from __future__ import annotations

from pathlib import Path

import yaml

from engine import parser, world, integrity
from .interfaces import IOBackend, LLMBackend
from .io import ConsoleIO
from .llm import NoOpLLM

from .commands import CommandProcessor
from .language import LanguageManager
from .persistence import SaveManager


class Game:
    def __init__(
        self,
        world_data_path: str,
        language: str,
        io_backend: IOBackend | None = None,
        llm_backend: LLMBackend | None = None,
        debug: bool = False,
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
        self._language = str(save_data.get("language", language))
        generic_path = self.data_dir / "generic" / "world.yaml"
        lang_world_path = self.data_dir / self._language / "world.yaml"

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

        if save_data:
            self.world.load_state(self.save_manager.save_path)
            self.save_manager.cleanup()

        self.language_manager = LanguageManager(
            self.data_dir, self._language, self.io, debug=debug
        )
        self.command_processor = CommandProcessor(
            self.world,
            self.language_manager,
            self.save_manager,
            self._check_end,
            self._check_npc_event,
            self.stop,
            self._update_world,
            self.io,
        )
        self.running = True

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
            self.io.output(ending)
            self.running = False

    def _check_npc_event(self) -> None:
        for npc_id, npc in self.world.npcs.items():
            meet = npc.get("meet", {})
            loc = meet.get("location")
            text = meet.get("text")
            pre = meet.get("preconditions")
            if loc == self.world.current and self.world.npc_state(npc_id) != "met":
                if pre and not self.world.check_preconditions(pre):
                    continue
                if text:
                    self.io.output(text)
                self.world.meet_npc(npc_id)

    def run(self) -> None:
        if self._show_intro and self.world.intro:
            self.io.output(self.world.intro)
        self.io.output(self.world.describe_current(self.language_manager.messages))
        self._check_npc_event()
        self._check_end()
        try:
            while self.running:
                raw = self.io.get_input()
                raw = self.llm.interpret(raw)
                raw = parser.parse(raw)
                self.command_processor.execute(raw)
        except (EOFError, KeyboardInterrupt):
            self.io.output(self.language_manager.messages["farewell"])
        finally:
            self.save_manager.save(self.world, self.language_manager.language)


def run(
    world_data_path: str,
    language: str = "en",
    io_backend: IOBackend | None = None,
    llm_backend: LLMBackend | None = None,
    debug: bool = False,
) -> None:
    Game(
        world_data_path,
        language,
        io_backend=io_backend,
        llm_backend=llm_backend,
        debug=debug,
    ).run()

