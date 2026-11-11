"""Reduced device charts embedded in the selection window, without controls."""
from dataclasses import dataclass
from collections.abc import Callable
import queue
import sqlite3
import threading
import tkinter as tk
from tkinter import ttk

import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FixedLocator, MultipleLocator
from pandas.errors import DatabaseError

from .overview_data import HISTORY_WINDOW, load_overview_history, overview_time
from .viewer_style import SERIES
from .viewer_device_header import DeviceHeader, DeviceIdentity

REFRESH_SECONDS = 10
POLL_INTERVAL_MS = 200
MIN_COLUMN_WIDTH = 420
COLUMN_HEIGHT = 480


@dataclass(frozen=True)
class DeviceActions:
    open_viewer: Callable
    update_firmware: Callable
    remove_device: Callable
    save_labels: Callable
    copy_id: Callable


class DeviceColumn:
    def __init__(self, parent, device, actions, theme):
        self.device_id = device.device_id
        self.frame = tk.Frame(parent, highlightthickness=1, borderwidth=0)
        self.actions = actions
        self.header = DeviceHeader(self.frame, device, actions.save_labels)
        self.header.frame.grid(row=0, column=0, sticky="ew")
        self.title = self.header.title
        self.figure = Figure(figsize=(3.3, 4.5), dpi=100)
        self.axes = self.figure.subplots(3, 1, sharex=True)
        self.figure.subplots_adjust(left=0.126, right=0.874, top=0.952, bottom=0.056, hspace=0.40)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self.frame)
        self.canvas.get_tk_widget().configure(cursor="hand2")
        self.canvas.get_tk_widget().grid(row=1, column=0, sticky="nsew")
        self.buttons = tk.Frame(self.frame)
        self.buttons.grid(row=3, column=0, padx=8, pady=(0, 14))
        self.update_button = ttk.Button(self.buttons, text="Update Firmware",
                                        command=lambda: actions.update_firmware(self.device_id))
        self.remove_button = ttk.Button(self.buttons, text="Remove Offline Device",
                                        command=lambda: actions.remove_device(self.device_id))
        button_width = max(button.winfo_reqwidth() for button in (self.update_button, self.remove_button))
        self.button_width = button_width
        self.identity = DeviceIdentity(self.frame, device, actions.copy_id)
        self.identity.frame.grid(row=2, column=0, pady=(0, 11))
        self.frame.rowconfigure(1, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.canvas.mpl_connect("button_press_event", self._click)
        self.lines = []
        self.empty_labels = []
        for axis, series in zip(self.axes, SERIES):
            line, = axis.plot([], [], color=series["color"], linewidth=1.5)
            self.lines.append(line)
            self.empty_labels.append(axis.text(0.5, 0.5, "No recent measurements",
                                                transform=axis.transAxes, ha="center", fontsize=8))
            axis.set_ylim(series["ymin"], series["ymax"])
            if "ticks" in series:
                axis.yaxis.set_major_locator(FixedLocator(series["ticks"]))
            elif series["step"]:
                axis.yaxis.set_major_locator(MultipleLocator(series["step"]))
            else:
                axis.yaxis.set_major_locator(FixedLocator([0, 5000, 10000, 15000]))
            axis.set_title(f'{series["label"]} [{series["unit"]}]', fontsize=9, fontweight="bold", pad=6.6)
            axis.set_navigate(False)
            axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=2, maxticks=4))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        self.update_device(device, False)
        self.set_window(overview_time())
        self.apply_theme(theme)

    def _click(self, event):
        if event.button == 1 and event.inaxes in self.axes:
            self.actions.open_viewer(self.device_id)

    def update_device(self, device, online):
        self.header.update(device, online)
        self.identity.update(device)

    def set_actions_enabled(self, open_viewer, update_firmware, remove_device,
                            show_update=True, show_remove=True):
        self.update_button.configure(state="normal" if update_firmware else "disabled")
        self.remove_button.configure(state="normal" if remove_device else "disabled")
        self.header.edit_enabled = open_viewer
        for index, (button, visible) in enumerate(((self.update_button, show_update),
                                                   (self.remove_button, show_remove))):
            button.grid_remove()
            self.buttons.columnconfigure(index, minsize=self.button_width if visible else 0)
            if visible:
                button.grid(row=0, column=index, sticky="ew", padx=2)
        if show_update or show_remove:
            self.buttons.grid()
        else:
            self.buttons.grid_remove()

    def set_window(self, end):
        self.axes[-1].set_xlim(end - HISTORY_WINDOW, end)

    def update_history(self, frame, end, error=None):
        self.set_window(end)
        for line, label, series in zip(self.lines, self.empty_labels, SERIES):
            if frame is None:
                line.set_data([], [])
                label.set_text("History unavailable" if error else "No recent measurements")
                label.set_visible(True)
                continue
            line.set_data(frame["timestamp"], frame[series["col"]])
            label.set_text("No recent measurements")
            label.set_visible(not frame[series["col"]].notna().any())
        self.canvas.draw_idle()

    def apply_theme(self, theme):
        self.frame.configure(background=theme["card"], highlightbackground=theme["grid"])
        self.header.apply_theme(theme)
        self.identity.apply_theme(theme)
        self.buttons.configure(background=theme["card"])
        self.figure.set_facecolor(theme["card"])
        self.canvas.get_tk_widget().configure(background=theme["card"])
        for axis, label in zip(self.axes, self.empty_labels):
            axis.set_facecolor(theme["plot"])
            axis.title.set_color(theme["text"])
            axis.tick_params(colors=theme["muted"], labelsize=7, labelbottom=True)
            axis.grid(axis="y", color=theme["grid"], linewidth=0.6, linestyle="-")
            for spine in axis.spines.values():
                spine.set_color(theme["grid"])
            label.set_color(theme["muted"])
        self.canvas.draw()

    def destroy(self):
        self.header.close()
        widget = self.canvas.get_tk_widget()
        for attribute in ("_idle_draw_id", "_event_loop_id"):
            callback = getattr(self.canvas, attribute, None)
            if callback is not None:
                widget.after_cancel(callback)
                setattr(self.canvas, attribute, None)
        self.figure.clear()
        self.frame.destroy()


