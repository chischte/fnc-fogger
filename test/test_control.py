import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from logger import logger, viewer
from logger.control_data import ControlMonitor, MAX_CONTROL_SAMPLES, Setpoints, SetpointRepository
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance


def control_payload(sequence=1, co2=1200, humidity=92, persisted=True, enabled=False, boot=1):
    return {"measurement": {"boot_id": boot, "sequence": sequence}, "control": {
        "version": 1, "settings_supported": True, "persisted": persisted,
        "setpoints": {"co2_ppm": co2, "humidity_rh": humidity}, "enabled": enabled,
        "humidity": {"p": 10, "i": 20, "sum": 30},
        "co2": {"p": 15, "i": 25, "sum": 40}}}


class ControlDataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / "measurements.db"
        self.monitor = ControlMonitor(self.database)

    def tearDown(self):
        self.temp.cleanup()

    def test_only_confirmed_setpoints_survive_restart(self):
        self.monitor.ingest(control_payload(persisted=False))
        self.assertIsNone(SetpointRepository(self.database).load())
        self.monitor.ingest(control_payload(persisted=True))
        reopened = ControlMonitor(self.database).snapshot()
        self.assertEqual(reopened["setpoints"], Setpoints(1200, 92))
        self.assertEqual(reopened["samples"], [])
        self.assertFalse(reopened["online"])
        with closing(sqlite3.connect(self.database)) as db:
            columns = {row[1] for row in db.execute("PRAGMA table_info(control_setpoints)")}
        self.assertEqual(columns, {"id", "co2_ppm", "humidity_rh", "confirmed_at"})

    def test_telemetry_is_deduplicated_bounded_and_reset_on_new_boot(self):
        self.monitor.ingest(control_payload())
        self.monitor.ingest(control_payload())
        self.assertEqual(len(self.monitor.snapshot()["samples"]), 1)
        with patch.object(self.monitor.repository, "save"):
            for sequence in range(2, MAX_CONTROL_SAMPLES + 5):
                self.monitor.ingest(control_payload(sequence))
        self.assertEqual(len(self.monitor.snapshot()["samples"]), MAX_CONTROL_SAMPLES)
        self.monitor.ingest(control_payload(1, boot=2))
        self.assertEqual(len(self.monitor.snapshot()["samples"]), 1)

    def test_acknowledgement_does_not_clear_live_history(self):
        self.monitor.ingest(control_payload())
        self.monitor.ingest({"control": control_payload(co2=1500)["control"]})
        self.assertEqual(len(self.monitor.snapshot()["samples"]), 1)
        self.assertEqual(self.monitor.snapshot()["setpoints"].co2_ppm, 1500)

    def test_old_firmware_and_offline_preserve_local_setpoints(self):
        self.monitor.ingest(control_payload())
        self.monitor.ingest({"measurement": {"boot_id": 1, "sequence": 2}})
        self.assertFalse(self.monitor.snapshot()["supported"])
        self.monitor.disconnected("Offline")
        self.assertFalse(self.monitor.snapshot()["online"])
        self.assertEqual(self.monitor.snapshot()["setpoints"], Setpoints(1200, 92))

    def test_setpoint_ranges_and_nonfinite_values(self):
        for co2, humidity in ((-1, 90), (20001, 90), (1000, 69), (1000, 101),
                              (float("nan"), 90), (1000, float("inf"))):
            with self.subTest(co2=co2, humidity=humidity), self.assertRaises(ValueError):
                Setpoints(co2, humidity)
        self.assertEqual(Setpoints(1200, 92.123).humidity_rh, 92.1)

    def test_commands_save_only_after_durable_device_ack(self):
        collector = LanceCollector(Lance("14c19f5cc8b4", "test.local", 80), self.database)
        collector.control.ingest(control_payload())
        collector.submit_setpoints(Setpoints(1500, 93))
        with patch("urllib.request.urlopen", side_effect=OSError("offline")):
            collector._send_pending_setpoints()
        self.assertFalse(collector.command_results.get_nowait()[0])
        self.assertEqual(collector.control.repository.load(), Setpoints(1200, 92))
        collector.submit_setpoints(Setpoints(1500, 93))
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            control_payload(co2=1500, humidity=93)["control"]).encode()
        with patch("urllib.request.urlopen", return_value=response) as request:
            collector._send_pending_setpoints()
        self.assertEqual(request.call_args.args[0].get_method(), "POST")
        self.assertTrue(collector.command_results.get_nowait()[0])
        self.assertEqual(collector.control.repository.load(), Setpoints(1500, 93))

    def test_unpersisted_ack_is_not_reported_as_success(self):
        collector = LanceCollector(Lance("14c19f5cc8b4", "test.local", 80), self.database)
        collector.control.ingest(control_payload())
        collector.submit_setpoints(Setpoints(1500, 93))
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(
            control_payload(co2=1500, humidity=93, persisted=False)["control"]).encode()
        with patch("urllib.request.urlopen", return_value=response):
            collector._send_pending_setpoints()
        self.assertFalse(collector.command_results.get_nowait()[0])
        self.assertEqual(collector.control.repository.load(), Setpoints(1200, 92))


