import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from logger import logger, viewer, viewer_data
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance, LanceRegistry


class LanceRegistryTests(unittest.TestCase):
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
                text.get_text() == "Lance Selection" for text in axis.texts))
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
    def test_device_id_is_selectable_readonly_and_click_copies_mac(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            device = registry.remember(Lance("b81f3f288aec", "test.local", 80))
            selection = LanceSelection(directory)
            try:
                field = selection.device_id_fields[device.device_id]
                field.insert(0, "cannot change")
                self.assertEqual(field.get(), "B8:1F:3F:28:8A:EC")
                field.selection_range(0, "end")
                self.assertTrue(field.selection_present())
                selection._copy_device_id(device.device_id)
                self.assertEqual(selection.window.clipboard_get(), "B8:1F:3F:28:8A:EC")
                self.assertEqual(registry.list()[0].device_id, "b81f3f288aec")
                self.assertEqual(field.cget("readonlybackground"), "#3b8c62")
                registry.remove(device.device_id)
                selection._refresh_rows()
                self.assertEqual(selection.device_id_fields, {})
            finally:
                selection._finish()

    def test_inline_edits_survive_refresh_and_save_on_selection_change(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            first = registry.remember(Lance("111111111111", "one.local", 80))
            second = registry.remember(Lance("222222222222", "two.local", 80))
            selection = LanceSelection(directory)
            try:
                selection._edit_cell(first.device_id, "name")
                selection.cell_editor.insert(0, "Lance A")
                selection._refresh_rows()
                self.assertEqual(selection.cell_editor.get(), "Lance A")
                selection._commit_edit()
                selection._edit_cell(first.device_id, "location")
                selection.cell_editor.insert(0, "Lab")
                selection.tree.selection_set(second.device_id)
                selection._select()
                saved = {item.device_id: item for item in registry.list()}
                self.assertEqual((saved[first.device_id].name, saved[first.device_id].location),
                                 ("Lance A", "Lab"))
                self.assertEqual(saved[second.device_id].name, "")
                self.assertIsNone(selection.cell_editor)
            finally:
                selection._finish()

    def test_escape_discards_edit_and_failed_save_retains_editor(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            lance = registry.remember(Lance("111111111111", "one.local", 80))
            selection = LanceSelection(directory)
            try:
                selection._edit_cell(lance.device_id, "name")
                selection.cell_editor.insert(0, "Discard this")
                selection._cancel_edit()
                selection._save_labels()
                self.assertEqual(registry.list()[0].name, "")
                selection._edit_cell(lance.device_id, "location")
                selection.cell_editor.insert(0, "Keep this")
                with patch.object(selection.registry, "save_labels", side_effect=OSError("Disk full")), \
                        patch("logger.viewer_selection.messagebox.showerror") as error:
                    self.assertFalse(selection._save_labels())
                    error.assert_called_once()
                self.assertEqual(selection.cell_editor.get(), "Keep this")
                self.assertTrue(selection._save_labels())
                self.assertEqual(registry.list()[0].location, "Keep this")
            finally:
                selection._finish()

    def test_click_address_opens_correct_device_in_browser(self):
        from types import SimpleNamespace
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            lance = registry.remember(Lance("111111111111", "one.local", 8080))
            selection = LanceSelection(directory)
            try:
                for callback in selection.window.tk.call("after", "info"):
                    selection.window.after_cancel(callback)
                selection.window.deiconify()
                selection.window.update()
                selection.tree.see(lance.device_id)
                selection.tree.update_idletasks()
                selection.tree.xview_moveto(1)
                selection.tree.update_idletasks()
                x, y, width, height = selection.tree.bbox(lance.device_id, "address")
                event = SimpleNamespace(x=x + width // 2, y=y + height // 2)
                with patch("logger.viewer_selection.webbrowser.open", return_value=True) as browser:
                    selection._click_address(event)
                    browser.assert_called_once_with("http://one.local:8080", new=2)
                    browser.reset_mock()
                    link = selection.address_links[lance.device_id]
                    self.assertEqual(link.cget("foreground"), "white")
                    self.assertEqual(link.cget("background"), "#3b8c62")
                    self.assertIn("underline", link.cget("font"))
                    link.event_generate("<ButtonRelease-1>")
                    browser.assert_called_once_with("http://one.local:8080", new=2)
            finally:
                selection._finish()

    def test_last_seen_uses_local_date_and_device_id_is_display_only(self):
        from datetime import datetime, timedelta
        from logger.viewer_selection import LanceSelection
        now = datetime.now().astimezone()
        yesterday = now - timedelta(days=1)
        self.assertEqual(LanceSelection._format_last_seen(now.isoformat()), now.strftime("%H:%M:%S"))
        self.assertEqual(LanceSelection._format_last_seen(yesterday.isoformat()),
                         yesterday.strftime("%Y-%m-%d %H:%M:%S"))
        self.assertEqual(LanceSelection._format_last_seen(""), "-")
        self.assertEqual(LanceSelection._format_device_id("b81f3f27ca14"), "B8:1F:3F:27:CA:14")
        self.assertEqual(LanceSelection._format_firmware("3.2.1-esp32c3"), "3.2.1")

    def test_remove_offline_device_and_last_row_clears_selection(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            lance = registry.remember(Lance("111111111111", "one.local", 80))
            selection = LanceSelection(directory)
            try:
                selection._select()
                selection.has_scanned = True
                selection._update_button_state()
                self.assertEqual(str(selection.remove_button["state"]), "normal")
                with patch("logger.viewer_selection.messagebox.askyesno", return_value=True):
                    selection._remove()
                self.assertEqual(registry.list(), [])
                self.assertFalse(selection.tree.exists(lance.device_id))
                self.assertIsNone(selection.selected_id)
                self.assertEqual(selection.name.get(), "")
                self.assertEqual(str(selection.open_button["state"]), "disabled")
                self.assertEqual(str(selection.remove_button["state"]), "disabled")
            finally:
                selection._finish()

    def test_removal_requires_confirmed_offline_status_and_confirmation(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            lance = registry.remember(Lance("111111111111", "one.local", 80))
            selection = LanceSelection(directory)
            try:
                selection._select()
                with patch("logger.viewer_selection.messagebox.askyesno") as confirm:
                    selection._remove()
                    selection.has_scanned = True
                    selection.online.add(lance.device_id)
                    selection._remove()
                    selection.online.clear()
                    selection.scanning = True
                    selection._remove()
                    selection.scanning = False
                    selection.updating = True
                    selection._remove()
                    confirm.assert_not_called()
                selection.updating = False
                with patch("logger.viewer_selection.messagebox.askyesno", return_value=False):
                    selection._remove()
                self.assertEqual(len(registry.list()), 1)
            finally:
                selection._finish()

    def test_overview_displays_persisted_firmware_for_offline_devices(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            lance = Lance("111111111111", "one.local", 80)
            registry.remember(lance, status={"firmware": "3.2.0-esp32c3",
                                            "hardware_profile": "esp32c3_supermini",
                                            "build_id": "0123456789ab"})
            selection = LanceSelection(directory)
            try:
                row = selection.tree.item(lance.device_id, "values")
                columns = selection.tree["columns"]
                values = dict(zip(columns, row))
                self.assertEqual(values["firmware"], "3.2.0")
                self.assertNotIn("hardware", values)
                self.assertNotIn("build", values)
                self.assertEqual(values["device_id"], "11:11:11:11:11:11")
                self.assertEqual(values["status"], "offline")
                for column in columns:
                    self.assertEqual(str(selection.tree.column(column, "anchor")),
                                     "w" if column == "name" else "center")
                self.assertNotEqual(values["last_seen"], "-")
                self.assertEqual(str(selection.update_button["state"]), "disabled")
            finally:
                selection._finish()

    def test_switching_rows_preserves_edits_and_open_returns_selected_lance(self):
        from logger.viewer_selection import LanceSelection
        with tempfile.TemporaryDirectory() as directory:
            registry = LanceRegistry(directory)
            first = registry.remember(Lance("111111111111", "one.local", 80))
            second = registry.remember(Lance("222222222222", "two.local", 80))
            selection = LanceSelection(directory)
            try:
                selection.tree.selection_set(first.device_id)
                selection._select()
                selection.name.set("Chamber A")
                selection.location.set("Lab")
                selection.tree.selection_set(second.device_id)
                selection._select()
                selection.tree.selection_set(first.device_id)
                selection._select()
                self.assertEqual(selection.name.get(), "Chamber A")
                self.assertEqual(selection.location.get(), "Lab")
                selection._open()
                self.assertEqual(selection.result.device_id, first.device_id)
                self.assertEqual(selection.result.name, "Chamber A")
                saved = {item.device_id: item for item in LanceRegistry(directory).list()}
                self.assertIn(second.device_id, saved)
                self.assertEqual(saved[first.device_id].location, "Lab")
            finally:
                if not selection.stop.is_set():
                    selection._finish()
