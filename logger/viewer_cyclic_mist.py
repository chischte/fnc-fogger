"""Single-row cyclic mist timing; zero ON minutes disables the saved cycle."""
import queue

from matplotlib.patches import Rectangle

from .cyclic_mist import CyclicMistSettings, MIST_TIME_LEVELS
from .viewer_stepper import SetpointStepper


class CyclicMistPanel:
    def __init__(self, figure, collector, on_change, panel_axis):
        self.frame = Rectangle((0, 0), 1, .24, transform=panel_axis.transAxes,
                               linewidth=1, clip_on=False, zorder=0)
        panel_axis.add_patch(self.frame)
        self.collector = collector
        self.on_change = on_change
        self.enabled = False
        self.pending = False
        self.feedback = ""
        self.requested = None
        self.mist_time = SetpointStepper(figure, "Mist Time [min]", MIST_TIME_LEVELS, self._edited)
        self.mist_time.set_val(0)
        self.label_axis = figure.add_axes([0, 0, .1, .03])
        self.label_axis.axis("off")
        self.label = self.label_axis.text(0, .5, "Cyclic Mist [min/h]", va="center", fontsize=9)
        self.set_visible(False)

    def _edited(self, _value):
        self._send()

    def _send(self):
        if self.collector is None:
            return
        self.enabled = self.mist_time.value > 0
        values = CyclicMistSettings.hourly(int(self.mist_time.value))
        try:
            self.collector.submit_cyclic_mist(values)
            self.requested = values
            self.pending = True
            self.feedback = "Saving cyclic mist on device..."
        except ValueError as error:
            self.feedback = str(error)
        self.on_change()

    def _read_results(self):
        if self.collector is None:
            return
        while True:
            try:
                _success, message, values = self.collector.cyclic_mist_results.get_nowait()
            except queue.Empty:
                return
            if values == self.requested:
                self.pending = False
                self.feedback = message

    def layout(self, box, reference):
        row_bottom = box.y0 + box.height*.04
        row_height = box.height*.16
        label_left = reference.ax.get_position().x0
        minus_bounds = reference.minus.ax.get_position()
        plus_bounds = reference.plus.ax.get_position()
        self.label_axis.set_position([label_left, row_bottom,
                                      minus_bounds.x0 - label_left - box.width*.02, row_height])
        field = self.mist_time
        left = minus_bounds.x0
        width = plus_bounds.x1 - left
        field.ax.set_position([left, row_bottom, width, row_height])
        field.minus.ax.set_position([minus_bounds.x0, row_bottom, minus_bounds.width, row_height])
        field.plus.ax.set_position([plus_bounds.x0, row_bottom, plus_bounds.width, row_height])
        field.label.set_position((.5, .5))
        field.label.set_ha("center")
        field.label.set_text(f"{field.value:g}")
        field.label.set_fontsize(9)
        field.value_text.set_visible(False)
        for button in (field.minus, field.plus):
            button.label.set_fontsize(9)

    def set_visible(self, visible):
        self.frame.set_visible(visible)
        for axis in self.mist_time.axes:
            axis.set_visible(visible)
        self.mist_time.set_active(False)
        self.label_axis.set_visible(visible)

    def update(self, state, visible, theme):
        self._read_results()
        cyclic = state.get("cyclic_mist", {})
        supported = cyclic.get("supported") is True
        if supported and not self.pending:
            confirmed = CyclicMistSettings.from_payload(cyclic)
            self.enabled = confirmed.enabled
            self.mist_time.set_val(confirmed.mist_time_min if confirmed.enabled else 0)
        available = (visible and supported and state["online"]
                     and ((state["enabled"] and not state.get("fault")) or self.enabled))
        self.set_visible(visible and supported)
        self.mist_time.set_active(available)
        self.mist_time.style(theme)
        self.mist_time.label.set_text(f"{self.mist_time.value:g}")
        self.label.set_color(theme["text"])
        self.frame.set_edgecolor(theme["grid"])
        self.frame.set_facecolor(theme["plot"])
        return self.enabled, self.pending, self.feedback, supported, cyclic.get("misting")
