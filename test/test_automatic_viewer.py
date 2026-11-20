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
        self.assertEqual(panel.automatic.button.label.get_text(), "Reset PI")
        self.assertFalse(panel.automatic.button.active)
        self.assertTrue(any("Humidity PI disabled" in text.get_text()
                            for text in panel.graphs[0].texts))
        self.collector.control.ingest({"control": telemetry(True)})
        panel.update(DARK_THEME)
        self.assertEqual(panel.automatic.button.label.get_text(), "Reset PI")
        panel.set_visible(False)
        self.assertFalse(panel.automatic.button.ax.get_visible())

    def test_reset_requires_support_and_acknowledged_counter(self):
        control = telemetry(True)
        control.update(pi_reset_supported=True, pi_reset_count=4)
        self.collector.control.ingest({"control": control})
        self.collector.submit_pi_reset()
        response = MagicMock()
        control["pi_reset_count"] = 5
        response.__enter__.return_value.read.return_value = json.dumps(control).encode()
        with patch("urllib.request.urlopen", return_value=response) as request:
            self.collector._send_pending_automatic()
            self.assertEqual(request.call_args.args[0].data, b"reset=1")
        self.assertTrue(self.collector.automatic_results.get_nowait()[0])
        self.collector.submit_pi_reset()
        with patch("urllib.request.urlopen", return_value=response):
            self.collector._send_pending_automatic()
        self.assertFalse(self.collector.automatic_results.get_nowait()[0])

    def test_leaving_manual_confirms_automatic_default(self):
        control = telemetry(True)
        control["automatic_default"] = True
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(control).encode()
        self.collector.submit_manual(ManualOutputs(False, 0, 0))
        with patch("urllib.request.urlopen", return_value=response):
            self.collector._send_pending_manual()
        self.assertTrue(self.collector.manual_results.get_nowait()[0])
        self.assertTrue(self.collector.control.snapshot()["enabled"])

    def test_emergency_button_switches_label_color_and_command(self):
        from matplotlib.figure import Figure
        from logger.viewer_automatic import AutomaticPanel, EMERGENCY_COLOR, EMERGENCY_TEXT_COLOR
        from logger.viewer_style import DARK_THEME, LIGHT_THEME
        panel = AutomaticPanel(Figure(), self.collector, lambda: None)
        for theme in (DARK_THEME, LIGHT_THEME):
            for trigger in ("humidity_emergency", "emergency_ventilation", "fault"):
                control = telemetry(True)
                control.update(pi_reset_supported=True, exit_emergency_supported=True)
                control[trigger] = True if trigger == "fault" else {"active": True}
                self.collector.control.ingest({"control": control})
                panel.update(self.collector.control.snapshot(), True, False, theme)
                self.assertEqual(panel.button.label.get_text(), "Exit Emergency")
                self.assertEqual(panel.button.color, EMERGENCY_COLOR)
                self.assertEqual(panel.button.label.get_color(), EMERGENCY_TEXT_COLOR)
                self.assertTrue(panel.button.active)
                panel._reset(None)
                self.assertEqual(self.collector.automatic_commands.get_nowait(), "exit_emergency")
                panel._reset(None)
                self.assertTrue(self.collector.automatic_commands.empty())
                self.collector.automatic_results.put((True, "Emergency exited."))
                self.collector.control.ingest({"control": telemetry(True) | {"pi_reset_supported": True}})
                panel.update(self.collector.control.snapshot(), True, False, theme)
                self.assertEqual(panel.button.label.get_text(), "Reset PI")
                self.assertEqual(panel.button.color, theme["selected"])
                panel._reset(None)
                self.assertEqual(self.collector.automatic_commands.get_nowait(), "reset")
                self.collector.automatic_results.put((True, "PI integrals reset."))

    def test_emergency_exit_requires_support_and_confirmation(self):
        control = telemetry(True)
        self.collector.control.ingest({"control": control})
        with self.assertRaisesRegex(ValueError, "firmware update required"):
            self.collector.submit_exit_emergency()
        control.update(exit_emergency_supported=True, fault=True)
        control["emergency_ventilation"] = {"active": True}
        self.collector.control.ingest({"control": control})
        response = MagicMock()
        for emergency_active in (True, False):
            self.collector.submit_exit_emergency()
            control["fault"] = emergency_active
            control["emergency_ventilation"]["active"] = emergency_active
            response.__enter__.return_value.read.return_value = json.dumps(control).encode()
            with patch("urllib.request.urlopen", return_value=response) as request:
                self.collector._send_pending_automatic()
                self.assertEqual(request.call_args.args[0].data, b"exit_emergency=1")
            self.assertEqual(self.collector.automatic_results.get_nowait()[0], not emergency_active)
