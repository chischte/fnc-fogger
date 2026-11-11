"""Device overview: discovery, metadata, naming and per-device actions."""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import firmware_update, logger
from .lance_discovery import discover_lances
from .lance_registry import LanceRegistry
from .window_icon import set_window_icon
from .viewer_overview import DeviceActions, DeviceOverview
from .viewer_style import DARK_THEME, LIGHT_THEME
from .viewer_device_header import format_device_id
from .firmware_catalog import available_versions, has_newer_firmware

SCAN_INTERVAL_MS = 15000
QUEUE_INTERVAL_MS = 100


class LanceSelection:
    def __init__(self, directory):
        self.registry = LanceRegistry(directory)
        self.result = None
        self.devices = {}
        self.online = set()
        self.firmware_versions = {}
        self.scanning = False
        self.has_scanned = False
        self.updating = False
        self.update_events = queue.Queue()
        self.scan_timer = None
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.dark_mode = True
        self.fullscreen = False
        self.window = tk.Tk()
        set_window_icon(self.window)
        self.window.title("Device Overview")
        width = min(1440, self.window.winfo_screenwidth() - 80)
        height = min(940, self.window.winfo_screenheight() - 80)
        self.window.geometry(f"{width}x{height}")
        self.window.minsize(min(1100, width), min(760, height))
        self.status = tk.StringVar(master=self.window, value="Searching for devices …")
        self._build()
        self._apply_theme()
        self._refresh_devices()
        self.window.protocol("WM_DELETE_WINDOW", self._close)
        self.window.after(0, self._scan)
        self.window.after(QUEUE_INTERVAL_MS, self._receive)
        self.window.after(0, self.overview.start)
        self.window.bind("<F11>", lambda event: self._toggle_fullscreen())
        self.window.bind("<Escape>", lambda event: self._exit_fullscreen())

    def _build(self):
        ttk.Style(self.window).theme_use("clam")
        frame = ttk.Frame(self.window, padding=16)
        frame.pack(fill="both", expand=True)
        actions = DeviceActions(self._open_device, self._update, self._remove,
                                self._save_device_labels, self._copy_device_id)
        self.overview = DeviceOverview(frame, self.registry, actions, DARK_THEME)
        controls = ttk.Frame(frame)
        controls.pack(pady=(10, 2))
        self.theme_button = ttk.Button(controls, text="Light Mode", command=self._toggle_theme)
        self.theme_button.pack(side="left", padx=10)
        self.fullscreen_button = ttk.Button(controls, text="Full Screen", command=self._toggle_fullscreen)
        self.fullscreen_button.pack(side="left")
        ttk.Label(frame, textvariable=self.status, wraplength=1100).pack(anchor="w", pady=(10, 0))

    def _apply_theme(self):
        theme = DARK_THEME if self.dark_mode else LIGHT_THEME
        self.window.configure(background=theme["page"])
        style = ttk.Style(self.window)
        style.configure("TFrame", background=theme["page"])
        style.configure("TLabel", background=theme["page"], foreground=theme["text"])
        style.configure("TButton", background=theme["button_off"], foreground=theme["text"], padding=(9, 5))
        style.map("TButton", background=[("active", theme["button_on"])],
                  foreground=[("disabled", theme["muted"])])
        style.configure("TEntry", fieldbackground=theme["card"], foreground=theme["text"], insertcolor=theme["text"])
        style.configure("TScrollbar", background=theme["button_off"], troughcolor=theme["page"],
                        arrowcolor=theme["muted"], bordercolor=theme["grid"])
        self.theme_button.configure(text="Light Mode" if self.dark_mode else "Dark Mode")
        self.overview.apply_theme(theme)

    def _toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self._apply_theme()

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        self.window.attributes("-fullscreen", self.fullscreen)
        self.fullscreen_button.configure(text="Exit Full Screen" if self.fullscreen else "Full Screen")

    def _exit_fullscreen(self):
        if self.fullscreen:
            self._toggle_fullscreen()

    def _refresh_devices(self):
        self.devices = {item.device_id: item for item in self.registry.list()}
        self.overview.update_devices(self.devices, self.online)
        self._update_button_state()

    def _update_button_state(self):
        for device_id, column in self.overview.columns.items():
            newer_available = has_newer_firmware(self.devices[device_id], self.firmware_versions)
            column.set_actions_enabled(not self.updating,
                                       newer_available and device_id in self.online and not self.updating,
                                       self._can_remove(device_id),
                                       show_update=newer_available,
                                       show_remove=self.has_scanned and device_id not in self.online)

    def _commit_edits(self):
        return self.overview.commit_edits()

    def _save_device_labels(self, device_id, name, location):
        if self.updating or device_id not in self.devices:
            return False
        try:
            self.registry.save_labels(device_id, name, location)
            self._refresh_devices()
            return True
        except Exception as error:
            messagebox.showerror("Save failed", str(error), parent=self.window)
            return False

    def _copy_device_id(self, device_id):
        if device_id not in self.devices:
            return
        text = format_device_id(device_id)
        try:
            self.window.clipboard_clear()
            self.window.clipboard_append(text)
        except tk.TclError as error:
            messagebox.showerror("Copy failed", str(error), parent=self.window)
            return
        self.status.set(f"Device ID copied: {text}")

    def _open_device(self, device_id):
        if self.updating or device_id not in self.devices or not self._commit_edits():
            return
        self.result = self.devices[device_id]
        self._finish()

    def _can_remove(self, device_id):
        return (device_id in self.devices and device_id not in self.online
                and self.has_scanned and not self.scanning and not self.updating)

    def _remove(self, device_id):
        if not self._can_remove(device_id) or not self._commit_edits():
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
        self._refresh_devices()
        self.status.set(f"{item.label} removed. Saved measurements and update history were kept.")

    def _scan(self):
        if self.scanning or self.updating or self.stop.is_set():
            return
        if self.scan_timer is not None:
            self.window.after_cancel(self.scan_timer)
            self.scan_timer = None
        self.scanning = True
        self._update_button_state()
        self.status.set("Searching for devices on the local network …")
        threading.Thread(target=self._discover, daemon=True).start()

    def _discover(self):
        versions = {}
        try:
            versions = available_versions(Path(__file__).resolve().parents[1] / "firmware")
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
            self.events.put((online, discovery_error, versions))
        except Exception as error:
            self.events.put((set(), str(error), versions))

    def _receive(self):
        try:
            online, error, versions = self.events.get_nowait()
        except queue.Empty:
            pass
        else:
            self.scanning = False
            self.has_scanned = error is None
            self.online = online
            self.firmware_versions = versions
            self._refresh_devices()
            if not self.updating:
                self.status.set(f"Discovery failed: {error}" if error else
                                f"{len(online)} device(s) online. Saved devices are also available offline.")
            self.scan_timer = self.window.after(SCAN_INTERVAL_MS, self._scan)
        self.window.after(QUEUE_INTERVAL_MS, self._receive)
        self._receive_update()

    def _update(self, device_id):
        if self.updating or device_id not in self.online or not self._commit_edits():
            return
        lance = self.devices[device_id]
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
                self._refresh_devices()
                # A timer may have fired during the upload; restart periodic discovery.
                if self.scan_timer is not None:
                    self.window.after_cancel(self.scan_timer)
                self.scan_timer = self.window.after(SCAN_INTERVAL_MS, self._scan)

    def _close(self):
        if self.updating:
            messagebox.showinfo("Firmware update", "Wait until the update result is available.", parent=self.window)
            return
        if self._commit_edits():
            self._finish()

    def _finish(self):
        self.stop.set()
        # Drain pending ttk theme redraws while their widgets still exist.
        self.window.update_idletasks()
        self.overview.close()
        for callback in self.window.tk.call("after", "info"):
            self.window.after_cancel(callback)
        self.window.destroy()

    def show(self):
        self.window.mainloop()
        return self.result
