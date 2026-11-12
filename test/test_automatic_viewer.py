import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from logger.control_data import ManualOutputs
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance


def telemetry(enabled=False):
    return {"version": 1, "settings_supported": True, "persisted": True,
            "setpoints": {"co2_ppm": 2500, "humidity_rh": 90},
            "automatic_supported": True, "fogger_enabled": False,
            "enabled": enabled, "reason": "automatic_no_co2_demand",
            "manual": {"supported": True, "active": False, "fan_percent": 0,
                       "fogger_percent": 0, "lease_ms": 0}}


class AutomaticViewerTests(unittest.TestCase):
    def test_parameter_labels_use_reported_gain_and_readable_integral_time(self):
        from logger.viewer_control import pi_parameter_label
        control = telemetry(True)
        control["parameters"] = {"co2_kp": 0.02, "co2_ti_s": 300,
                                 "humidity_kp": 1, "humidity_ti_s": 600}
        self.collector.control.ingest({"control": control})
        state = self.collector.control.snapshot()
        self.assertEqual(pi_parameter_label(state, "co2"),
                         "Kp: 2 %/100 ppm  |  Ti: 5 min")
        self.assertEqual(pi_parameter_label(state, "humidity"),
                         "Kp: 1 %/%RH  |  Ti: 10 min")
        state["parameters"]["co2_ti_s"] = 0
        self.assertEqual(pi_parameter_label(state, "co2"), "Kp: --  |  Ti: --")
        self.assertEqual(self.collector.control.snapshot()["parameters"]["co2_ti_s"], 300)

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.collector = LanceCollector(Lance("b81f3f27f4e0", "test.local", 80),
                                        Path(directory.name) / "data.db")
        self.collector.control.ingest({"control": telemetry()})

    def test_explicit_pi_command_clears_manual_renewal_and_requires_matching_ack(self):
        self.collector.submit_manual(ManualOutputs(True, 22, 0))
        self.collector._manual_lease = ManualOutputs(True, 22, 0)
        self.collector.submit_automatic(True)
        self.assertTrue(self.collector.manual_commands.empty())
        self.assertIsNone(self.collector._manual_lease)
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(telemetry(True)).encode()
        with patch("urllib.request.urlopen", return_value=response) as request:
            self.collector._send_pending_automatic()
            self.assertIn(b"enabled=1", request.call_args.args[0].data)
        self.assertTrue(self.collector.automatic_results.get_nowait()[0])
        self.assertTrue(self.collector.control.snapshot()["enabled"])
        self.collector.submit_automatic(False)
        with patch("urllib.request.urlopen", return_value=response):
            self.collector._send_pending_automatic()
        self.assertFalse(self.collector.automatic_results.get_nowait()[0])

    def test_manual_command_supersedes_pending_pi_and_rejects_locked_fogger(self):
        self.collector.submit_automatic(True)
        self.collector.submit_manual(ManualOutputs(True, 15, 0))
        self.assertTrue(self.collector.automatic_commands.empty())
        with self.assertRaisesRegex(ValueError, "Fogger disabled"):
            self.collector.submit_manual(ManualOutputs(True, 15, 1))

    def test_opening_command_panel_does_not_start_pi(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from logger.viewer_control import CommandPanel
        from logger.viewer_style import DARK_THEME
        figure = Figure(figsize=(12, 8))
        FigureCanvasAgg(figure)
        panel = CommandPanel(figure, figure.add_gridspec(3, 2), self.collector)
        panel.set_visible(True)
        panel.update(DARK_THEME)
        self.assertTrue(self.collector.automatic_commands.empty())
        self.assertTrue(panel.automatic.button.ax.get_visible())
        self.assertEqual(panel.automatic.button.label.get_text(), "Start PI")
        self.assertTrue(any("Humidity PI disabled" in text.get_text()
                            for text in panel.graphs[0].texts))
        self.collector.control.ingest({"control": telemetry(True)})
        panel.update(DARK_THEME)
        self.assertEqual(panel.automatic.button.label.get_text(), "Stop PI")
        panel.set_visible(False)
        self.assertFalse(panel.automatic.button.ax.get_visible())
