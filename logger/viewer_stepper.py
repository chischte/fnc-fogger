"""Read-only setpoint values with bounded minus/plus controls."""
from bisect import bisect_left, bisect_right

from matplotlib.widgets import Button

CO2_LEVELS = (tuple(range(500, 2001, 100))
              + tuple(range(2500, 5001, 500))
              + tuple(range(6000, 15001, 1000)))
HUMIDITY_LEVELS = tuple(range(70, 100))


class SetpointStepper:
    def __init__(self, figure, label, levels, on_change):
        self.levels = levels
        self.on_change = on_change
        self.value = None
        self.active = False
        self.ax = figure.add_axes([0, 0, 0.1, 0.03])
        self.ax.axis("off")
        self.label = self.ax.text(0, 0.5, label, fontsize=9, va="center")
        self.value_text = self.ax.text(0.65, 0.5, "--", fontsize=11,
                                       fontweight="semibold", ha="center", va="center")
        self.minus = Button(figure.add_axes([0, 0, 0.03, 0.03]), "−")
        self.plus = Button(figure.add_axes([0, 0, 0.03, 0.03]), "+")
        self.minus.on_clicked(lambda event: self._step(-1))
        self.plus.on_clicked(lambda event: self._step(1))

    @property
    def axes(self):
        return [self.ax, self.minus.ax, self.plus.ax]

    def set_val(self, value):
        self.value = value
        self.value_text.set_text(f"{value:g}")
        self.set_active(self.active)

    def set_active(self, active):
        self.active = active
        self.minus.set_active(active and self.value is not None and self.value > self.levels[0])
        self.plus.set_active(active and self.value is not None and self.value < self.levels[-1])

    def _step(self, direction):
        if not self.active or self.value is None:
            return
        index = bisect_right(self.levels, self.value) if direction > 0 else bisect_left(self.levels, self.value) - 1
        index = max(0, min(index, len(self.levels) - 1))
        value = self.levels[index]
        if value == self.value:
            return
        self.set_val(value)
        self.on_change(value)
        self.ax.figure.canvas.draw_idle()

    def layout(self, bounds):
        left, bottom, width, height = bounds
        self.ax.set_position(bounds)
        self.minus.ax.set_position([left + width * 0.40, bottom, width * 0.12, height])
        self.plus.ax.set_position([left + width * 0.82, bottom, width * 0.12, height])

    def style(self, theme):
        self.label.set_color(theme["text"])
        self.value_text.set_color(theme["text"])
        for button in (self.minus, self.plus):
            button.color = theme["card"] if button.active else theme["button_off"]
            button.hovercolor = theme["grid"]
            button.ax.set_facecolor(button.color)
            button.label.set_color(theme["text"] if button.active else theme["muted"])
