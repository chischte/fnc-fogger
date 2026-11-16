"""Live controls and PI diagrams backed by independent logger history."""
import math
import queue
import sqlite3
import textwrap
import time

import pandas as pd
from matplotlib import dates as mdates
from matplotlib.patches import Rectangle

from .control_data import Setpoints, HUMIDITY_EMERGENCY_MESSAGE
from .viewer_manual import ManualPanel
from .viewer_automatic import AutomaticPanel
from .viewer_cyclic_mist import CyclicMistPanel
from .viewer_format import whole_percent, format_rpm
from .viewer_stepper import CO2_LEVELS, HUMIDITY_LEVELS, SetpointStepper
from .viewer_control_history import ControlHistoryCache

AUTOSAVE_DELAY_SECONDS = 3
AUTOSAVE_RETRY_SECONDS = 5

TERM_STYLES = (("p", "p", ":"), ("i", "i", "--"), ("sum", "sum", "-"))
PI_OUTPUT_LIMITS = {"humidity": 100, "co2": 80}
PI_LIMIT_COLOR = "#e6c229"

CHANNEL_COLORS = {"humidity": "#2878a8", "co2": "#7b2cbf"}


def sensor_diagnostics_label(state):
    diagnostics = state.get("sensor_diagnostics", {})
    if not diagnostics:
        return ""
    co2 = diagnostics.get("co2", {})
    sht = diagnostics.get("sht45", {})
    return (f"Sensor outages: CO2 {co2.get('outages', 0)} | SHT45 {sht.get('outages', 0)}"
            f" | restarts: CO2 {co2.get('restarts', 0)}, SHT45 {sht.get('restarts', 0)}"
            f", bus {diagnostics.get('bus_restarts', 0)}")


def pi_parameter_label(state, channel):
    parameters = state.get("parameters", {})
    gain = parameters.get(channel + "_kp")
    integral_time = parameters.get(channel + "_ti_s")
    valid = all(isinstance(value, (int, float)) and not isinstance(value, bool)
                and math.isfinite(value) for value in (gain, integral_time))
    if not valid or gain < 0 or integral_time <= 0:
        return "Kp: --  |  Ti: --"
    duration = (f"{integral_time / 60:g} min" if integral_time % 60 == 0
                else f"{integral_time:g} s")
    if channel == "co2":
        gain *= 100
    unit = "%RH" if channel == "humidity" else "100 ppm"
    return f"Kp: {gain:g} %/{unit}  |  Ti: {duration}"


def actuator_graph_titles(state):
    return ("Humidity PI [%]", "CO2 PI [%]")


def actuator_graph_labels(state):
    values = state.get("actuators", {}) if state["online"] else {}
    samples = state.get("samples", [])
    latest = samples[-1] if samples and state["online"] and state.get("enabled") and not state.get("fault") else {}

    def seconds(value, precision=None):
        if value is None:
            return "--"
        return f"{value:.{precision}f}" if precision is not None else f"{value:g}"

    fogger_duty = values.get("duty_percent")
    if fogger_duty is None:
        fogger_duty = latest.get("humidity_sum")
    humidity = (f"fogger @ {whole_percent(fogger_duty)}%\n"
                f"on: {seconds(values.get('on_time_s'))}s | off: {seconds(values.get('off_time_s'), 2)}s")
    fan_duty = values.get("pwm_percent")
    if fan_duty is None:
        fan_duty = latest.get("co2_sum")
    co2 = f"fan @ {whole_percent(fan_duty)}%\n{format_rpm(values.get('rpm'))} rpm"
    if state.get("fault"):
        co2 += f" | Fan: {whole_percent(values.get('pwm_percent'))}% [fault]"
    return humidity, co2


