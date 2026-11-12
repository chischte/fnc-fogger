import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from logger.control_data import Setpoints
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance
from logger.viewer_control import CommandPanel
from logger.viewer_style import DARK_THEME


class SetpointAutosaveTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.collector = LanceCollector(Lance("b81f3f27f4e0", "test.local", 80),
                                        Path(directory.name) / "data.db")
        self.confirm(2000)
        figure = Figure(figsize=(12, 8))
        FigureCanvasAgg(figure)
        self.panel = CommandPanel(figure, figure.add_gridspec(3, 2), self.collector)
        self.panel.set_visible(True)
        self.panel.update(DARK_THEME)
        clock_patch = patch("logger.viewer_control.time.monotonic", return_value=100)
        self.clock = clock_patch.start()
        self.addCleanup(clock_patch.stop)

    def confirm(self, co2):
        self.collector.control.ingest({"control": {
            "version": 1, "settings_supported": True, "persisted": True,
            "setpoints": {"co2_ppm": co2, "humidity_rh": 90}, "enabled": False}})

    def edit(self, co2):
        self.panel.co2.set_val(co2)
        self.panel._edited(None)

    def tick(self, seconds):
        self.clock.return_value = seconds
        self.panel._maybe_save(self.collector.control.snapshot())

    def test_repeated_changes_send_only_latest_after_three_idle_seconds(self):
        self.edit(1500)
        self.clock.return_value = 102
        self.edit(1000)
        self.tick(104.9)
        self.assertTrue(self.collector.commands.empty())
        self.tick(105)
        self.assertEqual(self.collector.commands.get_nowait(), Setpoints(1000, 90))
        self.assertTrue(self.panel.pending)
        self.assertFalse(hasattr(self.panel, "save"))
        self.assertEqual(self.collector.control.snapshot()["setpoints"], Setpoints(2000, 90))

    def test_edits_during_upload_survive_older_acknowledgement(self):
        self.edit(1500)
        self.tick(103)
        self.assertEqual(self.collector.commands.get_nowait(), Setpoints(1500, 90))
        self.clock.return_value = 104
        self.edit(1000)
        self.confirm(1500)
        self.collector.command_results.put((True, "Saved"))
        self.panel._read_results()
        self.assertTrue(self.panel.dirty)
        self.assertEqual(self.panel.co2.value, 1000)
        self.tick(106)
        self.assertTrue(self.collector.commands.empty())
        self.tick(107)
        self.assertEqual(self.collector.commands.get_nowait(), Setpoints(1000, 90))
        self.confirm(1000)
        self.collector.command_results.put((True, "Saved"))
        self.panel._read_results()
        self.assertFalse(self.panel.dirty)

    def test_offline_changes_wait_and_failed_upload_retries_without_losing_draft(self):
        self.edit(1500)
        self.collector.control.disconnected("Offline")
        self.tick(103)
        self.assertTrue(self.collector.commands.empty())
        self.assertTrue(self.panel.dirty)
        self.confirm(2000)
        self.tick(104)
        self.collector.commands.get_nowait()
        self.collector.command_results.put((False, "Unconfirmed"))
        self.panel._read_results()
        self.tick(108)
        self.assertTrue(self.collector.commands.empty())
        self.tick(109)
        self.assertEqual(self.collector.commands.get_nowait(), Setpoints(1500, 90))

    def test_returning_to_confirmed_values_avoids_unnecessary_flash_write(self):
        self.edit(1500)
        self.edit(2000)
        self.tick(103)
        self.assertTrue(self.collector.commands.empty())
        self.assertFalse(self.panel.dirty)
