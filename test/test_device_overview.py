import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from logger import logger
from logger.lance_registry import Lance, LanceRegistry
from logger.overview_data import load_overview_history, overview_time
from logger.viewer_selection import LanceSelection


class OverviewHistoryTests(unittest.TestCase):
    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "missing.db"
            with self.assertRaises(sqlite3.OperationalError):
                load_overview_history(database, overview_time())
            self.assertFalse(database.exists())

    def test_recent_history_is_isolated_readonly_and_uses_corrected_humidity(self):
        with tempfile.TemporaryDirectory() as folder:
            end = overview_time().replace(microsecond=0)
            paths = [Path(folder) / f"{index}.db" for index in range(2)]
            for index, database in enumerate(paths):
                with closing(logger.connect(database)) as db:
                    for sequence, age in [(1, 31), (2, 2)]:
                        logger.insert(db, {"boot_id": 1, "sequence": sequence,
                                           "co2": 700 + index * 100, "humidity": 89,
                                           "humidity_offset_rh": 1, "boxtemp": 24})
                        db.execute("UPDATE measurements SET device_time=? WHERE sequence=?",
                                   ((end - timedelta(minutes=age)).isoformat(), sequence))
                    db.commit()
                frame = load_overview_history(database, end)
                self.assertEqual(frame["co2_ppm"].tolist(), [700 + index * 100])
                self.assertEqual(frame["humidity_corrected_rh"].tolist(), [90])
                with closing(sqlite3.connect(database)) as db:
                    self.assertEqual(db.execute("SELECT COUNT(*) FROM measurements").fetchone()[0], 2)


class OverviewWindowTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        registry = LanceRegistry(self.folder.name)
        self.devices = [registry.remember(Lance(f"{number:012x}", f"device-{number}.local", 80))
                        for number in (1, 2)]
        registry.save_labels(self.devices[1].device_id, "Fogger", "Lab")
        self.selection = LanceSelection(self.folder.name)
        # Exercise the UI without network discovery or a running logger.
        for callback in self.selection.window.tk.call("after", "info"):
            self.selection.window.after_cancel(callback)

    def tearDown(self):
        if self.selection.window.winfo_exists():
            self.selection._finish()
        self.folder.cleanup()

    def test_plot_click_opens_its_device_instead_of_selected_row(self):
        target = self.devices[1].device_id
        column = self.selection.overview.columns[target]
        with patch.object(self.selection, "_finish"):
            column._click(SimpleNamespace(button=1, inaxes=column.axes[1]))
        self.assertEqual(self.selection.result.device_id, target)

    def test_exactly_three_main_lines_keep_fixed_scales_after_refresh(self):
        column = self.selection.overview.columns[self.devices[0].device_id]
        with tempfile.TemporaryDirectory() as folder:
            database = Path(folder) / "data.db"
            with closing(logger.connect(database)) as db:
                logger.insert(db, {"boot_id": 1, "sequence": 1, "co2": 20000,
                                   "humidity": 5, "boxtemp": 50, "scd_humidity": 10,
                                   "ambient_temperature": 15, "ambient_humidity": 30})
            end = overview_time()
            column.update_history(load_overview_history(database, end), end)
        self.assertEqual([axis.get_ylim() for axis in column.axes], [(85, 100), (0, 15000), (20, 30)])
        self.assertEqual([len(axis.lines) for axis in column.axes], [1, 1, 1])
        self.assertTrue(all(not axis.get_navigate() for axis in column.axes))
        self.assertTrue(all(line.get_linestyle() == "-" for line in column.lines))
        column.canvas.draw()
        self.assertTrue(all(axis.get_xticklabels() for axis in column.axes))
        for axis in column.axes:
            bounds = axis.get_position()
            self.assertAlmostEqual((bounds.x0 + bounds.x1) / 2, 0.5)
            title_center = axis.title.get_transform().transform(axis.title.get_position())[0]
            self.assertAlmostEqual(title_center, column.figure.bbox.width / 2, delta=1)

    def test_theme_fullscreen_and_label_edits_preserve_management(self):
        target = self.devices[1].device_id
        column = self.selection.overview.columns[target]
        self.assertEqual(column.title.cget("text"), "fogger @ lab")
        self.assertTrue(self.selection.dark_mode)
        self.assertEqual(self.selection.theme_button.cget("text"), "Light Mode")
        self.selection._toggle_theme()
        self.assertFalse(self.selection.dark_mode)
        self.assertEqual(self.selection.theme_button.cget("text"), "Dark Mode")
        self.selection._toggle_fullscreen()
        self.assertTrue(self.selection.fullscreen)
        self.selection._exit_fullscreen()
        self.assertFalse(self.selection.fullscreen)
        self.selection.registry.save_labels(target, "New name", "New place")
        self.selection._refresh_devices()
        self.assertEqual(column.title.cget("text"), "new name @ new place")
        self.assertIn("Firmware", column.identity.firmware.cget("text"))
        self.assertEqual(column.update_button.cget("text"), "Update Firmware")

    def test_update_blocks_navigation_and_removal_destroys_only_target_column(self):
        target = self.devices[1].device_id
        column = self.selection.overview.columns[target]
        self.selection.updating = True
        self.selection._update_button_state()
        self.assertFalse(column.header.edit_enabled)
        self.selection._open_device(target)
        self.assertIsNone(self.selection.result)
        self.selection.registry.remove(target)
        self.selection._refresh_devices()
        self.assertNotIn(target, self.selection.overview.columns)
        self.assertIn(self.devices[0].device_id, self.selection.overview.columns)

    def test_seven_devices_keep_three_axes_each_and_independent_navigation(self):
        for number in range(3, 8):
            self.selection.registry.remember(Lance(f"{number:012x}", f"device-{number}.local", 80))
        self.selection._refresh_devices()
        self.assertEqual(len(self.selection.overview.columns), 7)
        self.assertTrue(all(len(column.axes) == 3 for column in self.selection.overview.columns.values()))
        target = f"{7:012x}"
        with patch.object(self.selection, "_finish"):
            column = self.selection.overview.columns[target]
            column._click(SimpleNamespace(button=1, inaxes=column.axes[0]))
        self.assertEqual(self.selection.result.device_id, target)


if __name__ == "__main__":
    unittest.main()