class CommandPanel:
    def __init__(self, figure, grid, collector, database=None):
        self.figure = figure
        self.collector = collector
        self.database = collector.database if collector is not None else database
        self.visible = False
        self.dirty = False
        self.pending = False
        self._save_due_at = None
        self._submitted_values = None
        self.last_setpoints = None
        self.feedback = ""
        self.changed = False
        self._last_render_state = None
        self._last_theme = None
        self.history = ControlHistoryCache()
        self._history_error = ""
        self.graphs = [figure.add_subplot(grid[row, 1]) for row in range(2)]
        self.editor = figure.add_subplot(grid[2, 1])
        self.editor.axis("off")
        self.heading = self.editor.set_title("Control Panel", fontsize=10, fontweight="bold", pad=6)
        self.frame = Rectangle((0, 0), 1, 1, transform=self.editor.transAxes,
                               linewidth=1, clip_on=False, zorder=0)
        self.editor.add_patch(self.frame)
        self.status = self.editor.text(0.04, -0.04, "", fontsize=8, va="top")
        self.co2 = SetpointStepper(figure, "CO2 [ppm]", CO2_LEVELS, self._edited)
        self.humidity = SetpointStepper(figure, "Humidity [%RH]", HUMIDITY_LEVELS, self._edited)
        self.co2.set_val(1000)
        self.humidity.set_val(90)
        self.manual = ManualPanel(figure, collector, self._refresh_manual)
        self.automatic = AutomaticPanel(figure, collector, self._refresh_manual)
        self.cyclic = CyclicMistPanel(figure, collector, self._refresh_manual, self.editor)
        self.set_visible(False)

    def _refresh_manual(self):
        if self._last_theme is not None:
            self.update(self._last_theme, self.graphs[0].get_xlim())
            self.figure.canvas.draw_idle()

    def _edited(self, _value):
        self.dirty = True
        self._save_due_at = time.monotonic() + AUTOSAVE_DELAY_SECONDS
        self.feedback = "Saving automatically 3 seconds after the last change..."
        self.status.set_text(textwrap.fill(self.feedback, 68))
        self.figure.canvas.draw_idle()

    def _maybe_save(self, state):
        if not self.dirty or self.pending or self.collector is None or self._save_due_at is None:
            return
        if time.monotonic() < self._save_due_at:
            return
        if not state["online"] or not state["supported"]:
            self.feedback = "Waiting for connection to save changed setpoints."
            return
        try:
            values = Setpoints(self.co2.value, self.humidity.value)
            if state["setpoints"] == values and state["persisted"]:
                self.dirty = False
                self._save_due_at = None
                self.feedback = "Setpoints already saved on the device."
                return
            self.collector.submit_setpoints(values)
            self._submitted_values = values
            self.pending = True
            self.feedback = "Saving setpoints..."
        except (ValueError, TypeError) as error:
            self.feedback = str(error)
            self._save_due_at = time.monotonic() + AUTOSAVE_RETRY_SECONDS

    def layout(self):
        box = self.editor.get_position()
        self.manual.layout(box)
        self.automatic.layout(box)
        self.frame.set_bounds(0, 0 if self.manual.selected else .28, 1,
                              1 if self.manual.selected else .72)
        self._layout_mode_buttons(box)
        for field, y in ((self.co2, .54), (self.humidity, .32)):
            bottom = box.y0 + box.height * y
            height = box.height * .16
            field.layout([box.x0 + box.width * .04, bottom,
                          box.width * .92, height])
            field.value_text.set_position(((.65 - .04) / .92, .5))
            for button, left in ((field.minus, .362), (field.plus, .762)):
                button.ax.set_position([box.x0 + box.width * left, bottom,
                                        box.width * .198, height])
        self.cyclic.layout(box, self.co2)

    def _layout_mode_buttons(self, box):
        positions = [(self.manual.toggle, .47, .49)]
        if not self.manual.selected:
            positions.append((self.automatic.button, .04, .40))
        for button, left, width in positions:
            button.ax.set_position([box.x0 + box.width * left,
                                    box.y0 + box.height * .76,
                                    box.width * width, box.height * .16])

    def set_visible(self, visible):
        self.visible = visible
        for axis in [*self.graphs, self.editor, *self.co2.axes, *self.humidity.axes]:
            axis.set_visible(visible)
        for widget in (self.co2, self.humidity):
            widget.set_active(visible)
        self.manual.set_visible(visible)
        self.cyclic.set_visible(visible and not self.manual.selected)
        if not visible:
            self.automatic.button.ax.set_visible(False)
        self.layout()

    def _read_results(self):
        if self.collector is None:
            return
        while True:
            try:
                success, message = self.collector.command_results.get_nowait()
            except queue.Empty:
                break
            self.pending = False
            self.feedback = message
            if success:
                values = Setpoints(self.co2.value, self.humidity.value)
                self.dirty = values != self._submitted_values
                if not self.dirty:
                    self._save_due_at = None
                else:
                    self.feedback = "Saving the latest changes automatically..."
            else:
                self._save_due_at = time.monotonic() + AUTOSAVE_RETRY_SECONDS

    def update(self, theme, limits=None):
        self._last_theme = theme
        self.changed = False
        self._read_results()
        state = self.collector.control.snapshot() if self.collector else {
            "setpoints": None, "samples": [], "supported": False,
            "online": False, "enabled": False, "message": "No lance connected."}
        self._maybe_save(state)
        manual_state = self.manual.update(state, self.visible, theme)
        automatic_state = self.automatic.update(state, self.visible, self.manual.selected, theme)
        cyclic_state = self.cyclic.update(state, self.visible and not self.manual.selected, theme)
        self.layout()
        history_window = None
        if self.visible and self.database is not None:
            try:
                history_window = self.history.window(self.database, limits)
                self._history_error = ""
            except (OSError, sqlite3.Error) as error:
                self._history_error = f"Could not load recorded PI history: {error}"
        graph_state = history_window[1] if history_window is not None else state
        setpoints = state["setpoints"]
        samples = state["samples"]
        render_state = (tuple(theme.items()), tuple(limits) if limits is not None else None,
                        setpoints, state["supported"], state["online"], state["enabled"],
                        state["message"], len(samples), samples[-1]["timestamp"] if samples else None,
                        actuator_graph_labels(graph_state), manual_state, automatic_state, cyclic_state,
                        pi_parameter_label(graph_state, "co2"), pi_parameter_label(graph_state, "humidity"),
                        self.history.revision, self._history_error,
                        sensor_diagnostics_label(state), self.feedback, self.pending, self.dirty, self.visible)
        if render_state == self._last_render_state:
            return setpoints
        self._last_render_state = render_state
        self.changed = True
        if setpoints is not None and not self.dirty and not self.pending and setpoints != self.last_setpoints:
            self.co2.set_val(setpoints.co2_ppm)
            self.humidity.set_val(setpoints.humidity_rh)
            self.last_setpoints = setpoints
        for field in (self.co2, self.humidity):
            for axis in field.axes:
                axis.set_visible(self.visible and not self.manual.selected)
            field.set_active(self.visible and not self.manual.selected)
        self.heading.set_text("Control Panel")
        self.heading.set_visible(True)
        self.heading.set_color(theme["text"])
        self.frame.set_edgecolor(theme["grid"])
        self.frame.set_facecolor(theme["plot"])
        message = state["message"]
        if self._history_error:
            message = self._history_error + "\n" + message
        if setpoints is None:
            message += " Displaying editable defaults; not saved to the device."
        feedback = self.manual.feedback if self.manual.selected or self.manual.pending else self.feedback
        if feedback:
            message = feedback + "\n" + message
        if self.cyclic.feedback and not self.manual.selected:
            message = self.cyclic.feedback + "\n" + message
        if self.automatic.feedback and not self.manual.selected:
            message = self.automatic.feedback + "\n" + message
        emergency = state.get("humidity_emergency", {}).get("active") is True
        if emergency:
            message = HUMIDITY_EMERGENCY_MESSAGE
        diagnostics = sensor_diagnostics_label(state)
        message = textwrap.fill(message, 68)
        if diagnostics:
            message += "\n" + textwrap.fill(diagnostics, 68)
        self.status.set_text(message)
        self.status.set_color("#ff5252" if emergency else theme["muted"])
        self.status.set_fontweight("bold" if emergency else "normal")
        for field in (self.co2, self.humidity):
            field.style(theme)
        if self.visible:
            self._draw_graphs(graph_state, theme, limits, history_window)
        return setpoints

    def _draw_graphs(self, state, theme, limits, history_window=None):
        frame = history_window[0] if history_window is not None else pd.DataFrame(state["samples"])
        for axis, channel, title in zip(self.graphs, ("humidity", "co2"),
                                         actuator_graph_titles(state)):
            humidity_locked = (history_window is None and channel == "humidity"
                               and not state.get("fogger_enabled", True))
            axis.clear()
            axis.set_facecolor(theme["plot"])
            axis.set_title(title, fontsize=10, fontweight="bold", color=theme["text"])
            axis.set_xlabel(pi_parameter_label(state, channel), fontsize=8, color=theme["muted"], labelpad=6)
            axis.xaxis.set_label_coords(0.5, -0.19)
            label = actuator_graph_labels(state)[0 if channel == "humidity" else 1]
            summary, _, detail = label.partition("\n")
            for text, height, size, weight in ((summary, .23, 10, "bold"),
                                                (detail, .06, 9, "normal")):
                axis.text(0.5, height, text, ha="center", va="bottom", fontsize=size,
                          fontweight=weight, color=theme["text"], transform=axis.transAxes,
                          zorder=5,
                          bbox={"facecolor": theme["plot"], "edgecolor": "none",
                                "alpha": 1, "pad": 3})
            for term, label, style in TERM_STYLES:
                timestamps = frame["timestamp"] if not frame.empty and not humidity_locked else []
                values = frame[f"{channel}_{term}"] if not frame.empty and not humidity_locked else []
                axis.plot(timestamps, values, label=label, color=CHANNEL_COLORS[channel],
                          linestyle=style, linewidth=1.4, zorder=3)
            output_limit = PI_OUTPUT_LIMITS[channel]
            axis.axhline(output_limit, color=PI_LIMIT_COLOR, linewidth=0.6,
                         linestyle=":", zorder=2)
            axis.set_ylim(-20, 100)
            axis.set_yticks([-20, 0, 25, 50, 75, 100])
            axis.spines["bottom"].set_position(("axes", 0))
            if limits is not None:
                axis.set_xlim(limits)
            axis.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=5))
            axis.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
            axis.tick_params(colors=theme["muted"], labelsize=8)
            axis.grid(True, linestyle="--", linewidth=0.6, color=theme["grid"])
            axis.spines[["top", "right"]].set_visible(False)
            axis.spines[["left", "bottom"]].set_color(theme["grid"])
            axis.legend(fontsize=8, loc="upper left", facecolor=theme["card"],
                        edgecolor=theme["grid"], labelcolor=theme["text"])
            columns = [f"{channel}_{term}" for term, *_ in TERM_STYLES]
            has_terms = not frame.empty and frame[columns].notna().any().any()
            if humidity_locked or not has_terms:
                message = ("No recorded PI data in this range" if history_window is not None else
                           "Humidity PI disabled - ventilation test" if humidity_locked else
                           "Controller not configured" if not state["enabled"] else
                           "Waiting for controller data")
                axis.text(0.5, 0.5, message, ha="center", va="center",
                          color=theme["muted"], fontsize=9, transform=axis.transAxes)
        self.heading.set_fontproperties(self.graphs[0].title.get_fontproperties())
