"""Save/load named parameter presets as JSON in the platformdirs config dir."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

import customtkinter as ctk

from ascii_video.utils.config_paths import presets_dir


def save_preset(name: str, data: dict) -> Path:
    path = presets_dir() / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return path


def load_preset(name: str) -> dict:
    path = presets_dir() / f"{name}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_presets() -> list[str]:
    return sorted(p.stem for p in presets_dir().glob("*.json"))


def delete_preset(name: str) -> None:
    path = presets_dir() / f"{name}.json"
    if path.exists():
        path.unlink()


_NO_PRESETS = "(no presets saved)"


class PresetBar(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_save: Callable[[str], None],
        on_load: Callable[[str], None],
        on_delete: Callable[[str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_save = on_save
        self.on_load = on_load
        self.on_delete = on_delete

        ctk.CTkLabel(self, text="Presets", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(0, 4))
        self.preset_var = ctk.StringVar(value="")
        self.menu = ctk.CTkOptionMenu(self, values=[_NO_PRESETS], variable=self.preset_var)
        self.menu.pack(fill="x", pady=2)

        ctk.CTkButton(self, text="Save As...", command=self._save_as).pack(fill="x", pady=2)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", pady=2)
        ctk.CTkButton(btn_row, text="Load", command=self._load).pack(side="left", expand=True, fill="x", padx=(0, 4))
        ctk.CTkButton(btn_row, text="Delete", command=self._delete).pack(side="left", expand=True, fill="x", padx=(4, 0))

        self.refresh()

    def refresh(self) -> None:
        names = list_presets()
        self.menu.configure(values=names or [_NO_PRESETS])
        if names:
            if self.preset_var.get() not in names:
                self.preset_var.set(names[0])
        else:
            self.preset_var.set(_NO_PRESETS)

    def _save_as(self) -> None:
        dialog = ctk.CTkInputDialog(text="Preset name:", title="Save preset")
        name = dialog.get_input()
        if name:
            self.on_save(name)
            self.refresh()
            self.preset_var.set(name)

    def _load(self) -> None:
        name = self.preset_var.get()
        if name and name != _NO_PRESETS:
            self.on_load(name)

    def _delete(self) -> None:
        name = self.preset_var.get()
        if name and name != _NO_PRESETS:
            self.on_delete(name)
            self.refresh()
