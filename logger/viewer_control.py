"""Command-mode controls and live, memory-only PI diagrams."""
import math
import queue
import textwrap
import time

import pandas as pd
from matplotlib import dates as mdates

from .control_data import Setpoints
from .viewer_manual import ManualPanel
from .viewer_automatic import AutomaticPanel
from .viewer_stepper import CO2_LEVELS, HUMIDITY_LEVELS, SetpointStepper

AUTOSAVE_DELAY_SECONDS = 3
AUTOSAVE_RETRY_SECONDS = 5

TERM_STYLES = (("p", "p", ":"), ("i", "i", "--"), ("sum", "sum", "-"))
CHANNEL_COLORS = {"humidity": "#2878a8", "co2": "#7b2cbf"}


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
    values = state.get("actuators", {}) if state["online"] else {}
    samples = state.get("samples", [])
    latest = samples[-1] if samples and state["online"] and state["enabled"] and not state.get("fault") else {}

    def formatted(value, unit):
        number = "—" if value is None or not math.isfinite(value) else f"{value:g}"
        return f"{number} {unit}"

    return (f"Humidity PI [%] | sum: {formatted(latest.get('humidity_sum'), '%')} | "
            f"ON: {formatted(values.get('on_time_s'), 's')} | "
            f"OFF: {formatted(values.get('off_time_s'), 's')}",
            f"CO2 PI [%] | sum: {formatted(latest.get('co2_sum'), '%')} | "
            f"Fan: {formatted(values.get('pwm_percent'), '%')} / {formatted(values.get('rpm'), 'rpm')}"
            f"{' [fault]' if state.get('fault') else ''}")


class CommandPanel:
    def __init__(self, figure, grid, collector):
        self.figure = figure
        self.collector = collector
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
        self.graphs = [figure.add_subplot(grid[row, 1]) for row in range(2)]
        self.editor = figure.add_subplot(grid[2, 1])
        self.editor.axis("off")
        self.heading = self.editor.text(0.04, 0.91, "Setpoints", fontsize=11, fontweight="bold")
        self.status = self.editor.text(0.04, -0.04, "", fontsize=8, va="top")
        self.co2 = SetpointStepper(figure, "CO2 [ppm]", CO2_LEVELS, self._edited)
        self.humidity = SetpointStepper(figure, "Humidity [%RH]", HUMIDITY_LEVELS, self._edited)
        self.co2.set_val(1000)
        self.humidity.set_val(90)
        self.manual = ManualPanel(figure, collector, self._refresh_manual)
        self.automatic = AutomaticPanel(figure, collector, self._refresh_manual)
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
        for field, y in ((self.co2, 0.62), (self.humidity, 0.38)):
            field.layout([box.x0 + box.width * 0.04, box.y0 + box.height * y,
                          box.width * 0.92, box.height * 0.17])

    def set_visible(self, visible):
        self.visible = visible
        for axis in [*self.graphs, self.editor, *self.co2.axes, *self.humidity.axes]:
            axis.set_visible(visible)
        for widget in (self.co2, self.humidity):
            widget.set_active(visible)
        self.manual.set_visible(visible)
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
        setpoints = state["setpoints"]
        samples = state["samples"]
        render_state = (tuple(theme.items()), tuple(limits) if limits is not None else None,
                        setpoints, state["supported"], state["online"], state["enabled"],
                        state["message"], len(samples), samples[-1]["timestamp"] if samples else None,
                        actuator_graph_titles(state), manual_state, automatic_state,
                        pi_parameter_label(state, "co2"), pi_parameter_label(state, "humidity"),
                        self.feedback, self.pending, self.dirty, self.visible)
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
        self.heading.set_text("Manual Outputs" if self.manual.selected else "Setpoints")
        self.heading.set_visible(self.manual.selected or not state.get("automatic_supported", False))
        self.heading.set_color(theme["text"])
        message = state["message"]
        if setpoints is None:
            message += " Displaying editable defaults; not saved to the device."
        feedback = self.manual.feedback if self.manual.selected or self.manual.pending else self.feedback
        if feedback:
            message = feedback + "\n" + message
        if self.automatic.feedback and not self.manual.selected:
            message = self.automatic.feedback + "\n" + message
        self.status.set_text(textwrap.fill(message, 68))
        self.status.set_color(theme["muted"])
        for field in (self.co2, self.humidity):
            field.style(theme)
        if self.visible:
            self._draw_graphs(state, theme, limits)
        return setpoints

    def _draw_graphs(self, state, theme, limits):
        frame = pd.DataFrame(state["samples"])
        for axis, channel, title in zip(self.graphs, ("humidity", "co2"),
                                         actuator_graph_titles(state)):
            humidity_locked = channel == "humidity" and not state.get("fogger_enabled", True)
            axis.clear()
            axis.set_facecolor(theme["plot"])
            axis.set_title(title, fontsize=10, fontweight="bold", color=theme["text"])
            axis.set_xlabel(pi_parameter_label(state, channel), fontsize=8, color=theme["muted"], labelpad=6)
            axis.xaxis.set_label_coords(0.5, -0.12)
            for term, label, style in TERM_STYLES:
                timestamps = frame["timestamp"] if not frame.empty and not humidity_locked else []
                values = frame[f"{channel}_{term}"] if not frame.empty and not humidity_locked else []
                axis.plot(timestamps, values, label=label, color=CHANNEL_COLORS[channel],
                          linestyle=style, linewidth=1.4, zorder=3)
            axis.set_ylim(-100, 100)
            axis.set_yticks([-100, -50, 0, 50, 100])
            axis.spines["bottom"].set_position(("data", 0))
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
                message = ("Humidity PI disabled - ventilation test" if humidity_locked else
                           "Controller not configured" if not state["enabled"] else
                           "Waiting for controller data")
                axis.text(0.5, 0.25, message, ha="center", va="center",
                          color=theme["muted"], fontsize=9, transform=axis.transAxes)
