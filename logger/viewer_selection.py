"""Tk home screen for discovering, naming and selecting measurement lances."""
import queue
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from datetime import datetime

from . import logger
from .lance_discovery import discover_lances
from .lance_registry import LanceRegistry
from . import firmware_update
from .window_icon import set_window_icon

SCAN_INTERVAL_MS = 15000
QUEUE_INTERVAL_MS = 100


class LanceSelection:
    def __init__(self, directory):
        self.registry = LanceRegistry(directory)
        self.result = None
        self.devices = {}
        self.online = set()
        self.selected_id = None
        self.cell_editor = None
        self.address_links = {}
        self.device_id_fields = {}
        self.edit_column = None
        self.saving_labels = False
        self.scanning = False
        self.has_scanned = False
        self.updating = False
        self.update_events = queue.Queue()
        self.scan_timer = None
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.window = tk.Tk()
        set_window_icon(self.window)
        self.window.title("Device Selection")
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
        style.configure("Treeview", rowheight=34, font=("Segoe UI Semibold", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))
        style.map("Treeview", background=[("selected", "#3b8c62")])
        frame = ttk.Frame(self.window, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Device Selection", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(frame, text="Select a device, assign a name and open its viewer",
                  font=("Segoe UI", 11)).pack(anchor="w", pady=(4, 18))

        table = ttk.Frame(frame)
        table.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(table, columns=("name", "location", "status", "firmware",
                                               "last_seen", "device_id", "address"),
                                 show="headings", selectmode="browse", height=7)
        for column, title, width in (("name", "Name", 150), ("location", "Location", 100),
                                      ("status", "Status", 75), ("firmware", "Firmware", 110),
                                      ("last_seen", "Last seen", 145),
                                      ("device_id", "Device ID", 165), ("address", "Address", 220)):
            self.tree.heading(column, text=title)
            self.tree.column(column, width=width, minwidth=70,
                             anchor="w" if column == "name" else "center")
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scrollbar.set, xscrollcommand=horizontal.set)
        table.rowconfigure(0, weight=1)
        table.columnconfigure(0, weight=1)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.bind("<<TreeviewSelect>>", self._select)
        self.tree.bind("<Double-1>", self._double_click)
        self.tree.bind("<ButtonRelease-1>", self._click_address)
        self.tree.bind("<Motion>", self._hover_cell)
        self.tree.bind("<Leave>", lambda event: self.tree.configure(cursor=""))
        self.tree.bind("<Configure>", lambda event: self._position_cells())
        self.tree.configure(yscrollcommand=lambda *args: self._scroll_editor(scrollbar, *args),
                            xscrollcommand=lambda *args: self._scroll_editor(horizontal, *args))
        actions = ttk.Frame(frame, padding=(0, 14, 0, 0))
        actions.pack(fill="x")
        self.scan_button = ttk.Button(actions, text="Refresh", command=self._scan)
        self.scan_button.pack(side="left")
        self.update_button = ttk.Button(actions, text="Update Firmware", command=self._update,
                                        state="disabled")
        self.update_button.pack(side="left", padx=12)
        self.remove_button = ttk.Button(actions, text="Remove Offline Device", command=self._remove,
                                        state="disabled")
        self.remove_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="Open Viewer", command=self._open, state="disabled")
        self.open_button.pack(side="right")
        ttk.Label(frame, textvariable=self.status, wraplength=820).pack(anchor="w", pady=(14, 0))

    def _refresh_rows(self):
        self.devices = {item.device_id: item for item in self.registry.list()}
        for device_id in self.tree.get_children():
            if device_id not in self.devices:
                self.tree.delete(device_id)
        if self.selected_id not in self.devices:
            self._cancel_edit()
            self.selected_id = None
            self.name.set("")
            self.location.set("")
            self.open_button.configure(state="disabled")
        for device_id, item in self.devices.items():
            values = (item.label, item.location, "online" if device_id in self.online else "offline",
                      self._format_firmware(item.firmware), self._format_last_seen(item.last_seen),
                      self._format_device_id(item.device_id), item.hostname)
            if self.tree.exists(device_id):
                self.tree.item(device_id, values=values)
            else:
                self.tree.insert("", "end", iid=device_id, values=values)
        if not self.tree.selection() and self.devices:
            self.tree.selection_set(next(iter(self.devices)))
        self._update_button_state()
        self._position_cells()

    def _position_cells(self):
        self._position_editor()
        self._position_address_links()
        self._position_device_ids()

    def _position_device_ids(self):
        for device_id in list(self.device_id_fields):
            if device_id not in self.devices:
                self.device_id_fields.pop(device_id).destroy()
        selected = self.tree.selection()
        for device_id in self.devices:
            if device_id not in self.device_id_fields:
                field = tk.Entry(self.tree, justify="center", relief="flat", borderwidth=0,
                                 highlightthickness=0, exportselection=False,
                                 font=("Segoe UI Semibold", 10), cursor="xterm")
                field.insert(0, self._format_device_id(device_id))
                field.configure(state="readonly")
                field.bind("<Button-1>", lambda event, target=device_id: self._copy_device_id(target))
                self.device_id_fields[device_id] = field
            field = self.device_id_fields[device_id]
            is_selected = device_id in selected
            field.configure(readonlybackground="#3b8c62" if is_selected else "white",
                            foreground="white" if is_selected else "#2a3630")
            self._place_cell(field, device_id, "device_id")

    def _copy_device_id(self, device_id):
        if device_id not in self.devices or not self._save_labels():
            return
        self.tree.selection_set(device_id)
        self._select()
        text = self._format_device_id(device_id)
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
        except tk.TclError as error:
            messagebox.showerror("Copy failed", str(error), parent=self.window)
            return
        self.status.set(f"Device ID copied: {text}")

    def _position_address_links(self):
        # Treeview cannot style individual cells, so links overlay the address cells.
        for device_id in list(self.address_links):
            if device_id not in self.devices:
                self.address_links.pop(device_id).destroy()
        selected = self.tree.selection()
        for device_id, device in self.devices.items():
            if device_id not in self.address_links:
                link = tk.Label(self.tree, foreground="#0055cc", borderwidth=0,
                                font=("Segoe UI", 10, "underline"), cursor="hand2")
                link.bind("<ButtonRelease-1>", lambda event, target=device_id: self._open_address(target))
                self.address_links[device_id] = link
            link = self.address_links[device_id]
            is_selected = device_id in selected
            link.configure(text=device.hostname,
                           background="#3b8c62" if is_selected else "white",
                           foreground="white" if is_selected else "#0055cc")
            self._place_cell(link, device_id, "address")

    def _place_cell(self, widget, device_id, column):
        bounds = self.tree.bbox(device_id, column)
        if bounds:
            x, y, width, height = bounds
            widget.place(x=x, y=y, width=width, height=height)
        else:
            widget.place_forget()

    def _cell_at(self, event):
        row = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if self.tree.identify_region(event.x, event.y) != "cell" or not row or not column:
            return None, None
        return row, self.tree["columns"][int(column[1:]) - 1]

    def _hover_cell(self, event):
        _, column = self._cell_at(event)
        self.tree.configure(cursor="hand2" if column == "address" else "")

    def _click_address(self, event):
        device_id, column = self._cell_at(event)
        if column == "address":
            self._open_address(device_id)

    def _open_address(self, device_id):
        if device_id not in self.devices or not self._save_labels():
            return
        try:
            if not webbrowser.open(self.devices[device_id].url, new=2):
                raise RuntimeError("No browser could be opened.")
        except Exception as error:
            messagebox.showerror("Open address failed", str(error), parent=self.window)

    def _double_click(self, event):
        device_id, column = self._cell_at(event)
        if column in ("name", "location"):
            self._edit_cell(device_id, column)
        elif column and column not in ("address", "device_id"):
            self._open()
        return "break"

    def _edit_cell(self, device_id, column):
        if not self._save_labels():
            return
        self.tree.selection_set(device_id)
        self._select()
        self.tree.see(device_id)
        self.tree.update_idletasks()
        self.edit_column = column
        value = self.name.get() if column == "name" else self.location.get()
        self.cell_editor = ttk.Entry(self.tree, justify="left" if column == "name" else "center")
        self.cell_editor.insert(0, value)
        self.cell_editor.bind("<Return>", lambda event: self._commit_edit())
        self.cell_editor.bind("<Escape>", lambda event: self._cancel_edit())
        self.cell_editor.bind("<FocusOut>", lambda event: self._save_labels())
        self._position_editor()
        self.cell_editor.focus_set()
        self.cell_editor.selection_range(0, "end")

    def _position_editor(self):
        if self.cell_editor is None:
            return
        bounds = self.tree.bbox(self.selected_id, self.edit_column)
        if not bounds:
            self._save_labels()
            return
        x, y, width, height = bounds
        self.cell_editor.place(x=x, y=y, width=width, height=height)

    def _scroll_editor(self, scrollbar, *args):
        scrollbar.set(*args)
        self._position_cells()

    def _commit_edit(self):
        if self._save_labels():
            self.tree.focus_set()
        return "break"

    def _cancel_edit(self, restore=True):
        editor = self.cell_editor
        if editor is not None and restore and self.selected_id in self.devices:
            item = self.devices[self.selected_id]
            self.name.set(item.name)
            self.location.set(item.location)
        self.cell_editor = None
        self.edit_column = None
        if editor is not None:
            editor.destroy()
        return "break"

    @staticmethod
    def _format_last_seen(value):
        if not value:
            return "-"
        seen = datetime.fromisoformat(value).astimezone()
        pattern = "%H:%M:%S" if seen.date() == datetime.now().astimezone().date() else "%Y-%m-%d %H:%M:%S"
        return seen.strftime(pattern)

    @staticmethod
    def _format_device_id(value):
        return ":".join(value[index:index + 2] for index in range(0, len(value), 2)).upper()

    @staticmethod
    def _format_firmware(value):
        return value.removesuffix("-esp32c3").removesuffix("-esp32s3") if value else "Unknown"

    def _update_button_state(self):
        enabled = self.selected_id in self.online and not self.updating
        self.update_button.configure(state="normal" if enabled else "disabled")
        self.remove_button.configure(state="normal" if self._can_remove(self.selected_id) else "disabled")

    def _can_remove(self, device_id):
        return (device_id in self.devices and device_id not in self.online
                and self.has_scanned and not self.scanning and not self.updating)

    def _remove(self):
        device_id = self.selected_id
        if not self._can_remove(device_id):
            return
        item = self.devices[device_id]
        if not messagebox.askyesno("Remove offline device",
                                  f"Remove {item.label} ({device_id}) from the device list?\n\n"
                                  "Measurements and update history will be kept. "
                                  "If the device comes online again, it will reappear.", parent=self.window):
            return
        if not self._can_remove(device_id):
            self.status.set("Device status changed. Wait for discovery and try again.")
            return
        try:
            self.registry.remove(device_id)
        except Exception as error:
            messagebox.showerror("Remove failed", str(error), parent=self.window)
            return
        self._refresh_rows()
        self._select()
        self.status.set(f"{item.label} removed. Saved measurements and update history were kept.")

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
        self._position_cells()

    def _save_labels(self):
        if self.selected_id is None:
            return True
        if self.saving_labels:
            return False
        self.saving_labels = True
        try:
            if self.cell_editor is not None:
                variable = self.name if self.edit_column == "name" else self.location
                variable.set(self.cell_editor.get())
            self.registry.save_labels(self.selected_id, self.name.get(), self.location.get())
            self._cancel_edit(restore=False)
            self._refresh_rows()
            return True
        except Exception as error:
            messagebox.showerror("Save failed", str(error), parent=self.window)
            if self.cell_editor is not None:
                self.window.after_idle(self.cell_editor.focus_set)
            return False
        finally:
            self.saving_labels = False

    def _scan(self):
        if self.scanning or self.updating or self.stop.is_set():
            return
        if self.scan_timer is not None:
            self.window.after_cancel(self.scan_timer)
            self.scan_timer = None
        self.scanning = True
        self._update_button_state()
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
            self.has_scanned = error is None
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
                                          initialdir=Path(__file__).resolve().parents[1] / "firmware",
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
