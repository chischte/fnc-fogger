"""Tk home screen for discovering, naming and selecting measurement lances."""
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from . import logger
from .lance_discovery import discover_lances
from .lance_registry import LanceRegistry

SCAN_INTERVAL_MS = 15000
QUEUE_INTERVAL_MS = 100


class LanceSelection:
    def __init__(self, directory):
        self.registry = LanceRegistry(directory)
        self.result = None
        self.devices = {}
        self.online = set()
        self.selected_id = None
        self.scanning = False
        self.scan_timer = None
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.window = tk.Tk()
        self.window.title("Lance selection")
        self.window.geometry("940x580")
        self.window.minsize(720, 480)
        self.window.configure(background="#f3f6f4")
        self.name = tk.StringVar(master=self.window)
        self.location = tk.StringVar(master=self.window)
        self.status = tk.StringVar(master=self.window, value="Searching for lances …")
        self._build()
        self._refresh_rows()
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        self.window.after(0, self._scan)
        self.window.after(QUEUE_INTERVAL_MS, self._receive)

    def _build(self):
        style = ttk.Style(self.window)
        style.theme_use("clam")
        style.configure("TFrame", background="#f3f6f4")
        style.configure("TLabel", background="#f3f6f4", foreground="#2a3630")
        style.configure("Treeview", rowheight=34, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#3b8c62")])
        frame = ttk.Frame(self.window, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Measurement lances", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Select a lance, assign a name and open its charts.",
                  font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 18))

        table = ttk.Frame(frame)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("name", "location", "status", "address"),
                                 show="headings", selectmode="browse", height=7)
        for column, title, width in (("name", "Name", 210), ("location", "Location", 180),
                                      ("status", "Status", 90), ("address", "Address", 280)):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=70)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._select)
        self.tree.bind("<Double-1>", lambda event: self._open())

        editor = ttk.Frame(frame)
        editor.pack(fill="x", pady=(18, 14))
        editor.columnconfigure(1, weight=1)
        editor.columnconfigure(3, weight=1)
        ttk.Label(editor, text="Name").grid(row=0, column=0, padx=(0, 8))
        ttk.Entry(editor, textvariable=self.name).grid(row=0, column=1, sticky="ew")
        ttk.Label(editor, text="Location").grid(row=0, column=2, padx=(18, 8))
        ttk.Entry(editor, textvariable=self.location).grid(row=0, column=3, sticky="ew")
        ttk.Button(editor, text="Save", command=self._save).grid(row=0, column=4, padx=(14, 0))

        actions = ttk.Frame(frame)
        actions.pack(fill="x")
        self.scan_button = ttk.Button(actions, text="Refresh", command=self._scan)
        self.scan_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="Open charts", command=self._open, state="disabled")
        self.open_button.pack(side="right")
        ttk.Label(frame, textvariable=self.status, wraplength=820).pack(anchor="w", pady=(14, 0))

    def _refresh_rows(self):
        self.devices = {item.device_id: item for item in self.registry.list()}
        for device_id, item in self.devices.items():
            values = (item.label, item.location, "Online" if device_id in self.online else "Offline",
                      item.hostname)
            if self.tree.exists(device_id):
                self.tree.item(device_id, values=values)
            else:
                self.tree.insert("", "end", iid=device_id, values=values)
        if not self.tree.selection() and self.devices:
            self.tree.selection_set(next(iter(self.devices)))

    def _select(self, _event=None):
        selection = self.tree.selection()
        if not selection or selection[0] == self.selected_id:
            return
        if not self._save_labels():
            if self.selected_id:
                self.tree.selection_set(self.selected_id)
            return
        self.selected_id = selection[0]
        item = self.devices[self.selected_id]
        self.name.set(item.name)
        self.location.set(item.location)
        self.open_button.configure(state="normal")

    def _save_labels(self):
        if self.selected_id is None:
            return True
        try:
            self.registry.save_labels(self.selected_id, self.name.get(), self.location.get())
            self._refresh_rows()
            return True
        except Exception as error:
            messagebox.showerror("Save failed", str(error), parent=self.window)
            return False

    def _save(self):
        if self._save_labels():
            self._refresh_rows()
            self.status.set("Name and location saved.")

    def _scan(self):
        if self.scanning or self.stop.is_set():
            return
        if self.scan_timer is not None:
            self.window.after_cancel(self.scan_timer)
            self.scan_timer = None
        self.scanning = True
        self.scan_button.configure(state="disabled")
        self.status.set("Searching for lances on the local network …")
        threading.Thread(target=self._discover, daemon=True).start()

    def _discover(self):
        try:
            online = set()
            for lance in discover_lances(self.stop):
                if self.stop.is_set():
                    return
                try:
                    payload = logger.fetch_json(lance.url + "/api/current")
                except Exception:
                    continue
                serial = payload.get("measurement", {}).get("scd_serial")
                self.registry.remember(lance, serial)
                online.add(lance.device_id)
            self.events.put((online, None))
        except Exception as error:
            self.events.put((set(), str(error)))

    def _receive(self):
        try:
            online, error = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.scanning = False
            self.online = online
            self.scan_button.configure(state="normal")
            self._refresh_rows()
            self.status.set(f"Discovery failed: {error}" if error else
                            f"{len(online)} lance(s) online. Saved lances are also available offline.")
            self.scan_timer = self.window.after(SCAN_INTERVAL_MS, self._scan)
        self.window.after(QUEUE_INTERVAL_MS, self._receive)

    def _open(self):
        if not self.selected_id or not self._save_labels():
            return
        self._refresh_rows()
        self.result = self.devices[self.selected_id]
        self._finish()

    def _close(self):
        if self._save_labels():
            self._finish()

    def _finish(self):
        self.stop.set()
        for callback in self.window.tk.call("after", "info"):
            self.window.after_cancel(callback)
        self.window.destroy()

    def show(self):
        self.window.mainloop()
        return self.result