class DeviceOverview:
    def __init__(self, parent, registry, actions, theme):
        self.registry = registry
        self.actions = actions
        self.theme = theme
        self.columns = {}
        self.stop = threading.Event()
        self.results = queue.Queue(maxsize=1)
        self.thread = None
        self.poll_timer = None
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(self.frame, highlightthickness=0, height=COLUMN_HEIGHT)
        self.scrollbar = ttk.Scrollbar(self.frame, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.scrollbar.set)
        self.canvas.pack(fill="both", expand=True)
        self.scrollbar.pack(fill="x")
        self.content = tk.Frame(self.canvas)
        self.content_id = self.canvas.create_window((0, 0), window=self.content, anchor="nw")
        self.canvas.bind("<Configure>", self._resize)
        self.empty = tk.Label(self.content, text="No devices registered. Searching the local network …",
                              font=("Segoe UI", 12))
        self.apply_theme(theme)

    def update_devices(self, devices, online):
        for index in range(len(self.columns)):
            self.content.columnconfigure(index, weight=0, uniform="")
        for device_id in set(self.columns) - set(devices):
            self.columns.pop(device_id).destroy()
        for index, device in enumerate(devices.values()):
            if device.device_id not in self.columns:
                self.columns[device.device_id] = DeviceColumn(
                    self.content, device, self.actions, self.theme)
            column = self.columns[device.device_id]
            column.update_device(device, device.device_id in online)
            column.frame.grid(row=0, column=index, sticky="nsew", padx=4)
            self.content.columnconfigure(index, weight=1, uniform="devices")
        if devices:
            self.empty.grid_forget()
        else:
            self.empty.grid(row=0, column=0, padx=20, pady=30)
        self._resize()

    def _resize(self, _event=None):
        width = max(self.canvas.winfo_width(), MIN_COLUMN_WIDTH * len(self.columns))
        height = max(1, self.canvas.winfo_height())
        self.canvas.itemconfigure(self.content_id, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        if width > self.canvas.winfo_width():
            self.scrollbar.pack(fill="x")
        else:
            self.scrollbar.pack_forget()
        self.content.rowconfigure(0, weight=1)

    def commit_edits(self):
        return all(column.header.commit_edit() for column in list(self.columns.values()))

    def apply_theme(self, theme):
        self.theme = theme
        self.canvas.configure(background=theme["page"])
        self.content.configure(background=theme["page"])
        self.empty.configure(background=theme["page"], foreground=theme["muted"])
        for column in self.columns.values():
            column.apply_theme(theme)

    def start(self):
        if self.thread is not None or self.stop.is_set():
            return
        self.thread = threading.Thread(target=self._load, daemon=True)
        self.thread.start()
        self._poll()

    def _load(self):
        while not self.stop.is_set():
            end = overview_time()
            histories = {}
            load_error = None
            try:
                for device in self.registry.list():
                    if self.stop.is_set():
                        return
                    try:
                        frame = load_overview_history(self.registry.measurement_path(device), end)
                        histories[device.device_id] = (frame, None)
                    except (OSError, ValueError, KeyError, sqlite3.Error, DatabaseError) as error:
                        histories[device.device_id] = (None, str(error))
            except (OSError, sqlite3.Error) as error:
                load_error = str(error)
            try:
                self.results.put_nowait((end, histories, load_error))
            except queue.Full:
                pass
            self.stop.wait(REFRESH_SECONDS)

    def _poll(self):
        if self.stop.is_set():
            return
        try:
            end, histories, error = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            for device_id, column in self.columns.items():
                frame, history_error = histories.get(device_id, (None, error))
                column.update_history(frame, end, history_error)
        self.poll_timer = self.frame.after(POLL_INTERVAL_MS, self._poll)

    def close(self):
        self.stop.set()
        if self.poll_timer is not None:
            self.frame.after_cancel(self.poll_timer)
            self.poll_timer = None
        for column in self.columns.values():
            column.destroy()
        self.columns.clear()
