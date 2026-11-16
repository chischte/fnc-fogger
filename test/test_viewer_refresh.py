import unittest
from unittest.mock import patch

import pandas as pd
from matplotlib import dates as mdates
from matplotlib.figure import Figure

from logger import viewer


class ViewerRefreshTests(unittest.TestCase):
    def setUp(self):
        self.figure = Figure()
        self.boxes = [self.figure.add_subplot(3, 3, i + 1) for i in range(3)]
        self.charts = [self.figure.add_subplot(3, 3, i + 4) for i in range(3)]
        self.range_axis = self.figure.add_subplot(3, 1, 3)
        self.footer = self.figure.text(0, 0, "")
        self.frame = pd.DataFrame({
            "timestamp": pd.date_range("2026-09-27T12:00:00", periods=3, freq="min"),
            "humidity_corrected_rh": [88.0, 88.1, 88.2],
            "co2_ppm": [1000, 1100, 1200],
            "temp_box_c": [25.0, 25.1, 25.2],
        })
        self.x_limits = tuple(mdates.date2num(self.frame["timestamp"].iloc[:2]))
        self.y_limits = [(87.5, 88.5), (900, 1300), (24.9, 25.3)]
        for axis, limits in zip(self.charts, self.y_limits):
            axis.set_xlim(self.x_limits)
            axis.set_ylim(limits)

    def refresh(self, preserve_view=True, adaptive_y=False):
        with patch.object(viewer, "load_data", return_value=self.frame), \
                patch.dict(viewer._state, {"range": "30m", "adaptive_y": adaptive_y}):
            viewer.draw(self.figure, self.boxes, self.charts, self.range_axis,
                        self.footer, preserve_view=preserve_view)

    def test_refresh_preserves_horizontal_and_vertical_zoom_with_new_data(self):
        for _ in range(2):
            self.refresh()
            for axis, limits in zip(self.charts, self.y_limits):
                self.assertEqual(self.x_limits, axis.get_xlim())
                self.assertEqual(limits, axis.get_ylim())
            self.frame.loc[len(self.frame)] = [
                self.frame["timestamp"].iloc[-1] + pd.Timedelta(minutes=1),
                90.0, 2000, 27.0,
            ]

    def test_adaptive_y_uses_visible_data_and_preserves_time_zoom(self):
        self.refresh(adaptive_y=True)
        for axis, limits in zip(self.charts, self.y_limits):
            self.assertEqual(self.x_limits, axis.get_xlim())
            self.assertNotEqual(limits, axis.get_ylim())

    def test_range_selection_restores_default_scales(self):
        self.refresh(preserve_view=False)
        for axis, series in zip(self.charts, viewer.SERIES):
            self.assertNotEqual(self.x_limits, axis.get_xlim())
            self.assertEqual((series["ymin"], series["ymax"]), axis.get_ylim())

    def test_rectangle_zoom_survives_adaptive_refresh_with_readable_y_ticks(self):
        with patch.dict(viewer._state, {"manual_y": True}):
            self.refresh(adaptive_y=True)
        for axis, limits in zip(self.charts, self.y_limits):
            self.assertEqual(self.x_limits, axis.get_xlim())
            self.assertEqual(limits, axis.get_ylim())
            ticks = [tick for tick in axis.get_yticks() if limits[0] <= tick <= limits[1]]
            self.assertGreaterEqual(len(ticks), 3)

    def test_real_rectangle_events_and_refresh_timer_keep_selected_co2_view(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from matplotlib.backend_bases import MouseEvent, NavigationToolbar2, TimerBase
        from matplotlib.backends.backend_agg import FigureCanvasAgg

        figure = Figure(figsize=(11, 8.5))
        canvas = FigureCanvasAgg(figure)
        toolbar = NavigationToolbar2(canvas)
        canvas.manager = SimpleNamespace(toolbar=toolbar, set_window_title=Mock())
        cache = Mock(revision=1)
        cache.load.return_value = self.frame
        timers = {}

        def timer(interval):
            timers[interval] = TimerBase(interval=interval)
            return timers[interval]

        def interact():
            axis = next(axis for axis in figure.axes if axis.get_title() == "CO2 [ppm]")
            canvas.draw()
            toolbar.zoom()
            limits = axis.get_xlim()
            points = [(limits[0] + (limits[1] - limits[0]) * fraction, value)
                      for fraction, value in [(0.3, 1020), (0.8, 1180)]]
            pixels = [axis.transData.transform(point) for point in points]
            line = axis.lines[0]
            for name, pixel in [("button_press_event", pixels[0]),
                                ("motion_notify_event", pixels[1])]:
                event = MouseEvent(name, canvas, *pixel, button=1,
                                   buttons={1} if name == "motion_notify_event" else None)
                canvas.callbacks.process(name, event)
            timers[viewer.REFRESH_INTERVAL_MS]._on_timer()
            self.assertIs(line, axis.lines[0], "Refresh must not clear an active selection")
            canvas.callbacks.process("button_release_event",
                                     MouseEvent("button_release_event", canvas, *pixels[1], button=1))
            selected = axis.get_xlim(), axis.get_ylim()
            self.assertTrue(viewer._state["manual_view"])
            self.assertTrue(viewer._state["manual_y"])
            self.assertLess(selected[0][1] - selected[0][0], limits[1] - limits[0])
            for _ in range(2):
                cache.revision += 1
                timers[viewer.REFRESH_INTERVAL_MS]._on_timer()
                self.assertEqual(selected, (axis.get_xlim(), axis.get_ylim()))

        panel = Mock()
        panel.history = None
        panel.update.return_value = None
        with patch.object(viewer.plt, "figure", return_value=figure), \
                patch.object(viewer.plt, "show", side_effect=interact), \
                patch.object(viewer, "configure_viewer_window", return_value=None), \
                patch.object(viewer, "CommandPanel", return_value=panel), \
                patch.object(viewer.viewer_data, "MeasurementCache", return_value=cache), \
                patch.object(canvas, "new_timer", side_effect=timer), \
                patch.dict(viewer._state, {"adaptive_y": True}):
            viewer.show_charts()
