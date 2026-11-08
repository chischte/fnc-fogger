import unittest
from unittest.mock import Mock, patch

from matplotlib.figure import Figure

from logger.viewer_stepper import CO2_LEVELS, HUMIDITY_LEVELS, SetpointStepper


class SetpointStepperTests(unittest.TestCase):
    def test_command_panel_does_not_redraw_unchanged_state(self):
        from matplotlib.gridspec import GridSpec
        from logger.viewer import DARK_THEME, LIGHT_THEME
        from logger.viewer_control import CommandPanel
        figure = Figure()
        panel = CommandPanel(figure, GridSpec(3, 2, figure=figure), None)
        panel.set_visible(True)
        with patch.object(panel, "_draw_graphs") as redraw:
            panel.update(LIGHT_THEME)
            self.assertTrue(panel.changed)
            panel.update(LIGHT_THEME)
            self.assertFalse(panel.changed)
            self.assertEqual(redraw.call_count, 1)
            panel.update(DARK_THEME)
            self.assertTrue(panel.changed)
            self.assertEqual(redraw.call_count, 2)

    def test_command_panel_can_edit_defaults_without_device_support(self):
        from matplotlib.gridspec import GridSpec
        from logger.viewer import LIGHT_THEME
        from logger.viewer_control import CommandPanel
        figure = Figure(figsize=(11, 8.5))
        panel = CommandPanel(figure, GridSpec(3, 2, figure=figure), None)
        panel.set_visible(True)
        panel.update(LIGHT_THEME)
        self.assertEqual(panel.co2.value, 1000)
        self.assertEqual(panel.humidity.value, 90)
        panel.co2._step(1)
        panel.humidity._step(-1)
        self.assertEqual((panel.co2.value, panel.humidity.value), (1500, 89))
        self.assertTrue(panel.dirty)
        self.assertFalse(panel.save.active)
        self.assertEqual(panel.save.label.get_text(), "Save")
        self.assertLess(panel.save.ax.get_position().y1, panel.humidity.ax.get_position().y0)

    def make_stepper(self, levels, value):
        stepper = SetpointStepper(Figure(), "Setpoint", levels, Mock())
        stepper.set_val(value)
        stepper.set_active(True)
        return stepper

    def test_co2_crosses_5000_with_correct_steps_in_both_directions(self):
        stepper = self.make_stepper(CO2_LEVELS, 4500)
        for expected in (5000, 6000, 7000):
            stepper._step(1)
            self.assertEqual(stepper.value, expected)
        for expected in (6000, 5000, 4500):
            stepper._step(-1)
            self.assertEqual(stepper.value, expected)

    def test_co2_stops_at_zero_and_20000(self):
        stepper = self.make_stepper(CO2_LEVELS, 0)
        stepper._step(-1)
        self.assertEqual(stepper.value, 0)
        self.assertFalse(stepper.minus.active)
        stepper.set_val(20000)
        stepper._step(1)
        self.assertEqual(stepper.value, 20000)
        self.assertFalse(stepper.plus.active)
        self.assertFalse(stepper.on_change.called)

    def test_humidity_uses_integer_steps_and_stops_at_70_and_100(self):
        stepper = self.make_stepper(HUMIDITY_LEVELS, 70)
        for expected in range(71, 101):
            stepper._step(1)
            self.assertEqual(stepper.value, expected)
        stepper._step(1)
        self.assertEqual(stepper.value, 100)
        for expected in range(99, 69, -1):
            stepper._step(-1)
            self.assertEqual(stepper.value, expected)
        stepper._step(-1)
        self.assertEqual(stepper.value, 70)

    def test_existing_off_grid_values_move_to_next_allowed_value(self):
        stepper = self.make_stepper(CO2_LEVELS, 1200)
        stepper._step(1)
        self.assertEqual(stepper.value, 1500)
        stepper.set_val(1200)
        stepper._step(-1)
        self.assertEqual(stepper.value, 1000)

    def test_pending_controls_cannot_change_values(self):
        stepper = self.make_stepper(CO2_LEVELS, 1000)
        stepper.set_active(False)
        stepper._step(1)
        self.assertEqual(stepper.value, 1000)
        self.assertFalse(stepper.on_change.called)
