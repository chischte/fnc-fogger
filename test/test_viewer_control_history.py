import tempfile
import unittest
from pathlib import Path

import pandas as pd
from matplotlib import dates as mdates
from matplotlib.figure import Figure

from logger import logger
from logger.control_recording import record_control
from logger.lance_collection import LanceCollector
from logger.lance_registry import Lance
from logger.viewer_control import CommandPanel
from logger.viewer_control_history import ControlHistoryCache
from logger.viewer_style import DARK_THEME


def limits(start, end):
    return tuple(mdates.date2num(pd.Timestamp(value).to_pydatetime()) for value in (start, end))


class ControlHistoryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "device.db"
        self.db = logger.connect(self.path)
        self.addCleanup(self.db.close)
        self.cache = ControlHistoryCache()

    def append(self, timestamp, output, boot=1, enabled=True, fault=False, setpoints=None):
        control = {"setpoints": setpoints or {}, "enabled": enabled, "fault": fault, "fogger_enabled": True,
                   "co2": {"p": output / 2, "i": output / 2, "sum": output},
                   "humidity": {"p": 1, "i": 1.125, "sum": 2.125},
                   "fan": {"pwm_percent": round(output), "rpm": 1200},
                   "parameters": {"co2_kp": .02, "co2_ti_s": 300}}
        record_control(self.db, {"measurement": {"boot_id": boot}, "control": control}, timestamp)
        self.db.commit()

    def test_setpoint_history_retains_changes_even_when_pi_disabled_or_faulted(self):
        self.append("2026-11-12T10:00:00+00:00", 10, enabled=False,
                    setpoints={"co2_ppm": 1500, "humidity_rh": 98})
        self.append("2026-11-12T10:00:05+00:00", 10, fault=True,
                    setpoints={"co2_ppm": 2000, "humidity_rh": 95})
        frame = ControlHistoryCache().load(self.path)
        self.assertEqual(frame.co2_setpoint.tolist(), [1500, 2000])
        self.assertEqual(frame.humidity_setpoint.tolist(), [98, 95])
        self.assertTrue(frame.co2_sum.isna().all())
        selected, _ = self.cache.window(self.path, limits("2026-11-12 11:00:04", "2026-11-12 11:00:06"))
        self.assertEqual(selected.co2_setpoint.tolist(), [2000])

    def test_setpoint_lines_break_at_recording_gaps(self):
        values = {"co2_ppm": 1500, "humidity_rh": 98}
        self.append("2026-11-12T10:00:00+00:00", 10, setpoints=values)
        self.append("2026-11-12T10:01:00+00:00", 10, setpoints=values)
        frame = self.cache.load(self.path)
        self.assertTrue(frame.loc[frame.gap, "co2_setpoint"].isna().all())
        self.assertTrue(frame.loc[frame.gap, "humidity_setpoint"].isna().all())

    def test_sensor_graphs_plot_recorded_setpoints_as_green_dotted_steps(self):
        from logger import viewer
        from logger.viewer_style import SERIES
        timestamps = pd.date_range("2026-11-12 11:00", periods=2, freq="5s")
        history = pd.DataFrame({"timestamp": timestamps, "co2_setpoint": [1500, 2000],
                                "humidity_setpoint": [98, 95]})
        sensors = pd.DataFrame({"timestamp": timestamps, "co2_ppm": [1600, 1700],
                                "humidity_corrected_rh": [96, 97], "temp_box_c": [24, 24]})
        figure = Figure()
        for index, expected in ((0, [98, 95]), (1, [1500, 2000]), (2, None)):
            axis = figure.add_subplot(3, 1, index + 1)
            viewer.plot_series(axis, sensors, SERIES[index], history)
            lines = [line for line in axis.lines if line.get_label() == "Setpoint"]
            if expected is None:
                self.assertEqual(lines, [])
            else:
                self.assertEqual(lines[0].get_ydata().tolist(), expected)
                self.assertEqual(lines[0].get_linestyle(), ":")
                self.assertEqual(lines[0].get_color(), viewer.SETPOINT_COLOR)
                self.assertEqual(lines[0].get_drawstyle(), "steps-post")

    def test_history_survives_new_viewer_and_uses_zurich_time(self):
        self.append("2026-11-12T10:00:00+00:00", 12.345)
        frame, state = self.cache.window(self.path, limits("2026-11-12 10:59", "2026-11-12 11:01"))
        self.assertEqual(frame.timestamp.iloc[0], pd.Timestamp("2026-11-12 11:00"))
        self.assertEqual(frame.co2_sum.iloc[0], 12.345)
        self.assertEqual(state["samples"][0]["co2_sum"], 12.345)
        restored, _ = ControlHistoryCache().window(self.path, None)
        self.assertEqual(restored.co2_sum.iloc[0], 12.345)

    def test_new_samples_append_once_and_range_selects_matching_values(self):
        self.append("2026-11-12T10:00:00+00:00", 10)
        self.cache.load(self.path)
        revision = self.cache.revision
        self.cache.load(self.path)
        self.assertEqual(self.cache.revision, revision)
        self.append("2026-11-12T10:00:05+00:00", 20)
        frame, state = self.cache.window(self.path, limits("2026-11-12 11:00:04", "2026-11-12 11:00:06"))
        self.assertEqual(frame.co2_sum.tolist(), [20])
        self.assertEqual(state["samples"][0]["co2_sum"], 20)
        self.assertEqual(len(self.cache.load(self.path)), 2)

    def test_fault_manual_reboot_and_missing_recording_break_the_curve(self):
        self.append("2026-11-12T10:00:00+00:00", 10)
        self.append("2026-11-12T10:00:05+00:00", 20, fault=True)
        self.append("2026-11-12T10:00:10+00:00", 30, enabled=False)
        self.append("2026-11-12T10:00:15+00:00", 40, boot=2)
        self.append("2026-11-12T10:01:00+00:00", 50, boot=2)
        frame = self.cache.load(self.path)
        self.assertEqual(frame.gap.sum(), 2)
        self.assertEqual(frame.loc[~frame.gap, "co2_sum"].isna().tolist(), [False, True, True, False, False])
        self.assertTrue(frame.loc[frame.gap, "co2_sum"].isna().all())

    def test_empty_selected_range_does_not_show_live_values(self):
        self.append("2026-11-12T10:00:00+00:00", 10)
        frame, state = self.cache.window(self.path, limits("2026-11-12 09:00", "2026-11-12 09:10"))
        self.assertTrue(frame.empty)
        self.assertFalse(state["online"])
        self.assertEqual(state["samples"], [])

    def test_command_graph_uses_history_while_device_is_offline(self):
        self.append("2026-11-12T10:00:00+00:00", 12.345)
        collector = LanceCollector(Lance("b81f3f27f4e0", "test.local", 80), self.path)
        collector.control.disconnected("Offline")
        figure = Figure(figsize=(12, 8))
        panel = CommandPanel(figure, figure.add_gridspec(3, 2), collector)
        panel.set_visible(True)
        panel.update(DARK_THEME, limits("2026-11-12 10:59", "2026-11-12 11:01"))
        self.assertEqual(panel.graphs[1].lines[2].get_ydata().tolist(), [12.345])
        self.assertIn("fan @ 12%", [text.get_text() for text in panel.graphs[1].texts])
        self.assertTrue(collector.automatic_commands.empty())
        self.assertFalse(collector.control.snapshot()["online"])
