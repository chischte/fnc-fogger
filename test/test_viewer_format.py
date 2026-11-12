import unittest

from logger.viewer_format import rounded_rpm, whole_percent
from logger.viewer_control import actuator_graph_labels


class ViewerFormatTests(unittest.TestCase):
    def test_paused_fogger_shows_zero_output_despite_retained_pi_demand(self):
        state = {"online": True, "enabled": True,
                 "samples": [{"humidity_sum": 7.2}],
                 "actuators": {"duty_percent": 0, "on_time_s": 0, "off_time_s": None}}
        self.assertEqual(actuator_graph_labels(state)[0], "fogger @ 0%\non: 0s | off: --s")

    def test_rpm_rounding_respects_ranges_and_missing_values(self):
        for value, expected in [(0, "0"), (324, "300"), (325, "350"),
                                (975, "1000"), (1000, "1000"), (1050, "1100"),
                                (4220, "4200"), (None, "--")]:
            self.assertEqual(rounded_rpm(value), expected)

    def test_graph_labels_use_actual_duty_and_clear_offline(self):
        state = {"online": True, "enabled": True,
                 "samples": [{"humidity_sum": 14.7, "co2_sum": 80}],
                 "actuators": {"pwm_percent": 80, "rpm": 4220,
                               "on_time_s": .1, "off_time_s": .567}}
        self.assertEqual(actuator_graph_labels(state),
                         ("fogger @ 15%\non: 0.1s | off: 0.57s", "fan @ 80%\n4200rpm"))
        state["online"] = False
        self.assertEqual(actuator_graph_labels(state),
                         ("fogger @ --%\non: --s | off: --s", "fan @ --%\n--rpm"))
        self.assertEqual(whole_percent(15.5), "16")
        self.assertEqual(whole_percent(float("nan")), "--")
