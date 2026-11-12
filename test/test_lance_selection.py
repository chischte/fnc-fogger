import sys
import sqlite3
import tempfile
import unittest
from contextlib import closing, contextmanager
from pathlib import Path
from unittest.mock import patch

from logger import logger, viewer, viewer_data
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance, LanceRegistry


class LanceRegistryTests(unittest.TestCase):
    def test_equipment_survives_restart_and_rediscovery(self):
        self.assertFalse(self.registry.remember(self.lance).actuators_installed)
        self.registry.set_actuators_installed(self.lance.device_id, True)
        registry = LanceRegistry(self.directory)
        updated = registry.remember(Lance(self.lance.device_id, "new.local", 8080))
        self.assertTrue(updated.actuators_installed)
        registry.set_actuators_installed(self.lance.device_id, False)
        self.assertFalse(registry.list()[0].actuators_installed)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.registry = LanceRegistry(self.directory)
        self.lance = Lance("14c19f5cc8b4", "fnc-fogger-5cc8b4.local", 80)

    def tearDown(self):
        self.temp.cleanup()

    def test_labels_survive_restart_and_address_change(self):
        original = self.registry.remember(self.lance)
        self.registry.save_labels(self.lance.device_id, " Chamber 1 ", " Lab ")
        registry = LanceRegistry(self.directory)
        updated = registry.remember(Lance(self.lance.device_id, "new.local", 8080))
        self.assertEqual((updated.name, updated.location), ("Chamber 1", "Lab"))
        self.assertEqual(updated.database_name, original.database_name)
        self.assertEqual(updated.url, "http://new.local:8080")

    def test_legacy_history_is_assigned_only_to_matching_sensor(self):
        with closing(logger.connect(self.directory / "measurements.db")) as db:
            logger.insert(db, {"boot_id": 1, "sequence": 1, "scd_serial": "SENSOR-A"})
        other = self.registry.remember(Lance("aaaaaaaaaaaa", "other.local", 80), "SENSOR-B")
        selected = self.registry.remember(self.lance, "SENSOR-A")
        self.assertEqual(selected.database_name, "measurements.db")
        self.assertNotEqual(other.database_name, selected.database_name)
        self.assertEqual(len(self.registry.list()), 2)

    def test_different_lances_keep_identical_boot_sequences_separate(self):
        first = self.registry.remember(self.lance)
        second = self.registry.remember(Lance("aaaaaaaaaaaa", "other.local", 80))
        for lance, temperature in [(first, 23), (second, 29)]:
            path = self.registry.measurement_path(lance)
            with closing(logger.connect(path)) as db:
                logger.insert(db, {"boot_id": 1, "sequence": 1, "boxtemp": temperature})
            frame = viewer_data.load_data(path, path.with_suffix(".csv"))
            self.assertEqual(frame["temp_box_c"].tolist(), [temperature])

    def test_invalid_device_id_cannot_become_a_database_path(self):
        with self.assertRaises(ValueError):
            self.registry.remember(Lance("../../elsewhere", "bad.local", 80))

    def test_removing_device_preserves_history_and_restores_assignment_on_rediscovery(self):
        with closing(logger.connect(self.directory / "measurements.db")) as db:
            logger.insert(db, {"boot_id": 1, "sequence": 1, "scd_serial": "SENSOR-A"})
        original = self.registry.remember(self.lance, "SENSOR-A")
        self.registry.save_labels(original.device_id, "Old lance", "Lab")
        self.registry.remove(original.device_id)
        self.assertEqual(LanceRegistry(self.directory).list(), [])
        self.assertTrue(self.registry.measurement_path(original).exists())
        other = self.registry.remember(Lance("aaaaaaaaaaaa", "other.local", 80), "SENSOR-A")
        self.assertNotEqual(other.database_name, "measurements.db")
        restored = self.registry.remember(self.lance, "SENSOR-A")
        self.assertEqual(restored.database_name, original.database_name)
        self.assertEqual(restored.name, "Old lance")

    def test_viewer_telemetry_stops_without_writing_measurements(self):
        lance = self.registry.remember(self.lance)
        collector = LanceCollector(lance, self.registry.measurement_path(lance))

        def payload(url):
            self.assertEqual(url, self.lance.url + "/api/current")
            return {"device_id": self.lance.device_id, "measurement": {"boot_id": 4, "sequence": 2, "boxtemp": 24}}

        with patch("logger.lance_collection.logger.fetch_json", side_effect=payload), \
                patch.object(collector.command_event, "wait", side_effect=lambda _: collector.stop()):
            collector.start()
            collector.thread.join(timeout=3)
        self.assertFalse(collector.thread.is_alive())
        with closing(sqlite3.connect(collector.database)) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("measurements", tables)
        self.assertEqual(collector.latest_status(), "Connected")


