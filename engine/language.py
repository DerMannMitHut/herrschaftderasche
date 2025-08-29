"""Handle translations and language switching."""

from __future__ import annotations

from pathlib import Path

from . import i18n, world
from .persistence import SaveManager


class LanguageManager:
    """Manage messages, command translations and language switches."""

    def __init__(self, data_dir: Path, language: str, debug: bool = False):
        self.data_dir = data_dir
        self.debug = debug
        self.language = language
        self.messages = i18n.load_messages(language)
        self.commands = i18n.load_commands(language)
        self.command_info = i18n.load_command_info()

    def switch(self, language: str, current_world: world.World, save_manager: SaveManager) -> world.World:
        """Switch the game to a different language.

        Returns the reloaded world instance.  Raises ``ValueError`` if the
        language data cannot be found.
        """

        try:
            messages = i18n.load_messages(language)
            commands = i18n.load_commands(language)
            generic_path = self.data_dir / "generic" / "world.yaml"
            world_path = self.data_dir / language / "world.yaml"
            new_world = world.World.from_files(generic_path, world_path, debug=self.debug)
        except FileNotFoundError as exc:  # pragma: no cover - defensive programming
            raise ValueError("Unknown language") from exc

        save_manager.save(current_world, self.language)
        new_world.load_state(save_manager.save_path)
        save_manager.cleanup()

        self.language = language
        self.messages = messages
        self.commands = commands
        return new_world


__all__ = ["LanguageManager"]

