"""Centered device metadata and inline name/location editing."""
from datetime import datetime
import tkinter as tk
from tkinter import ttk


def format_last_seen(value):
    if not value:
        return "-"
    seen = datetime.fromisoformat(value).astimezone()
    pattern = "%H:%M:%S" if seen.date() == datetime.now().astimezone().date() else "%Y-%m-%d %H:%M:%S"
    return seen.strftime(pattern)


def format_device_id(value):
    return ":".join(value[index:index + 2] for index in range(0, len(value), 2)).upper()


def format_firmware(value):
    return value.removesuffix("-esp32c3").removesuffix("-esp32s3").lower() if value else "unknown"


class DeviceHeader:
    def __init__(self, parent, device, save_labels):
        self.device = device
        self.save_labels = save_labels
        self.editing = False
        self.edit_enabled = True
        self.saving = False
        self.focus_timer = None
        self.closed = False
        self.frame = tk.Frame(parent)
        self.frame.columnconfigure(0, weight=1)
        self.title = tk.Label(self.frame, font=("Segoe UI Semibold", 12), height=2,
                              wraplength=290, justify="center", cursor="xterm")
        self.title.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        title_row_height = round((self.title.winfo_reqheight() + 10) * 0.8)
        self.title.configure(height=0)
        self.frame.rowconfigure(0, minsize=title_row_height)
        self.title.bind("<Button-1>", lambda event: self.begin_edit())
        self.status = tk.Label(self.frame, font=("Segoe UI Semibold", 9), justify="center")
        self.status.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.editor = tk.Frame(self.frame)
        self.name = tk.StringVar(master=self.frame)
        self.location = tk.StringVar(master=self.frame)
        self.name_entry = ttk.Entry(self.editor, textvariable=self.name, justify="center", width=14)
        self.location_entry = ttk.Entry(self.editor, textvariable=self.location, justify="center", width=14)
        self.name_entry.grid(row=0, column=0, sticky="ew", padx=2)
        self.separator = tk.Label(self.editor, text="@")
        self.separator.grid(row=0, column=1)
        self.location_entry.grid(row=0, column=2, sticky="ew", padx=2)
        self.editor.columnconfigure((0, 2), weight=1)
        for entry in (self.name_entry, self.location_entry):
            entry.bind("<Return>", lambda event: self.commit_edit())
            entry.bind("<Escape>", lambda event: self.cancel_edit())
            entry.bind("<FocusOut>", lambda event: self._schedule_leave())
        self.frame.bind("<Configure>", lambda event: self.title.configure(
            wraplength=max(120, event.width - 24)))
        self.update(device, False)

    def update(self, device, online):
        self.device = device
        self.connection = "online" if online else "offline"
        self.title.configure(text=device.label + (f" @ {device.location}" if device.location else ""))
        self._update_status()

    def _update_status(self):
        text = self.connection
        if self.connection == "offline":
            text = f"last seen {format_last_seen(self.device.last_seen)}"
        self.status.configure(text=text)

    def begin_edit(self):
        if not self.edit_enabled or self.editing:
            return
        self.name.set(self.device.name)
        self.location.set(self.device.location)
        self.editing = True
        self.title.grid_remove()
        self.editor.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        self.name_entry.focus_set()
        self.name_entry.selection_range(0, "end")

    def _leave_editor(self):
        self.focus_timer = None
        if self.editing and self.frame.focus_get() not in (self.name_entry, self.location_entry):
            self.commit_edit()

    def _schedule_leave(self):
        if self.closed:
            return
        if self.focus_timer is not None:
            self.frame.after_cancel(self.focus_timer)
        self.focus_timer = self.frame.after_idle(self._leave_editor)

    def commit_edit(self):
        if not self.editing:
            return True
        if self.saving:
            return False
        self.saving = True
        try:
            if not self.save_labels(self.device.device_id, self.name.get(), self.location.get()):
                self.name_entry.focus_set()
                return False
            self.cancel_edit()
            return True
        finally:
            self.saving = False

    def cancel_edit(self):
        self.editing = False
        self.editor.grid_remove()
        self.title.grid()
        return "break"

    def apply_theme(self, theme):
        for widget in (self.frame, self.editor):
            widget.configure(background=theme["card"])
        for label in (self.title, self.status, self.separator):
            label.configure(background=theme["card"], foreground=theme["text"] if label == self.title else theme["muted"])

    def close(self):
        self.closed = True
        if self.focus_timer is not None:
            self.frame.after_cancel(self.focus_timer)
            self.focus_timer = None


class DeviceIdentity:
    """Compact, copyable identity line between the charts and actions."""
    def __init__(self, parent, device, copy_id):
        self.frame = tk.Frame(parent)
        self.device_id = tk.Entry(self.frame, justify="center", relief="flat", borderwidth=0,
                                  width=17, highlightthickness=0, exportselection=False,
                                  font=("Consolas", 9), cursor="xterm")
        self.device_id.insert(0, format_device_id(device.device_id))
        self.device_id.configure(state="readonly")
        self.device_id.pack(side="left")
        self.device_id.bind("<Button-1>", lambda event: copy_id(device.device_id))
        self.separator = tk.Label(self.frame, text=" | ", font=("Segoe UI", 9), padx=0)
        self.separator.pack(side="left")
        self.firmware = tk.Label(self.frame, font=("Segoe UI", 9), padx=0)
        self.firmware.pack(side="left")
        self.update(device)

    def update(self, device):
        self.firmware.configure(text=f"Firmware {format_firmware(device.firmware)}")

    def apply_theme(self, theme):
        self.frame.configure(background=theme["card"])
        self.device_id.configure(readonlybackground=theme["card"], foreground=theme["muted"])
        for label in (self.separator, self.firmware):
            label.configure(background=theme["card"], foreground=theme["muted"])