class ChartNavigationTests(unittest.TestCase):
    def test_home_closes_chart_and_requests_selection_screen(self):
        from matplotlib.backend_bases import MouseEvent
        import matplotlib.pyplot as plt

        def click_home():
            fig = plt.gcf()
            fig.canvas.draw()
            home = next(axis for axis in fig.axes if any(
                text.get_text() == "device overview" for text in axis.texts))
            x, y = home.transAxes.transform((0.5, 0.5))
            for event in ("button_press_event", "button_release_event"):
                fig.canvas.callbacks.process(event, MouseEvent(event, fig.canvas, x, y, button=1))

        with patch.object(viewer, "draw"), patch.object(viewer, "configure_viewer_window", return_value=None), \
                patch.object(plt, "show", side_effect=click_home):
            self.assertTrue(viewer.show_charts(title="Test lance | Lab"))
        self.assertEqual(plt.get_fignums(), [])

    def test_closing_chart_exits_without_reopening_selection(self):
        import matplotlib.pyplot as plt
        with patch.object(viewer, "draw"), patch.object(viewer, "configure_viewer_window", return_value=None), \
                patch.object(plt, "show", side_effect=lambda: plt.close("all")):
            self.assertFalse(viewer.show_charts())


class SelectionEditingTests(unittest.TestCase):
    def test_overview_uses_secondary_monitor_startup_placement(self):
        with self.selection_window() as (selection, _registry):
            with patch("logger.viewer_selection.maximize_on_secondary_monitor") as position, \
                    patch.object(selection.window, "after") as schedule:
                selection._position_on_startup()
                position.assert_called_once_with(selection.window)
                schedule.assert_called_once_with(100, selection._toggle_fullscreen)

    @unittest.skipUnless(sys.platform == "win32", "Windows fullscreen placement")
    def test_fullscreen_stays_on_current_monitor(self):
        with self.selection_window() as (selection, _registry):
            selection.window.update()
            geometry = selection.window.geometry()
            with patch("logger.viewer_selection.current_monitor_bounds",
                       return_value=(-1920, -100, 0, 980)):
                selection._toggle_fullscreen()
            selection.window.update_idletasks()
            self.assertTrue(selection.window.overrideredirect())
            self.assertEqual(selection.window.geometry(), "1920x1080+-1920+-100")
            selection._exit_fullscreen()
            selection.window.update_idletasks()
            self.assertFalse(selection.window.overrideredirect())
            self.assertEqual(selection.window.geometry(), geometry)

    @staticmethod
    @contextmanager
    def selection_window(count=1):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            for number in range(1, count + 1):
                registry.remember(Lance(f"{number:012x}", f"device-{number}.local", 80),
                                  status={"firmware": "3.2.0-esp32c3",
                                          "hardware_profile": "esp32c3_supermini"})
            selection = LanceSelection(directory)
            for callback in selection.window.tk.call("after", "info"):
                selection.window.after_cancel(callback)
            try:
                yield selection, registry
            finally:
                if not selection.stop.is_set():
                    selection._finish()

    def test_device_id_is_selectable_readonly_and_click_copies_mac(self):
        with self.selection_window() as (selection, registry):
            device = registry.list()[0]
            field = selection.overview.columns[device.device_id].identity.device_id
            field.insert(0, "cannot change")
            self.assertEqual(field.get(), "00:00:00:00:00:01")
            field.selection_range(0, "end")
            self.assertTrue(field.selection_present())
            selection._copy_device_id(device.device_id)
            self.assertEqual(selection.window.clipboard_get(), field.get())
            registry.remove(device.device_id)
            selection._refresh_devices()
            self.assertEqual(selection.overview.columns, {})

    def test_title_click_becomes_editor_and_edits_survive_refresh(self):
        with self.selection_window() as (selection, registry):
            device = registry.list()[0]
            header = selection.overview.columns[device.device_id].header
            selection.window.update()
            header.title.event_generate("<Button-1>")
            self.assertTrue(header.editing)
            header.name.set("Lance A")
            header.location.set("Lab")
            selection._refresh_devices()
            self.assertEqual(header.name.get(), "Lance A")
            self.assertTrue(header.commit_edit())
            saved = registry.list()[0]
            self.assertEqual((saved.name, saved.location), ("Lance A", "Lab"))
            self.assertEqual(header.title.cget("text"), "Lance A @ Lab")
            self.assertFalse(header.editing)

    def test_escape_discards_edit_and_failed_save_retains_editor(self):
        with self.selection_window() as (selection, registry):
            header = next(iter(selection.overview.columns.values())).header
            header.begin_edit()
            header.name.set("Discard")
            header.cancel_edit()
            self.assertEqual(registry.list()[0].name, "")
            header.begin_edit()
            header.location.set("Keep")
            with patch.object(selection.registry, "save_labels", side_effect=OSError("Disk full")), \
                    patch("logger.viewer_selection.messagebox.showerror") as error:
                self.assertFalse(header.commit_edit())
                error.assert_called_once()
            self.assertTrue(header.editing)
            self.assertEqual(header.location.get(), "Keep")
            self.assertTrue(header.commit_edit())
            self.assertEqual(registry.list()[0].location, "Keep")

    def test_header_status_shows_last_seen_only_when_offline_and_has_no_link(self):
        from dataclasses import replace
        from datetime import datetime
        from logger.viewer_device_header import format_last_seen
        with self.selection_window() as (selection, registry):
            device = replace(registry.list()[0], last_seen=datetime.now().astimezone().isoformat())
            header = selection.overview.columns[device.device_id].header
            header.update(device, True)
            self.assertEqual(header.status.cget("text"), "online")
            header.update(device, False)
            self.assertEqual(header.status.cget("text"), "last seen " + format_last_seen(device.last_seen))
            self.assertEqual(selection.overview.columns[device.device_id].identity.firmware.cget("text"), "Firmware 3.2.0")
            self.assertFalse(hasattr(header, "address"))

    def test_last_seen_uses_local_date_and_device_id_is_display_only(self):
        from datetime import datetime, timedelta
        from logger.viewer_device_header import format_last_seen, format_device_id, format_firmware
        now = datetime.now().astimezone()
        yesterday = now - timedelta(days=1)
        self.assertEqual(format_last_seen(now.isoformat()), now.strftime("%H:%M:%S"))
        self.assertEqual(format_last_seen(yesterday.isoformat()), yesterday.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual(format_last_seen(""), "-")
        self.assertEqual(format_device_id("b81f3f27ca14"), "B8:1F:3F:27:CA:14")
        self.assertEqual(format_firmware("3.2.1-esp32c3"), "3.2.1")

    def test_remove_button_removes_only_its_offline_column(self):
        with self.selection_window(2) as (selection, registry):
            device = registry.list()[1]
            selection.has_scanned = True
            selection._update_button_state()
            column = selection.overview.columns[device.device_id]
            self.assertEqual(str(column.remove_button["state"]), "normal")
            with patch("logger.viewer_selection.messagebox.askyesno", return_value=True):
                column.remove_button.invoke()
            self.assertEqual(len(registry.list()), 1)
            self.assertNotIn(device.device_id, selection.overview.columns)

    def test_removal_requires_confirmed_offline_status_and_confirmation(self):
        with self.selection_window() as (selection, registry):
            device_id = registry.list()[0].device_id
            with patch("logger.viewer_selection.messagebox.askyesno") as confirm:
                selection._remove(device_id)
                selection.has_scanned = True
                selection.online.add(device_id)
                selection._remove(device_id)
                selection.online.clear()
                selection.scanning = True
                selection._remove(device_id)
                selection.scanning = False
                selection.updating = True
                selection._remove(device_id)
                confirm.assert_not_called()
            selection.updating = False
            with patch("logger.viewer_selection.messagebox.askyesno", return_value=False):
                selection._remove(device_id)
            self.assertEqual(len(registry.list()), 1)

    def test_metadata_is_in_footer_and_redundant_controls_are_absent(self):
        with self.selection_window() as (selection, registry):
            device = registry.list()[0]
            column = selection.overview.columns[device.device_id]
            self.assertIn("Firmware 3.2.0", column.identity.firmware.cget("text"))
            self.assertIn("last seen", column.header.status.cget("text"))
            self.assertFalse(hasattr(column.header, "address"))
            self.assertFalse(hasattr(selection, "tree"))
            self.assertFalse(hasattr(column, "open_button"))
            self.assertEqual(column.identity.frame.grid_info()["row"], 2)
            self.assertEqual(column.identity.separator.cget("text"), " | ")
            self.assertEqual(selection.window.title(), "Device Overview")
            self.assertFalse(hasattr(selection, "heading"))
            selection.window.deiconify()
            selection.window.update()
            controls = selection.theme_button.master
            self.assertFalse(hasattr(selection, "scan_button"))
            self.assertIs(controls, selection.fullscreen_button.master)
            self.assertAlmostEqual(controls.winfo_x() + controls.winfo_width() / 2,
                                   controls.master.winfo_width() / 2, delta=1)
            self.assertGreater(controls.winfo_y(), selection.overview.frame.winfo_y())
            self.assertEqual(str(column.update_button["state"]), "disabled")

    def test_opening_another_device_commits_pending_title_edit(self):
        with self.selection_window(2) as (selection, registry):
            first, second = registry.list()
            header = selection.overview.columns[first.device_id].header
            header.begin_edit()
            header.name.set("Chamber A")
            header.location.set("Lab")
            selection._open_device(second.device_id)
            self.assertEqual(selection.result.device_id, second.device_id)
            saved = {device.device_id: device for device in registry.list()}
            self.assertEqual((saved[first.device_id].name, saved[first.device_id].location), ("Chamber A", "Lab"))

    def test_firmware_button_targets_its_column_and_retains_confirmation(self):
        from types import SimpleNamespace
        with self.selection_window(2) as (selection, registry):
            target = registry.list()[1]
            selection.online = set(selection.devices)
            selection.firmware_versions = {"esp32c3_supermini": (3, 4, 2)}
            selection._update_button_state()
            image = SimpleNamespace(profile="esp32c3_supermini", version="3.4.2", build_id="0123456789ab")
            with patch("logger.viewer_selection.filedialog.askopenfilename", return_value="firmware.bin"), \
                    patch("logger.viewer_selection.firmware_update.read_image", return_value=image), \
                    patch("logger.viewer_selection.messagebox.askyesno", return_value=True) as confirm, \
                    patch("logger.viewer_selection.threading.Thread") as thread:
                selection.overview.columns[target.device_id].update_button.invoke()
            self.assertIn(target.device_id, confirm.call_args.args[1])
            self.assertEqual(thread.call_args.kwargs["args"][0].device_id, target.device_id)
            self.assertTrue(selection.updating)

    def test_action_visibility_depends_on_version_and_offline_status(self):
        with self.selection_window(2) as (selection, registry):
            first, second = registry.list()
            registry.remember(second, status={"firmware": "3.4.2-esp32c3",
                                              "hardware_profile": "esp32c3_supermini"})
            selection.has_scanned = True
            selection.online = {first.device_id}
            selection.firmware_versions = {"esp32c3_supermini": (3, 4, 2)}
            selection._refresh_devices()
            first_column = selection.overview.columns[first.device_id]
            second_column = selection.overview.columns[second.device_id]
            self.assertEqual(first_column.update_button.winfo_manager(), "grid")
            self.assertEqual(first_column.remove_button.winfo_manager(), "")
            self.assertEqual(second_column.update_button.winfo_manager(), "")
            self.assertEqual(second_column.remove_button.winfo_manager(), "grid")
            selection.online.add(second.device_id)
            selection.firmware_versions = {}
            selection._update_button_state()
            self.assertEqual(first_column.update_button.winfo_manager(), "")
            self.assertEqual(second_column.remove_button.winfo_manager(), "")
            self.assertEqual(second_column.buttons.winfo_manager(), "")
