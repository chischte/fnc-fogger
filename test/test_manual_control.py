import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from logger.control_data import ManualOutputs
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance
from logger.viewer import LIGHT_THEME
from logger.viewer_control import CommandPanel


def payload(outputs=ManualOutputs(True), enabled=False):
    return {"version": 1, "settings_supported": True, "persisted": False,
            "setpoints": {"co2_ppm": 1000, "humidity_rh": 90}, "enabled": enabled,
            "reason": "manual", "manual": {"supported": True, "active": outputs.active,
            "fan_percent": outputs.fan_percent, "fogger_percent": outputs.fogger_percent}}


class ManualControlTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.collector = LanceCollector(Lance("b81f3f288aec", "test.local", 80),
                                        Path(self.temp.name) / "data.db")
        self.collector.control.ingest({"control": payload()})

    def tearDown(self):
        self.temp.cleanup()

    def response(self, outputs, enabled=False):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(payload(outputs, enabled)).encode()
        return response

    def test_ranges_and_inactive_outputs(self):
        for args in ((True, -1, 0), (True, 0, 101), (True, 1.5, 0),
                     (True, True, 0), (False, 1, 0)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                ManualOutputs(*args)

    def test_acknowledged_commands_renew_but_failed_commands_do_not(self):
        outputs = ManualOutputs(True, 40, 25)
        self.collector.submit_manual(outputs)
        with patch("urllib.request.urlopen", return_value=self.response(outputs)) as request:
            self.collector._send_pending_manual()
            self.assertTrue(self.collector.manual_results.get_nowait()[0])
            self.assertEqual(self.collector.control.snapshot()["manual"], outputs)
            self.assertIn(b"fogger_percent=25", request.call_args.args[0].data)
            self.collector._send_pending_manual()
            self.assertEqual(request.call_count, 2)
            self.assertIn(b"mode=renew", request.call_args.args[0].data)
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.collector._send_pending_manual()
        self.assertIsNone(self.collector._manual_lease)
        with patch("urllib.request.urlopen") as request:
            self.collector._send_pending_manual()
            request.assert_not_called()

    def test_rejects_ack_with_controller_enabled(self):
        outputs = ManualOutputs(True, 50, 50)
        self.collector.submit_manual(outputs)
        with patch("urllib.request.urlopen", return_value=self.response(outputs, enabled=True)):
            self.collector._send_pending_manual()
        self.assertFalse(self.collector.manual_results.get_nowait()[0])
        self.assertIsNone(self.collector._manual_lease)

    def test_no_timeout_firmware_does_not_need_renewal_or_restart_after_disconnect(self):
        outputs = ManualOutputs(True, 40, 25)
        response = self.response(outputs)
        control = payload(outputs)
        control["manual"]["lease_ms"] = 0
        response.__enter__.return_value.read.return_value = json.dumps(control).encode()
        self.collector.submit_manual(outputs)
        with patch("urllib.request.urlopen", return_value=response) as request:
            self.collector._send_pending_manual()
            self.assertTrue(self.collector.manual_results.get_nowait()[0])
            self.assertIsNone(self.collector._manual_lease)
            self.collector._send_pending_manual()
            self.assertEqual(request.call_count, 1)
        self.collector.submit_manual(outputs)
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            self.collector._send_pending_manual()
        self.assertIn("remain active", self.collector.manual_results.get_nowait()[1])
        with patch("urllib.request.urlopen") as request:
            self.collector._send_pending_manual()
            request.assert_not_called()

    def test_stale_lease_never_restarts_outputs(self):
        self.collector._manual_lease = ManualOutputs(True, 100, 100)
        self.collector._manual_renewed_at = 1
        with patch("logger.lance_collection.time.monotonic", return_value=22), \
                patch("urllib.request.urlopen") as request:
            self.collector._send_pending_manual()
            request.assert_not_called()
        self.assertIsNone(self.collector._manual_lease)

    def test_stop_replaces_queued_nonzero_command_and_wakes_collector(self):
        self.collector.submit_manual(ManualOutputs(True, 100, 100))
        self.collector.submit_manual(ManualOutputs(True))
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True))
        self.assertTrue(self.collector.command_event.is_set())
        self.collector.control.disconnected("Offline")
        with self.assertRaises(ValueError):
            self.collector.submit_manual(ManualOutputs(True, 10, 10))

    def test_manual_panel_keeps_setpoints_separate_and_stops_at_zero(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        figure = Figure(figsize=(12, 8))
        FigureCanvasAgg(figure)
        panel = CommandPanel(figure, figure.add_gridspec(3, 2), self.collector)
        panel.set_visible(True)
        panel.update(LIGHT_THEME)
        # A device already in Manual Mode is displayed as such.
        self.assertTrue(panel.manual.selected)
        self.assertFalse(panel.co2.ax.get_visible())
        self.assertTrue(panel.manual.fan.ax.get_visible())
        panel.manual.fan.set_val(40)
        panel.manual.fogger.set_val(25)
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True))
        panel.manual._toggle_output("fan")
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True, 40, 0))
        panel.manual._toggle_output("fogger")
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True, 40, 25))
        panel.manual.fan.set_val(60)
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True, 60, 25))
        panel.manual._toggle_output("fan")
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True, 0, 25))
        self.assertEqual(panel.manual.fan.val, 60)
        panel.manual._stop(None)
        self.assertEqual(self.collector.manual_commands.get_nowait(), ManualOutputs(True))
        panel.set_visible(False)
        self.assertFalse(panel.manual.fan.ax.get_visible())
        self.assertFalse(panel.manual.toggle.ax.get_visible())
