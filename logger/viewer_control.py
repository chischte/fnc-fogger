"""Command-mode controls and live, memory-only PI diagrams."""
import queue
import textwrap

import pandas as pd
from matplotlib import dates as mdates
from matplotlib.widgets import Button

from .control_data import Setpoints
from .viewer_stepper import CO2_LEVELS, HUMIDITY_LEVELS, SetpointStepper

TERM_STYLES = (("p", "P", ":"), ("i", "I", "--"), ("sum", "SUM", "-"))
CHANNEL_COLORS = {"humidity": "#2878a8", "co2": "#7b2cbf"}


class CommandPanel:
    def __init__(self, figure, grid, collector):
        self.figure = figure
        self.collector = collector
        self.visible = False
        self.dirty = False
        self.pending = False
        self.last_setpoints = None
        self.feedback = ""
        self.changed = False
        self._last_render_state = None
        self.graphs = [figure.add_subplot(grid[row, 1]) for row in range(2)]
        self.editor = figure.add_subplot(grid[2, 1])
        self.editor.axis("off")
        self.heading = self.editor.text(0.04, 0.91, "Setpoints", fontsize=11, fontweight="bold")
        self.status = self.editor.text(0.04, -0.04, "", fontsize=8, va="top")
        self.co2 = SetpointStepper(figure, "CO2 [ppm]", CO2_LEVELS, self._edited)
        self.humidity = SetpointStepper(figure, "Humidity [%RH]", HUMIDITY_LEVELS, self._edited)
        self.co2.set_val(1000)
        self.humidity.set_val(90)
        self.save = Button(figure.add_axes([0, 0, 0.1, 0.03]), "Save")
        self.save.on_clicked(self._submit)
        self.set_visible(False)

    def _edited(self, _value):
        self.dirty = True
        self.feedback = "Changed – not saved to the device yet."

    def _submit(self, _event):
        if self.pending or self.collector is None:
            return
        try:
            values = Setpoints(self.co2.value, self.humidity.value)
            self.collector.submit_setpoints(values)
            self.pending = True
            for widget in (self.co2, self.humidity, self.save):
                widget.set_active(False)
            self.feedback = "Saving …"
        except (ValueError, TypeError) as error:
            self.feedback = str(error)
        self.status.set_text(textwrap.fill(self.feedback, 68))
        self.figure.canvas.draw_idle()

    def layout(self):
        box = self.editor.get_position()
        for field, y in ((self.co2, 0.62), (self.humidity, 0.38)):
            field.layout([box.x0 + box.width * 0.04, box.y0 + box.height * y,
                          box.width * 0.92, box.height * 0.17])
        self.save.ax.set_position([box.x0 + box.width * 0.25, box.y0 + box.height * 0.10,
                                   box.width * 0.50, box.height * 0.18])

    def set_visible(self, visible):
        self.visible = visible
        for axis in [*self.graphs, self.editor, *self.co2.axes, *self.humidity.axes, self.save.ax]:
            axis.set_visible(visible)
        for widget in (self.co2, self.humidity, self.save):
            widget.set_active(visible and not self.pending)
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
                self.dirty = False

    def update(self, theme, limits=None):
        self.changed = False
        self._read_results()
        state = self.collector.control.snapshot() if self.collector else {
            "setpoints": None, "samples": [], "supported": False,
            "online": False, "enabled": False, "message": "No lance connected."}
        setpoints = state["setpoints"]
        samples = state["samples"]
        render_state = (tuple(theme.items()), tuple(limits) if limits is not None else None,
                        setpoints, state["supported"], state["online"], state["enabled"],
                        state["message"], len(samples), samples[-1]["timestamp"] if samples else None,
                        self.feedback, self.pending, self.dirty, self.visible)
        if render_state == self._last_render_state:
            return setpoints
        self._last_render_state = render_state
        self.changed = True
        if setpoints is not None and not self.dirty and not self.pending and setpoints != self.last_setpoints:
            self.co2.set_val(setpoints.co2_ppm)
            self.humidity.set_val(setpoints.humidity_rh)
            self.last_setpoints = setpoints
        available = self.visible and state["supported"] and state["online"] and not self.pending
        self.save.set_active(available)
        for field in (self.co2, self.humidity):
            field.set_active(self.visible and not self.pending)
        self.heading.set_color(theme["text"])
        message = state["message"]
        if setpoints is None:
            message += " Displaying editable defaults; not saved to the device."
        if self.feedback:
            message = self.feedback + "\n" + message
        self.status.set_text(textwrap.fill(message, 68))
        self.status.set_color(theme["muted"])
        for field in (self.co2, self.humidity):
            field.style(theme)
        self.save.color = theme["card"] if available else theme["button_off"]
        self.save.hovercolor = theme["grid"]
        self.save.ax.set_facecolor(self.save.color)
        self.save.label.set_color(theme["text"])
        if self.visible:
            self._draw_graphs(state, theme, limits)
        return setpoints

    def _draw_graphs(self, state, theme, limits):
        frame = pd.DataFrame(state["samples"])
        for axis, channel, title in zip(self.graphs, ("humidity", "co2"),
                                         ("Humidity PI [%]", "CO2 PI [%]")):
            axis.clear()
            axis.set_facecolor(theme["plot"])
            axis.set_title(title, fontsize=10, fontweight="bold", color=theme["text"])
            for term, label, style in TERM_STYLES:
                timestamps = frame["timestamp"] if not frame.empty else []
                values = frame[f"{channel}_{term}"] if not frame.empty else []
                axis.plot(timestamps, values, label=label, color=CHANNEL_COLORS[channel],
                          linestyle=style, linewidth=1.4)
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
            if not has_terms:
                axis.text(0.5, 0.25, "Controller not configured" if not state["enabled"]
                          else "Waiting for controller data", ha="center", va="center",
                          color=theme["muted"], fontsize=9, transform=axis.transAxes)
