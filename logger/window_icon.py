"""Shared application icon for the device selector and measurement viewer."""
import sys
import tkinter as tk
from pathlib import Path

ASSET_DIRECTORY = Path(__file__).resolve().parents[1] / "assets"


def set_window_icon(window):
    if sys.platform == "win32":
        icon = str(ASSET_DIRECTORY / "monitoring-eye.ico")
        window.iconbitmap(bitmap=icon, default=icon)
        return
    window._application_icon = tk.PhotoImage(master=window, file=str(ASSET_DIRECTORY / "monitoring-eye.png"))
    window.iconphoto(True, window._application_icon)
