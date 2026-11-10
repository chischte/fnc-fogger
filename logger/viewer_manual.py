"""Independent manual actuator controls; slider edits are sent immediately."""
import queue

from matplotlib.widgets import Button, Slider

from .control_data import ManualOutputs


class ManualPanel:
    def __init__(self, figure, collector, on_change=lambda: None):
        self.figure = figure
        self.collector = collector
        self.on_change = on_change
        self.selected = False
        self.pending = False
        self.feedback = ""
        self.fan_on = False
        self.fogger_on = False
        self._initialized = False
        self._requested = None
        self.toggle = Button(figure.add_axes([0, 0, .1, .03]), "Manual Mode")
        self.fan = Slider(figure.add_axes([0, 0, .1, .03]), "Fan [%]", 0, 100,
                          valinit=0, valstep=1, valfmt="%0.0f")
        self.fogger = Slider(figure.add_axes([0, 0, .1, .03]), "Fogger [%]", 0, 100,
                             valinit=0, valstep=1, valfmt="%0.0f")
        self.fan_button = Button(figure.add_axes([0, 0, .1, .03]), "Fan Off")
        self.fogger_button = Button(figure.add_axes([0, 0, .1, .03]), "Fogger Off")
        self.stop = Button(figure.add_axes([0, 0, .1, .03]), "Stop All")
        self.toggle.on_clicked(self._toggle)
        self.fan_button.on_clicked(lambda event: self._toggle_output("fan"))
        self.fogger_button.on_clicked(lambda event: self._toggle_output("fogger"))
        self.stop.on_clicked(self._stop)
        self.fan.on_changed(self._edited)
        self.fogger.on_changed(self._edited)

    def _values(self):
        return ManualOutputs(self.selected,
                             int(self.fan.val) if self.selected and self.fan_on else 0,
                             int(self.fogger.val) if self.selected and self.fogger_on else 0)

    def _edited(self, value):
        if self.selected:
            self._send(self._values())

    def _toggle_output(self, output):
        attribute = output + "_on"
        setattr(self, attribute, not getattr(self, attribute))
        self._send(self._values())

    def _stop(self, event):
        self.fan_on = False
        self.fogger_on = False
        self._send(self._values())

    def _toggle(self, event):
        self.selected = not self.selected
        self.fan_on = False
        self.fogger_on = False
        self._send(self._values())

    def _send(self, outputs):
        if self.collector is None:
            return
        try:
            self.collector.submit_manual(outputs)
        except ValueError as error:
            self.fan_on = False
            self.fogger_on = False
            self.feedback = str(error)
            self.on_change()
            return
        self._requested = outputs
        self.pending = True
        self.feedback = "Sending manual outputs..."
        self.on_change()
        self.figure.canvas.draw_idle()

    def layout(self, box):
        def bounds(x, y, width, height):
            return [box.x0 + box.width*x, box.y0 + box.height*y,
                    box.width*width, box.height*height]
        self.toggle.ax.set_position(bounds(.55, .86, .42, .19))
        self.fan.ax.set_position(bounds(.20, .61, .54, .12))
        self.fogger.ax.set_position(bounds(.20, .37, .54, .12))
        self.fan_button.ax.set_position(bounds(.81, .58, .18, .18))
        self.fogger_button.ax.set_position(bounds(.81, .34, .18, .18))
        self.stop.ax.set_position(bounds(.25, .08, .50, .18))

    def set_visible(self, visible):
        self.toggle.ax.set_visible(visible)
        for widget in self._output_widgets():
            widget.ax.set_visible(visible and self.selected)

    def _output_widgets(self):
        return (self.fan, self.fogger, self.fan_button, self.fogger_button, self.stop)

    def _read_results(self, confirmed):
        if self.collector is None:
            return
        while True:
            try:
                success, message = self.collector.manual_results.get_nowait()
            except queue.Empty:
                return
            if not success:
                self.fan_on = False
                self.fogger_on = False
            if not success or confirmed == self._requested:
                self.pending = False
                self.feedback = message

    def update(self, state, visible, theme):
        confirmed = state.get("manual")
        self._read_results(confirmed)
        if confirmed is not None and not self._initialized:
            self._initialized = True
            if confirmed.active:
                self.selected = True
                self.fan_on = confirmed.fan_percent > 0
                self.fogger_on = confirmed.fogger_percent > 0
                for slider, value in ((self.fan, confirmed.fan_percent),
                                      (self.fogger, confirmed.fogger_percent)):
                    slider.eventson = False
                    slider.set_val(value)
                    slider.eventson = True
        if not state["online"] or (confirmed is not None and not confirmed.active and not self.pending):
            self.fan_on = False
            self.fogger_on = False
        available = visible and state["online"] and state.get("manual_supported", False)
        self.set_visible(visible)
        self.toggle.set_active(available)
        self.toggle.label.set_text("Exit Manual" if self.selected else "Manual Mode")
        for widget in self._output_widgets():
            widget.set_active(available and self.selected)
        self.fan_button.label.set_text("On" if self.fan_on else "Off")
        self.fogger_button.label.set_text("On" if self.fogger_on else "Off")
        for button, on in ((self.toggle, self.selected), (self.fan_button, self.fan_on),
                           (self.fogger_button, self.fogger_on), (self.stop, False)):
            button.color = theme["selected"] if on else theme["card"]
            if not button.active:
                button.color = theme["button_off"]
            button.hovercolor = theme["grid"]
            button.ax.set_facecolor(button.color)
            button.label.set_color("white" if on and button.active else theme["text"])
        for slider in (self.fan, self.fogger):
            slider.ax.set_facecolor(theme["card"])
            slider.label.set_color(theme["text"])
            slider.valtext.set_color(theme["text"])
        return (self.selected, self.pending, self.feedback, confirmed,
                self.fan_on, self.fogger_on, state.get("manual_supported", False))
