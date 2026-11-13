import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from matplotlib.figure import Figure

from logger.cyclic_mist import CyclicMistSettings, MIST_PAUSE_LEVELS
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance
from logger.viewer_control import CommandPanel
from logger.viewer_style import DARK_THEME


def control(values=CyclicMistSettings(), enabled=True):
    return {"version": 1, "persisted": True, "settings_supported": True,
            "setpoints": {"co2_ppm": 1500, "humidity_rh": 99},
            "enabled": enabled, "fault": False,
            "manual": {"supported": True, "active": False, "fan_percent": 0, "fogger_percent": 0},
            "cyclic_mist": {"supported": True, "enabled": values.enabled,
                            "mist_time_min": values.mist_time_min,
                            "mist_pause_min": values.mist_pause_min,
                            "misting": values.enabled, "remaining_ms": 60000}}


class CyclicMistTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.collector = LanceCollector(Lance("b81f3f27f4e0", "test.local", 80),
                                        Path(directory.name) / "device.db")
        self.collector.control.ingest({"control": control()})

    @staticmethod
    def response(values):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(control(values)).encode()
        return response

    def test_validated_minute_steps_and_bounds(self):
        self.assertEqual(MIST_PAUSE_LEVELS, tuple(range(10, 61, 5)))
        for time in (1, 10):
            for pause in (10, 15, 60):
                self.assertEqual(CyclicMistSettings(True, time, pause).mist_time_min, time)
        for args in ((True, 0, 10), (True, 11, 10), (True, 1, 11), (True, 1, 61),
                     (True, 1, 1), (True, 1.5, 10), (1, 1, 10), (True, True, 10)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                CyclicMistSettings(*args)

    def test_zero_on_is_off_and_increasing_it_activates_the_cycle(self):
        self.assertEqual(CyclicMistSettings(False, 0, 10).fields()["enabled"], 0)
        figure = Figure(figsize=(12, 9))
        panel = CommandPanel(figure, figure.add_gridspec(3, 2), self.collector)
        panel.set_visible(True)
        panel.update(DARK_THEME)
        self.assertEqual(panel.cyclic.mist_time.value, 0)
        panel.cyclic.mist_time._step(1)
        self.assertEqual(self.collector.cyclic_mist_commands.get_nowait(), CyclicMistSettings(True, 1, 10))

    def test_latest_command_is_sent_and_device_confirmation_is_required(self):
        self.collector.submit_cyclic_mist(CyclicMistSettings(True, 1, 10))
        requested = CyclicMistSettings(True, 2, 15)
        self.collector.submit_cyclic_mist(requested)
        with patch("urllib.request.urlopen", return_value=self.response(requested)) as request:
            self.collector._send_pending_cyclic_mist()
        sent = request.call_args.args[0]
        self.assertTrue(sent.full_url.endswith("/api/control/cyclic-mist"))
        self.assertIn(b"enabled=1", sent.data)
        self.assertIn(b"mist_time_min=2", sent.data)
        self.assertIn(b"mist_pause_min=15", sent.data)
        self.assertTrue(self.collector.cyclic_mist_results.get_nowait()[0])
        self.assertEqual(self.collector.control.snapshot()["cyclic_mist"]["mist_pause_min"], 15)
        self.collector.submit_cyclic_mist(CyclicMistSettings(False, 2, 15))
        with patch("urllib.request.urlopen", return_value=self.response(requested)):
            self.collector._send_pending_cyclic_mist()
        self.assertFalse(self.collector.cyclic_mist_results.get_nowait()[0])
        self.assertTrue(self.collector.control.snapshot()["cyclic_mist"]["enabled"])

    def test_offline_and_unsupported_devices_do_not_send_commands(self):
        self.collector.control.disconnected("offline")
        with self.assertRaises(ValueError):
            self.collector.submit_cyclic_mist(CyclicMistSettings(True))
        legacy = control()
        legacy.pop("cyclic_mist")
        self.collector.control.ingest({"control": legacy})
        with self.assertRaises(ValueError):
            self.collector.submit_cyclic_mist(CyclicMistSettings(True))

    def test_panel_restores_device_values_and_sends_without_apply(self):
        saved = CyclicMistSettings(True, 3, 20)
        self.collector.control.ingest({"control": control(saved)})
        figure = Figure(figsize=(12, 9))
        panel = CommandPanel(figure, figure.add_gridspec(3, 2), self.collector)
        panel.set_visible(True)
        panel.update(DARK_THEME)
        self.assertEqual(panel.humidity.levels[-1], 99)
        self.assertTrue(panel.cyclic.enabled)
        self.assertEqual(panel.cyclic.label.get_text(), "Cyclic Mist [min]")
        self.assertFalse(hasattr(panel.cyclic, "toggle"))
        self.assertEqual(panel.cyclic.mist_time.label.get_ha(), "center")
        self.assertEqual(panel.cyclic.mist_pause.label.get_ha(), "center")
        self.assertFalse(panel.cyclic.mist_time.value_text.get_visible())
        self.assertFalse(panel.cyclic.mist_pause.value_text.get_visible())
        self.assertTrue(panel.cyclic.frame.get_visible())
        self.assertLess(panel.cyclic.frame.get_y() + panel.cyclic.frame.get_height(),
                               panel.frame.get_y())
        self.assertEqual(panel.cyclic.mist_time.label.get_text(), "ON 3")
        self.assertEqual(panel.cyclic.mist_pause.label.get_text(), "OFF 20")
        self.assertEqual(panel.cyclic.mist_time.value, 3)
        panel.cyclic.mist_time._step(1)
        self.assertEqual(self.collector.cyclic_mist_commands.get_nowait(), CyclicMistSettings(True, 4, 20))
        for expected in (3, 2, 1, 0):
            panel.cyclic.mist_time._step(-1)
            self.assertEqual(self.collector.cyclic_mist_commands.get_nowait(),
                             CyclicMistSettings(expected > 0, expected, 20))
        for field in (panel.cyclic.mist_time, panel.cyclic.mist_pause):
            self.assertTrue(field.ax.get_visible())
        box = panel.editor.get_position()
        row = [panel.cyclic.label_axis.get_position(), panel.cyclic.mist_time.ax.get_position(),
               panel.cyclic.mist_pause.ax.get_position()]
        self.assertTrue(all(abs(bounds.y0 - row[0].y0) < 1e-9 for bounds in row))
        self.assertLess(row[0].x1, row[1].x0)
        self.assertLess(row[1].x1, row[2].x0)
        self.assertAlmostEqual(row[0].x0, panel.co2.ax.get_position().x0)
        for group, button in ((row[1], panel.co2.minus), (row[2], panel.co2.plus)):
            self.assertAlmostEqual(group.x0, button.ax.get_position().x0)
            self.assertAlmostEqual(group.width, button.ax.get_position().width)
        panel.set_visible(False)
        self.assertFalse(panel.cyclic.label_axis.get_visible())

    def test_saved_cycle_can_be_disabled_even_during_a_pi_fault(self):
        saved = CyclicMistSettings(True, 3, 20)
        faulted = control(saved)
        faulted["fault"] = True
        self.collector.control.ingest({"control": faulted})
        figure = Figure(figsize=(12, 9))
        panel = CommandPanel(figure, figure.add_gridspec(3, 2), self.collector)
        panel.set_visible(True)
        panel.update(DARK_THEME)
        self.assertTrue(panel.cyclic.mist_time.active)
        for _ in range(3):
            panel.cyclic.mist_time._step(-1)
        self.assertEqual(self.collector.cyclic_mist_commands.get_nowait(), CyclicMistSettings(False, 0, 20))

    def test_device_state_can_resume_after_offline_without_enabling_from_viewer(self):
        saved = CyclicMistSettings(True, 10, 60)
        self.collector.control.ingest({"control": control(saved)})
        self.collector.control.disconnected("offline")
        self.assertTrue(self.collector.control.snapshot()["cyclic_mist"]["enabled"])
        self.collector.control.ingest({"control": control(saved)})
        self.assertTrue(self.collector.cyclic_mist_commands.empty())


if __name__ == "__main__":
    unittest.main()
