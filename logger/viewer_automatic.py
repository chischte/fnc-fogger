"""Operator actions for PI integrals and emergency recovery."""
import queue

from matplotlib.widgets import Button

EMERGENCY_COLOR = "#b3261e"
EMERGENCY_HOVER_COLOR = "#8c1d18"
EMERGENCY_TEXT_COLOR = "#ffffff"


class AutomaticPanel:
    def __init__(self, figure, collector, on_change):
        self.collector = collector
        self.on_change = on_change
        self.pending = False
        self.feedback = ""
        self.enabled = False
        self.emergency = False
        self.button = Button(figure.add_axes([0, 0, .1, .03]), "Reset PI")
        self.button.on_clicked(self._reset)

    def _reset(self, _event):
        if self.collector is None or self.pending:
            return
        try:
            if self.emergency:
                self.collector.submit_exit_emergency()
            else:
                self.collector.submit_pi_reset()
            self.pending = True
            self.feedback = "Exiting emergency..." if self.emergency else "Resetting PI integrals..."
        except ValueError as error:
            self.feedback = str(error)
        self.on_change()

    def layout(self, box):
        self.button.ax.set_position([box.x0 + box.width*.06, box.y0 + box.height*.76,
                                     box.width*.41, box.height*.17])

    def update(self, state, visible, manual_selected, theme):
        if self.collector is not None:
            while True:
                try:
                    _success, self.feedback = self.collector.automatic_results.get_nowait()
                    self.pending = False
                except queue.Empty:
                    break
        self.enabled = state["enabled"]
        self.emergency = (state.get("humidity_emergency", {}).get("active") is True
                          or state.get("emergency_ventilation", {}).get("active") is True
                          or state.get("fault") is True)
        self.button.label.set_text("Exit Emergency" if self.emergency else "Reset PI")
        action_supported = state.get("exit_emergency_supported" if self.emergency else "pi_reset_supported", False)
        supported = state.get("automatic_supported", False)
        self.button.ax.set_visible(visible and supported and not manual_selected)
        self.button.set_active(visible and supported and state["online"] and self.enabled
                               and action_supported and not self.pending)
        if self.emergency:
            self.button.color = EMERGENCY_COLOR
            self.button.hovercolor = EMERGENCY_HOVER_COLOR
            text_color = EMERGENCY_TEXT_COLOR
        else:
            self.button.color = theme["selected"] if self.enabled else theme["card"]
            self.button.hovercolor = theme["grid"]
            text_color = theme["page"] if self.enabled and self.button.active else theme["text"]
        self.button.ax.set_facecolor(self.button.color)
        self.button.label.set_color(text_color)
        return self.enabled, self.pending, self.feedback, supported, self.emergency, action_supported
