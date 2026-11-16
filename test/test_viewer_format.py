import unittest

from logger.viewer_format import format_rpm, whole_percent
from logger.viewer_control import actuator_graph_labels, cyclic_mist_activity_label


class ViewerFormatTests(unittest.TestCase):
    def test_paused_fogger_shows_zero_output_despite_retained_pi_demand(self):
        state = {"online": True, "enabled": True,
                 "samples": [{"humidity_sum": 7.2}],
                 "actuators": {"duty_percent": 0, "on_time_s": 0, "off_time_s": None}}
        self.assertEqual(actuator_graph_labels(state)[0], "fogger @ 0%\non: 0s | off: --s")

    def test_cyclic_mist_fan_label_shows_fixed_output_instead_of_held_pi_sum(self):
        state = {"online": True, "enabled": True,
                 "samples": [{"co2_sum": 17}],
                 "actuators": {"pwm_percent": 50, "rpm": 2900}}
        self.assertEqual(actuator_graph_labels(state)[1], "fan @ 50%\n2900 rpm")

    def test_rpm_rounds_to_ten_and_handles_missing_values(self):
        for value, expected in [(0, "0"), (324, "320"), (325, "330"),
                                (975, "980"), (1000, "1000"), (1050, "1050"),
                                (4220, "4220"), (324.5, "320"), (None, "--")]:
            self.assertEqual(format_rpm(value), expected)

    def test_graph_labels_use_actual_duty_and_clear_offline(self):
        state = {"online": True, "enabled": True,
                 "samples": [{"humidity_sum": 14.7, "co2_sum": 80}],
                 "actuators": {"pwm_percent": 80, "rpm": 4220,
                               "on_time_s": .1, "off_time_s": .567}}
        self.assertEqual(actuator_graph_labels(state),
                         ("fogger @ 15%\non: 0.1s | off: 0.57s", "fan @ 80%\n4220 rpm"))
        state["online"] = False
        self.assertEqual(actuator_graph_labels(state),
                         ("fogger @ --%\non: --s | off: --s", "fan @ --%\n-- rpm"))
        self.assertEqual(whole_percent(15.5), "16")
        self.assertEqual(whole_percent(float("nan")), "--")

    def test_cyclic_activity_covers_misting_and_settling_only_in_automatic_mode(self):
        state = {"online": True, "enabled": True, "cyclic_mist": {"misting": True}}
        self.assertEqual(cyclic_mist_activity_label(state), "cyclic mist active")
        state["cyclic_mist"] = {"misting": False, "settling": True}
        self.assertEqual(cyclic_mist_activity_label(state), "cyclic mist active")
        state["cyclic_mist"] = {"misting": False, "settling": False}
        self.assertEqual(cyclic_mist_activity_label(state), "")
        state["cyclic_mist"]["settling"] = True
        state["enabled"] = False
        self.assertEqual(cyclic_mist_activity_label(state), "")
