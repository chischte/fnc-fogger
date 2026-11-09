"""Tk home screen for discovering, naming and selecting measurement lances."""
import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from . import logger
from .lance_discovery import discover_lances
from .lance_registry import LanceRegistry
from . import firmware_update

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
        self.updating = False
        self.update_events = queue.Queue()
        self.scan_timer = None
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.window = tk.Tk()
        self.window.title("Lance selection")
        self.window.geometry("1380x620")
        self.window.minsize(1100, 480)
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
        self.tree = ttk.Treeview(table, columns=("name", "location", "status", "hardware", "firmware",
                                               "build", "last_seen", "device_id", "address"),
                                 show="headings", selectmode="browse", height=7)
        for column, title, width in (("name", "Name", 150), ("location", "Location", 100),
                                      ("status", "Status", 75), ("hardware", "Hardware", 145),
                                      ("firmware", "Firmware (last confirmed)", 175),
                                      ("build", "Build", 110), ("last_seen", "Last seen", 145),
                                      ("device_id", "Device ID", 115), ("address", "Address", 220)):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=70)
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
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
        self.update_button = ttk.Button(actions, text="Update selected firmware", command=self._update,
                                        state="disabled")
        self.update_button.pack(side="left", padx=12)
        self.open_button = ttk.Button(actions, text="Open charts", command=self._open, state="disabled")
        self.open_button.pack(side="right")
        ttk.Label(frame, textvariable=self.status, wraplength=820).pack(anchor="w", pady=(14, 0))

    def _refresh_rows(self):
        self.devices = {item.device_id: item for item in self.registry.list()}
        for device_id, item in self.devices.items():
            values = (item.label, item.location, "Online" if device_id in self.online else "Offline",
                      item.hardware_profile or "Unknown", item.firmware or "Unknown",
                      item.build_id or "-", self._format_last_seen(item.last_seen),
                      item.device_id, item.hostname)
            if self.tree.exists(device_id):
                self.tree.item(device_id, values=values)
            else:
                self.tree.insert("", "end", iid=device_id, values=values)
        if not self.tree.selection() and self.devices:
            self.tree.selection_set(next(iter(self.devices)))
        self._update_button_state()

    @staticmethod
    def _format_last_seen(value):
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M:%S") if value else "-"

    def _update_button_state(self):
        enabled = self.selected_id in self.online and not self.updating
        self.update_button.configure(state="normal" if enabled else "disabled")

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
        self._update_button_state()

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
        if self.scanning or self.updating or self.stop.is_set():
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
            candidates = {lance.device_id: lance for lance in self.registry.list()}
            discovery_error = None
            try:
                candidates.update({lance.device_id: lance for lance in discover_lances(self.stop)})
            except Exception as error:
                discovery_error = str(error)
            for lance in candidates.values():
                if self.stop.is_set():
                    return
                try:
                    payload = logger.fetch_json(lance.url + "/api/current")
                except Exception:
                    continue
                serial = payload.get("measurement", {}).get("scd_serial")
                if payload.get("device_id", lance.device_id) != lance.device_id:
                    continue
                self.registry.remember(lance, serial, status=payload)
                online.add(lance.device_id)
            self.events.put((online, discovery_error))
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
            self.scan_button.configure(state="disabled" if self.updating else "normal")
            self._refresh_rows()
            if not self.updating:
                self.status.set(f"Discovery failed: {error}" if error else
                                f"{len(online)} lance(s) online. Saved lances are also available offline.")
            self.scan_timer = self.window.after(SCAN_INTERVAL_MS, self._scan)
        self.window.after(QUEUE_INTERVAL_MS, self._receive)
        self._receive_update()

    def _update(self):
        if self.updating or self.selected_id not in self.online or not self._save_labels():
            return
        lance = self.devices[self.selected_id]
        path = filedialog.askopenfilename(parent=self.window, title=f"Firmware for {lance.label}",
                                          filetypes=[("FNC firmware", "*.bin")])
        if not path:
            return
        try:
            image = firmware_update.read_image(path)
            # The worker repeats the live target check immediately before upload.
            profile = lance.hardware_profile or ("esp32s3" if lance.firmware.endswith("-esp32s3") else "")
            if image.profile != profile:
                raise ValueError(f"Selected firmware is for {image.profile}; device profile is {profile or 'unknown'}.")
        except Exception as error:
            messagebox.showerror("Firmware rejected", str(error), parent=self.window)
            return
        details = (f"{lance.label} / {lance.location}\nDevice ID: {lance.device_id}\n"
                   f"Address: {lance.url}\nHardware: {image.profile}\n"
                   f"{lance.firmware} -> {image.version}\nBuild: {image.build_id}\n\n"
                   "Install on this device?")
        if not messagebox.askyesno("Update selected device", details, parent=self.window):
            return
        self.updating = True
        self._update_button_state()
        self.scan_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.status.set(f"Updating {lance.label} ({lance.device_id}) ...")
        threading.Thread(target=self._install, args=(lance, image), daemon=True).start()

    def _install(self, lance, image):
        def report(phase, payload):
            self.registry.record_update(lance.device_id, image, phase)
            self.update_events.put((False, f"{lance.label}: {phase}"))

        try:
            result = firmware_update.install(lance, image, report, self.stop)
            self.registry.remember(lance, status=result)
            self.update_events.put((True, f"{lance.label}: firmware {image.version} confirmed after restart."))
        except Exception as error:
            detail = str(error)
            try:
                self.registry.record_update(lance.device_id, image, "unconfirmed", detail)
            except Exception as log_error:
                detail += f" Update history could not be saved: {log_error}"
            self.update_events.put((True, f"{lance.label}: update not confirmed. {detail}"))

    def _receive_update(self):
        while not self.update_events.empty():
            finished, text = self.update_events.get_nowait()
            self.status.set(text)
            if finished:
                self.updating = False
                self.scan_button.configure(state="normal")
                self.open_button.configure(state="normal" if self.selected_id else "disabled")
                self._refresh_rows()
                # A timer may have fired during the upload; restart periodic discovery.
                if self.scan_timer is not None:
                    self.window.after_cancel(self.scan_timer)
                self.scan_timer = self.window.after(SCAN_INTERVAL_MS, self._scan)

    def _open(self):
        if self.updating or not self.selected_id or not self._save_labels():
            return
        self._refresh_rows()
        self.result = self.devices[self.selected_id]
        self._finish()

    def _close(self):
        if self.updating:
            messagebox.showinfo("Firmware update", "Wait until the update result is available.", parent=self.window)
            return
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
