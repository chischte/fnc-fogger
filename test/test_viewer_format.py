import unittest

from logger.viewer_format import rounded_rpm, whole_percent
from logger.viewer_control import actuator_graph_labels


class ViewerFormatTests(unittest.TestCase):
    def test_rpm_rounding_respects_ranges_and_missing_values(self):
        for value, expected in [(0, "0"), (324, "300"), (325, "350"),
                                (975, "1000"), (1000, "1000"), (1050, "1100"),
                                (4220, "4200"), (None, "--")]:
            self.assertEqual(rounded_rpm(value), expected)

    def test_graph_labels_use_actual_duty_and_clear_offline(self):
        state = {"online": True, "actuators": {"duty_percent": 14.7,
                 "pwm_percent": 80, "rpm": 4220}}
        self.assertEqual(actuator_graph_labels(state), ("15%", "80% - 4200rpm"))
        state["online"] = False
        self.assertEqual(actuator_graph_labels(state), ("--%", "--% - --rpm"))
        self.assertEqual(whole_percent(15.5), "16")
        self.assertEqual(whole_percent(float("nan")), "--")
