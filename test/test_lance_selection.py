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

    def test_collection_uses_selected_device_and_stops_cleanly(self):
        lance = self.registry.remember(self.lance)
        collector = LanceCollector(lance, self.registry.measurement_path(lance))

        def payload(url):
            self.assertEqual(url, self.lance.url + "/api/current")
            return {"boot_id": 4, "sequence": 2, "boxtemp": 24}

        with patch("logger.lance_collection.logger.fetch_json", side_effect=payload), \
                patch.object(collector.stop_event, "wait", side_effect=lambda _: collector.stop()):
            collector.start()
            collector.thread.join(timeout=3)
        self.assertFalse(collector.thread.is_alive())
        frame = viewer_data.load_data(collector.database, collector.database.with_suffix(".csv"))
        self.assertEqual(frame["temp_box_c"].tolist(), [24])


class ChartNavigationTests(unittest.TestCase):
    def test_home_closes_chart_and_requests_selection_screen(self):
        from matplotlib.backend_bases import MouseEvent
        import matplotlib.pyplot as plt

        def click_home():
            fig = plt.gcf()
            fig.canvas.draw()
            home = next(axis for axis in fig.axes if any(
                text.get_text() == "Home" for text in axis.texts))
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
                self.assertEqual(values["firmware"], "3.2.0-esp32c3")
                self.assertEqual(values["hardware"], "esp32c3_supermini")
                self.assertEqual(values["build"], "0123456789ab")
                self.assertEqual(values["status"], "Offline")
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
