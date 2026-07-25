"""Builds the CTk root and starts the app."""
from __future__ import annotations

import customtkinter as ctk

from .ui.main_window import MainWindow


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("green")
    window = MainWindow()
    window.mainloop()


if __name__ == "__main__":
    main()