class CommandLayoutTests(unittest.TestCase):
    def test_mode_toggle_uses_two_columns_and_restores_full_width(self):
        import matplotlib.pyplot as plt
        from matplotlib.backend_bases import MouseEvent

        def exercise():
            fig = plt.gcf()
            fig.canvas.draw()
            charts = [axis for axis in fig.axes if axis.get_title() in
                      ("Humidity [%RH]", "CO2 [ppm]", "Temperature [°C]")]
            button_axis = next(axis for axis in fig.axes if any(
                text.get_text() == "Command mode" for text in axis.texts))
            x, y = button_axis.transAxes.transform((0.5, 0.5))
            for _ in range(2):
                for event in ("button_press_event", "button_release_event"):
                    fig.canvas.callbacks.process(event, MouseEvent(event, fig.canvas, x, y, button=1))
                fig.canvas.draw()
                if button_axis.texts[0].get_text() == "View mode":
                    for axis in charts:
                        self.assertLessEqual(axis.get_position().x1, 0.51)
                    pi_axes = [axis for axis in fig.axes if axis.get_title().endswith("PI [%]")]
                    self.assertEqual(len(pi_axes), 2)
                    self.assertTrue(all(axis.get_ylim() == (-100, 100) for axis in pi_axes))
                    for axis in pi_axes:
                        self.assertEqual(axis.spines["bottom"].get_position(), ("data", 0))
                        self.assertEqual([line.get_linestyle() for line in axis.lines], [":", "--", "-"])
                        self.assertEqual([text.get_text() for text in axis.get_legend().get_texts()],
                                         ["P", "I", "SUM"])
                        color = "#2878a8" if axis.get_title().startswith("Humidity") else "#7b2cbf"
                        self.assertTrue(all(line.get_color() == color for line in axis.lines))
                else:
                    self.assertTrue(all(axis.get_position().x1 > 0.9 for axis in charts))
            plt.close(fig)

        import pandas as pd
        frame = pd.DataFrame({"timestamp": pd.date_range("2026-11-07", periods=3, freq="min"),
                              "humidity_corrected_rh": [90, 91, 92], "co2_ppm": [1300, 1250, 1200],
                              "temp_box_c": [25, 25, 25]})
        with patch.object(viewer.viewer_data.MeasurementCache, "load", return_value=frame), \
                patch.object(viewer, "configure_viewer_window", return_value=None), \
                patch.object(plt, "show", side_effect=exercise):
            viewer.show_charts()

    def test_setpoints_use_temperature_delta_font_size(self):
        import pandas as pd
        from matplotlib.figure import Figure
        figure = Figure()
        axes = [figure.add_subplot(1, 3, i + 1) for i in range(3)]
        viewer.draw_value_boxes(axes, pd.Series({"humidity_corrected_rh": 91, "co2_ppm": 1400,
                                                "temp_box_c": 25, "temp_ambient_c": 22}), Setpoints(1200, 92))
        self.assertEqual(next(text for text in axes[0].texts if text.get_text() == "92").get_fontsize(), 11)
        self.assertEqual(next(text for text in axes[1].texts if text.get_text() == "1200").get_fontsize(), 11)

    def test_card_details_show_actual_minus_setpoint_and_live_output(self):
        import pandas as pd
        from matplotlib.figure import Figure
        axes = [Figure().add_subplot() for _ in range(3)]
        values = pd.Series({"humidity_corrected_rh": 91, "co2_ppm": 1400,
                            "temp_box_c": 25, "temp_ambient_c": 22})
        state = {"online": True, "enabled": True,
                 "samples": [{"humidity_sum": 30, "co2_sum": 40}]}
        viewer.draw_value_boxes(axes, values, Setpoints(1200, 92), state)
        for axis, difference, output in ((axes[0], "-1.0", "30.0"), (axes[1], "+200", "40.0")):
            labels = {text.get_text() for text in axis.texts}
            self.assertTrue({"SET:", "DIF:", "PI%:", difference, output} <= labels)
        state["online"] = False
        viewer.draw_value_boxes(axes, values, Setpoints(1200, 92), state)
        self.assertNotIn("30.0", {text.get_text() for text in axes[0].texts})
