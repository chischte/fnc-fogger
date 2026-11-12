"""Reset firmware PI integrals without changing mode or tuning."""
import queue

from matplotlib.widgets import Button


class AutomaticPanel:
    def __init__(self, figure, collector, on_change):
        self.collector = collector
        self.on_change = on_change
        self.pending = False
        self.feedback = ""
        self.enabled = False
        self.button = Button(figure.add_axes([0, 0, .1, .03]), "Reset PI")
        self.button.on_clicked(self._reset)

    def _reset(self, _event):
        if self.collector is None or self.pending:
            return
        try:
            self.collector.submit_pi_reset()
            self.pending = True
            self.feedback = "Resetting PI integrals..."
        except ValueError as error:
            self.feedback = str(error)
        self.on_change()

    def layout(self, box):
        self.button.ax.set_position([box.x0 + box.width*.04, box.y0 + box.height*.86,
                                     box.width*.42, box.height*.19])

    def update(self, state, visible, manual_selected, theme):
        if self.collector is not None:
            while True:
                try:
                    _success, self.feedback = self.collector.automatic_results.get_nowait()
                    self.pending = False
                except queue.Empty:
                    break
        self.enabled = state["enabled"]
        supported = state.get("automatic_supported", False)
        self.button.ax.set_visible(visible and supported and not manual_selected)
        self.button.set_active(visible and supported and state["online"] and self.enabled
                               and state.get("pi_reset_supported", False) and not self.pending)
        self.button.color = theme["selected"] if self.enabled else theme["card"]
        self.button.hovercolor = theme["grid"]
        self.button.ax.set_facecolor(self.button.color)
        self.button.label.set_color(theme["page"] if self.enabled and self.button.active else theme["text"])
        return self.enabled, self.pending, self.feedback, supported
