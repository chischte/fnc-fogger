"""
fnc-fogger – long-term data viewer
Discovers measurement lances and shows their stored and live measurements.

Requirements:
    pip install -r logger/requirements.txt
"""

import sys
from datetime import timedelta
from pathlib import Path
from functools import partial

if __package__:
    from . import viewer_data
    from .viewer_style import DARK_THEME, LIGHT_THEME, SERIES
    from .viewer_window import configure_viewer_window
    from .viewer_control import CommandPanel
    from .viewer_format import whole_percent
else:
    import viewer_data
    from viewer_style import DARK_THEME, LIGHT_THEME, SERIES
    from viewer_window import configure_viewer_window
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from logger.viewer_control import CommandPanel
    from logger.viewer_format import whole_percent

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import matplotlib.patches as mpatches
    from matplotlib.ticker import AutoLocator, FixedLocator, MultipleLocator
    from matplotlib.patches import FancyBboxPatch
    from matplotlib.widgets import Button
except ImportError:
    print("Missing dependencies. Run:  pip install matplotlib pandas")
    sys.exit(1)

CSV_FILE = Path(__file__).parent / "data" / "measurements.csv"
DB_FILE = Path(__file__).parent / "data" / "measurements.db"
REFRESH_INTERVAL_MS = 10_000
AXIS_DATE_FORMAT = "%d/%m/%y"
AXIS_LABEL_FONT_SIZE = 8

ADAPTIVE_BUTTON_CENTER_X = 0.825
DARK_MODE_BUTTON_CENTER_X = 0.175
TOGGLE_BUTTON_CENTER_Y = 0.0585
TOGGLE_BUTTON_WIDTH_INCHES = 1.69
TOGGLE_BUTTON_HEIGHT_INCHES = 0.37
CONTROL_ROW_TOP = 0.09
X_AXIS_LABEL_SPACE_INCHES = 0.45
CONTROL_BUTTON_GAP_INCHES = 0.10


def current_theme() -> dict:
    return DARK_THEME if _state["dark_mode"] else LIGHT_THEME



_state = {
    "range": "30m",
    "adaptive_y": True,
    "dark_mode": True,
    "manual_view": False,
}

RANGES = [
    ("all", "∞",      None),
    ("40d", "40d",    timedelta(days=40)),
    ("1w", "1w",      timedelta(weeks=1)),
    ("24h", "24h",    timedelta(hours=24)),
    ("3h", "3h",      timedelta(hours=3)),
    ("30m", "30min",  timedelta(minutes=30)),
    ("5m", "5min",    timedelta(minutes=5)),
]

RANGE_TRACK_START = 0.12
RANGE_TRACK_END = 0.88
RANGE_MINUS_X = 0.04
RANGE_PLUS_X = 0.96


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_data() -> pd.DataFrame:
    return viewer_data.load_data(DB_FILE, CSV_FILE)


def filter_data(df: pd.DataFrame) -> pd.DataFrame:
    delta = next(d for k, _, d in RANGES if k == _state["range"])
    if delta is None:
        return df
    cutoff = df["timestamp"].max() - delta
    return df[df["timestamp"] >= cutoff]


# ---------------------------------------------------------------------------
# Chart helpers
# ---------------------------------------------------------------------------

def format_xaxis(ax: "plt.Axes", df: pd.DataFrame) -> None:
    span = (df["timestamp"].max() - df["timestamp"].min()).total_seconds()

    def _fmt_with_midnight(x, pos):
        dt = mdates.num2date(x)
        if dt.hour == 0 and dt.minute == 0:
            return dt.strftime(f"{AXIS_DATE_FORMAT}\n00:00")
        return dt.strftime("%H:%M")

    def _bold_midnight():
        for label in ax.get_xticklabels():
            if "\n" in label.get_text():
                label.set_fontweight("bold")

    if _state["range"] == "1w":
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_with_midnight))
        t_max = df["timestamp"].max()
        ax.set_xlim(mdates.date2num(t_max - timedelta(weeks=1)), mdates.date2num(t_max))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        _bold_midnight()
    elif _state["range"] == "24h":
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_with_midnight))
        t_max = df["timestamp"].max()
        ax.set_xlim(mdates.date2num(t_max - timedelta(hours=24)), mdates.date2num(t_max))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        _bold_midnight()
    elif _state["range"] == "3h":
        ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=[0, 30]))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        t_max = df["timestamp"].max()
        ax.set_xlim(mdates.date2num(t_max - timedelta(hours=3)), mdates.date2num(t_max))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    elif _state["range"] == "5m":
        ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=1))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        t_max = df["timestamp"].max()
        ax.set_xlim(mdates.date2num(t_max - timedelta(minutes=5)), mdates.date2num(t_max))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    elif _state["range"] == "30m":
        ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 5)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        t_max = df["timestamp"].max()
        ax.set_xlim(mdates.date2num(t_max - timedelta(minutes=30)), mdates.date2num(t_max))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    elif span < 3600:
        ax.xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 5)))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    elif span < 86400:
        ax.xaxis.set_major_locator(mdates.HourLocator())
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_with_midnight))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        _bold_midnight()
    elif span < 7 * 86400:
        ax.xaxis.set_major_locator(mdates.HourLocator(byhour=range(0, 24, 6)))
        ax.xaxis.set_major_formatter(plt.FuncFormatter(_fmt_with_midnight))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        _bold_midnight()
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter(AXIS_DATE_FORMAT))
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def format_zoomed_xaxis(ax: "plt.Axes") -> None:
    locator = mdates.AutoDateLocator(
        minticks=5,
        maxticks=10,
        interval_multiples=True,
    )
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(
        locator,
        formats=[AXIS_DATE_FORMAT, AXIS_DATE_FORMAT, "%d", "%H:%M", "%H:%M", "%S.%f"],
        zero_formats=["", AXIS_DATE_FORMAT, AXIS_DATE_FORMAT, AXIS_DATE_FORMAT, "%H:%M", "%H:%M"],
        offset_formats=[
            "", AXIS_DATE_FORMAT, AXIS_DATE_FORMAT, AXIS_DATE_FORMAT,
            AXIS_DATE_FORMAT, f"{AXIS_DATE_FORMAT} %H:%M",
        ],
    ))
    ax.xaxis.get_offset_text().set_fontsize(AXIS_LABEL_FONT_SIZE)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def set_y_axis(ax: "plt.Axes", series: dict) -> None:
    if not _state["adaptive_y"]:
        ax.set_ylim(series["ymin"], series["ymax"])
        if "ticks" in series:
            locator = FixedLocator(series["ticks"])
        else:
            locator = MultipleLocator(series["step"]) if series["step"] else AutoLocator()
        ax.yaxis.set_major_locator(locator)
        return

    x_min, x_max = sorted(ax.get_xlim())
    visible_values = []
    for line in ax.lines:
        x_values = line.get_xdata(orig=False)
        y_values = line.get_ydata(orig=False)
        visible = (
            pd.notna(x_values)
            & pd.notna(y_values)
            & (x_values >= x_min)
            & (x_values <= x_max)
        )
        visible_values.extend(y_values[visible])

    if not visible_values:
        return

    visible_min = min(visible_values)
    visible_max = max(visible_values)
    visible_span = visible_max - visible_min
    padding = visible_span * 0.08 if visible_span else max(abs(visible_min) * 0.05, 0.5)
    ax.set_ylim(visible_min - padding, visible_max + padding)
    ax.yaxis.set_major_locator(AutoLocator())


def synchronize_x_axes(chart_axes: list, source_axis: "plt.Axes") -> None:
    x_limits = source_axis.get_xlim()
    for axis in chart_axes:
        if axis is not source_axis:
            axis.set_xlim(x_limits)


def position_toggle_button(fig: "plt.Figure", button_axis: "plt.Axes",
                           center_x: float) -> None:
    width = TOGGLE_BUTTON_WIDTH_INCHES / fig.get_figwidth()
    height = TOGGLE_BUTTON_HEIGHT_INCHES / fig.get_figheight()
    button_axis.set_position([
        center_x - width / 2,
        TOGGLE_BUTTON_CENTER_Y - height / 2,
        width,
        height,
    ])


def style_toggle_button(button: Button, background: FancyBboxPatch,
                        label: str, enabled: bool) -> None:
    theme = current_theme()
    button.color = theme["page"]
    button.hovercolor = theme["page"]
    button.ax.set_facecolor(theme["page"])
    button.label.set_text(f"{label}: {'on' if enabled else 'off'}")
    button.label.set_color(theme["button_text_on" if enabled else "button_text_off"])
    background.set_facecolor(theme["button_on" if enabled else "button_off"])


def create_toggle_button(fig: "plt.Figure", center_x: float,
                         label: str, enabled: bool) -> tuple[Button, FancyBboxPatch]:
    button_axis = fig.add_axes([0, 0, 0.13, 0.035])
    position_toggle_button(fig, button_axis, center_x)
    button = Button(button_axis, "")
    for spine in button_axis.spines.values():
        spine.set_visible(False)
    background = FancyBboxPatch(
        (0, 0), 1, 1,
        boxstyle="round,pad=0.02,rounding_size=0.24",
        linewidth=0, transform=button_axis.transAxes, zorder=1,
    )
    button_axis.add_patch(background)
    button.label.set_fontsize(9.5)
    button.label.set_fontweight("bold")
    button.label.set_zorder(2)
    style_toggle_button(button, background, label, enabled)
    return button, background


def plot_series(ax: "plt.Axes", df: pd.DataFrame, s: dict) -> None:
    theme = current_theme()
    ax.clear()
    col = s["col"]
    humidity = col == "humidity_corrected_rh"
    def offset_label(label, column):
        if not humidity or column not in df or df.empty:
            return label
        offset = df[column].iloc[-1]
        return f"{label} ({offset:+.1f}%RH)" if pd.notna(offset) else label
    ax.fill_between(df["timestamp"], df[col], s["ymin"],
                    color=s["color"], alpha=0.12, zorder=2)
    ax.plot(df["timestamp"], df[col], color=s["color"], linewidth=1.5, zorder=3,
            label=offset_label(s.get("line_label", "Box"), "humidity_offset_rh"))

    overlays = list(s.get("extra_overlays", []))
    if s.get("overlay_col"):
        overlays.insert(0, {"col": s["overlay_col"], "color": s["overlay_color"],
                            "style": s.get("overlay_style", "--"),
                            "label": offset_label(s.get("overlay_label", "Ambient"), "scd_humidity_offset_rh")})
    for overlay in overlays:
        if overlay["col"] not in df.columns:
            continue
        overlay_column = ("humidity_scd_corrected_rh" if overlay["col"] == "humidity_scd_rh"
                          and "humidity_scd_corrected_rh" in df else overlay["col"])
        ax.plot(df["timestamp"], df[overlay_column], color=overlay["color"],
                linewidth=1.2, linestyle=overlay["style"], zorder=4,
                label=overlay["label"])
    if overlays or s.get("line_label"):
        ax.legend(fontsize=8, loc="upper left", framealpha=0.7,
                  facecolor=theme["card"], edgecolor=theme["grid"],
                  labelcolor=theme["text"])

    ax.set_title(f'{s["label"]} [{s["unit"]}]', fontsize=10, fontweight="bold",
                 color=theme["text"], pad=6)
    ax.set_facecolor(theme["plot"])
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(theme["grid"])
    ax.tick_params(colors=theme["muted"], labelsize=AXIS_LABEL_FONT_SIZE)
    ax.xaxis.get_offset_text().set_color(theme["muted"])
    ax.xaxis.get_offset_text().set_fontsize(AXIS_LABEL_FONT_SIZE)
    ax.yaxis.get_offset_text().set_color(theme["muted"])
    ax.grid(True, linestyle="--", linewidth=0.6, color=theme["grid"], zorder=1)
    format_xaxis(ax, df)
    set_y_axis(ax, s)


# ---------------------------------------------------------------------------
# Value boxes (like the website cards)
# ---------------------------------------------------------------------------

def draw_control_values(ax, value, series, setpoints, control_state):
    target = None
    if setpoints is not None:
        target = setpoints.humidity_rh if series["col"] == "humidity_corrected_rh" else setpoints.co2_ppm
    difference = value - target if target is not None and pd.notna(value) else None
    output = None
    if control_state and control_state["online"] and control_state["enabled"] and not control_state.get("fault"):
        samples = control_state["samples"]
        channel = "humidity" if series["col"] == "humidity_corrected_rh" else "co2"
        if samples:
            output = samples[-1].get(f"{channel}_sum")
    fields = (("SET:", f"{target:g}" if target is not None else "--"),
              ("DIF:", format(difference, "+" + series["fmt"]) if difference is not None else "--"),
              ("PI%:", whole_percent(output)))
    for y, (label, text) in zip((0.78, 0.49, 0.20), fields):
        for x, content, alignment in ((0.62, label, "left"), (0.95, text, "right")):
            ax.text(x, y, content, ha=alignment, va="center", fontsize=11,
                    fontweight="bold", color=current_theme()["muted"],
                    transform=ax.transAxes, zorder=2)


def draw_value_boxes(box_axes: list, last: pd.Series, setpoints=None, control_state=None) -> None:
    theme = current_theme()
    for ax, s in zip(box_axes, SERIES):
        ax.clear()
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")

        # Card background with border
        card = FancyBboxPatch((0.03, 0.05), 0.94, 0.90,
                              boxstyle="round,pad=0.02",
                              linewidth=1, edgecolor=theme["grid"],
                              facecolor=theme["card"],
                              transform=ax.transAxes, zorder=1,
                              clip_on=False)
        ax.add_patch(card)

        val = last[s["col"]]
        val_str = format(val, s["fmt"]) if pd.notna(val) else "--"

        val_y = 0.45
        value_x = 0.32 if s["col"] != "temp_box_c" else 0.5

        # Label (top, bold, muted grey)
        ax.text(value_x, 0.78, s["label"],
                ha="center", va="center", fontsize=10, fontweight="bold",
                color=theme["muted"], transform=ax.transAxes, zorder=2)
        ax.text(value_x, val_y, val_str,
                ha="center", va="center", fontsize=22, fontweight="bold",
                color=s["color"], transform=ax.transAxes, zorder=2)
        if s["col"] == "temp_box_c":
            ambient = last.get("temp_ambient_c")
            if pd.notna(val) and pd.notna(ambient):
                ax.text(0.82, val_y, f"{val - ambient:+.1f}",
                        ha="center", va="center", fontsize=11, fontweight="bold",
                        color=s["overlay_color"], transform=ax.transAxes, zorder=2)
        else:
            draw_control_values(ax, val, s, setpoints, control_state)
        ax.text(value_x, 0.13, s["unit"],
                ha="center", va="center", fontsize=10, fontweight="bold",
                color=theme["muted"], transform=ax.transAxes, zorder=2)


# ---------------------------------------------------------------------------
# Range selector
# ---------------------------------------------------------------------------

def range_selector_positions() -> list[float]:
    spacing = (RANGE_TRACK_END - RANGE_TRACK_START) / (len(RANGES) - 1)
    return [RANGE_TRACK_START + index * spacing for index in range(len(RANGES))]


def draw_range_selector(range_axis: "plt.Axes") -> None:
    theme = current_theme()
    range_axis.clear()
    range_axis.set_xlim(0, 1)
    range_axis.set_ylim(0, 1)
    range_axis.axis("off")

    card = FancyBboxPatch((0.01, 0.08), 0.98, 0.84,
                          boxstyle="round,pad=0.02",
                          linewidth=1, edgecolor=theme["grid"],
                          facecolor=theme["card"],
                          transform=range_axis.transAxes, zorder=1,
                          clip_on=False)
    range_axis.add_patch(card)

    track_y = 0.60
    label_y = 0.22
    positions = range_selector_positions()
    range_axis.plot(
        [RANGE_TRACK_START, RANGE_TRACK_END], [track_y, track_y],
        color=theme["track"], linewidth=1.5,
        transform=range_axis.transAxes, zorder=2,
    )
    range_axis.text(
        RANGE_MINUS_X, track_y, "−",
        ha="center", va="center", fontsize=15, fontweight="bold",
        color=theme["button_text_off"], transform=range_axis.transAxes, zorder=3,
    )
    range_axis.text(
        RANGE_PLUS_X, track_y, "+",
        ha="center", va="center", fontsize=14, fontweight="bold",
        color=theme["button_text_off"], transform=range_axis.transAxes, zorder=3,
    )

    for position, (key, label, _) in zip(positions, RANGES):
        selected = _state["range"] == key
        marker_width = 0.075 if selected else 0.051
        marker_height = 0.100 if selected else 0.068
        marker = mpatches.Ellipse(
            (position, track_y),
            width=marker_width,
            height=marker_height,
            edgecolor=theme["selected"] if selected else theme["track"],
            facecolor=theme["selected"] if selected else theme["card"],
            linewidth=1.2, transform=range_axis.transAxes, zorder=3,
        )
        range_axis.add_patch(marker)
        range_axis.text(
            position, label_y, label,
            ha="center", va="center", fontsize=8,
            color=theme["text"] if selected else theme["muted"],
            fontweight="bold" if selected else "normal",
            transform=range_axis.transAxes, zorder=3,
        )

    range_axis.figure.canvas.draw_idle()


def range_index_for_click(x_position: float) -> int:
    current_index = next(
        index for index, (key, _, _) in enumerate(RANGES)
        if key == _state["range"]
    )
    if x_position <= (RANGE_MINUS_X + RANGE_TRACK_START) / 2:
        return max(0, current_index - 1)
    if x_position >= (RANGE_PLUS_X + RANGE_TRACK_END) / 2:
        return min(len(RANGES) - 1, current_index + 1)

    positions = range_selector_positions()
    return min(
        range(len(positions)),
        key=lambda index: abs(positions[index] - x_position),
    )


# ---------------------------------------------------------------------------
# Main draw loop
# ---------------------------------------------------------------------------

def draw(fig: "plt.Figure", box_axes: list, chart_axes: list,
         range_axis: "plt.Axes", footer_text: "plt.Text",
         preserve_view: bool = False, data_cache=None,
         skip_unchanged: bool = False, database=None, csv=None, control_monitor=None) -> None:
    preserved_limits = (
        [(axis.get_xlim(), axis.get_ylim()) for axis in chart_axes]
        if preserve_view else None
    )

    try:
        previous_revision = data_cache.revision if data_cache else None
        df_all = data_cache.load(database or DB_FILE, csv or CSV_FILE) if data_cache else load_data()
        if skip_unchanged and data_cache and data_cache.revision == previous_revision:
            return
    except Exception as exc:
        print(f"Could not read measurements: {exc}", file=sys.stderr)
        return

    df = filter_data(df_all)
    if df.empty:
        footer_text.set_text("No measurements yet. Waiting for the selected lance …")
        footer_text.set_color(current_theme()["muted"])
        fig.canvas.draw_idle()
        return

    last = df_all.iloc[-1]
    ts = last["timestamp"]

    control_state = control_monitor.snapshot() if control_monitor else None
    setpoints = control_state["setpoints"] if control_state else None
    draw_value_boxes(box_axes, last, setpoints, control_state)
    for ax, s in zip(chart_axes, SERIES):
        plot_series(ax, df, s)
    if preserved_limits:
        for axis, series, (x_limits, y_limits) in zip(chart_axes, SERIES, preserved_limits):
            axis.set_xlim(x_limits)
            format_zoomed_xaxis(axis)
            if _state["adaptive_y"]:
                set_y_axis(axis, series)
            else:
                axis.set_ylim(y_limits)
    draw_range_selector(range_axis)

    footer_text.set_text(
        f"Last Reading:  {ts.strftime(AXIS_DATE_FORMAT)}  {ts.strftime('%H:%M:%S')}"
        f"   |   {len(df_all)} data points"
    )

    fig.set_facecolor(current_theme()["page"])
    footer_text.set_color(current_theme()["muted"])
    fig.canvas.draw_idle()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@plt.rc_context({"font.family": "Segoe UI" if sys.platform == "win32" else "DejaVu Sans",
                 "font.weight": "semibold", "axes.labelweight": "semibold"})
def show_charts(database=DB_FILE, csv=CSV_FILE, title="Lance", collector=None,
                actuators_installed=None) -> bool:
    render = partial(draw, database=database, csv=csv,
                     control_monitor=collector.control if collector else None)
    return_home = False
    _state["manual_view"] = False

    data_cache = viewer_data.MeasurementCache()
    fig = plt.figure(figsize=(11, 8.5))
    fig.patch.set_facecolor(current_theme()["page"])
    fig.canvas.manager.set_window_title(title)
    title_text = fig.text(0.5, 0.955, title, color=current_theme()["text"],
                          fontsize=12, fontweight="semibold", ha="center", va="center")
    home_axis = fig.add_axes([0.02, 0.935, 0.18, 0.04])
    home_button = Button(home_axis, "device overview", color=current_theme()["button_off"],
                         hovercolor=current_theme()["grid"])
    home_button.label.set_color(current_theme()["text"])
    command_mode = (bool(collector and collector.lance.actuators_installed)
                    if actuators_installed is None else bool(actuators_installed))

    def _home(_event):
        nonlocal return_home
        return_home = True
        plt.close(fig)

    home_button.on_clicked(_home)
    window_controls = configure_viewer_window(fig)
    if window_controls is not None:
        window_controls.apply_theme(current_theme())

    from matplotlib.gridspec import GridSpec, GridSpecFromSubplotSpec

    # Outer grid: row 0 = boxes, row 1 = charts block, row 2 = toggle
    gs_outer = GridSpec(
        3, 1,
        figure=fig,
        height_ratios=[1, 6.5, 0.01],
        hspace=0.12,          # gap between boxes row and charts block
        top=0.91,
        bottom=CONTROL_ROW_TOP + X_AXIS_LABEL_SPACE_INCHES / fig.get_figheight(),
        left=0.07, right=0.97,
    )

    # Inner grid for the 3 charts — controls spacing between charts only
    gs_charts = GridSpecFromSubplotSpec(
        3, 2,
        subplot_spec=gs_outer[1],
        width_ratios=(3, 2),
        hspace=0.52,
        wspace=0.22,
    )

    # Value boxes (top row, one per column)
    gs_boxes = GridSpecFromSubplotSpec(1, 3, subplot_spec=gs_outer[0], wspace=0.28)
    box_axes = [fig.add_subplot(gs_boxes[0, i]) for i in range(3)]

    # Charts
    chart_axes = [fig.add_subplot(gs_charts[r, 0] if command_mode else gs_charts[r, :])
                  for r in range(3)]
    command_panel = CommandPanel(fig, gs_charts, collector, database=database)

    command_panel.set_visible(command_mode)

    # Range selector flanked by matching theme and adaptive Y toggles.
    range_axis = fig.add_axes([0.32, 0.030, 0.36, 0.060])
    adaptive_button, adaptive_button_background = create_toggle_button(
        fig, ADAPTIVE_BUTTON_CENTER_X, "adaptive y", _state["adaptive_y"]
    )
    dark_mode_button, dark_mode_button_background = create_toggle_button(
        fig, DARK_MODE_BUTTON_CENTER_X, "dark mode", _state["dark_mode"]
    )

    # Footer text at very bottom
    footer_text = fig.text(
        0.5, 0.008, "",
        ha="center", va="bottom",
        fontsize=8, color=current_theme()["muted"], fontfamily="monospace",
    )

    render(fig, box_axes, chart_axes, range_axis, footer_text, data_cache=data_cache)
    command_panel.update(current_theme(), chart_axes[0].get_xlim())

    # Minus/plus step through the ranges; labels and markers select directly.
    def _on_click(event):
        if event.inaxes is range_axis and event.xdata is not None:
            idx = range_index_for_click(event.xdata)
            _state["range"] = RANGES[idx][0]
            _state["manual_view"] = False
            render(fig, box_axes, chart_axes, range_axis, footer_text, data_cache=data_cache)
            command_panel.update(current_theme(), chart_axes[0].get_xlim())
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_press_event", _on_click)

    def _toggle_adaptive_y(_event):
        _state["adaptive_y"] = not _state["adaptive_y"]
        style_toggle_button(
            adaptive_button, adaptive_button_background, "adaptive y", _state["adaptive_y"]
        )
        for axis, series in zip(chart_axes, SERIES):
            set_y_axis(axis, series)
        fig.canvas.draw_idle()

    adaptive_button.on_clicked(_toggle_adaptive_y)

    def _toggle_dark_mode(_event):
        _state["dark_mode"] = not _state["dark_mode"]
        title_text.set_color(current_theme()["text"])
        home_button.color = current_theme()["button_off"]
        home_button.hovercolor = current_theme()["grid"]
        home_button.ax.set_facecolor(home_button.color)
        home_button.label.set_color(current_theme()["text"])
        command_panel.update(current_theme(), chart_axes[0].get_xlim())
        if window_controls is not None:
            window_controls.apply_theme(current_theme())
        limits = [(axis.get_xlim(), axis.get_ylim()) for axis in chart_axes]
        render(
            fig, box_axes, chart_axes, range_axis, footer_text,
            preserve_view=_state["manual_view"], data_cache=data_cache,
        )
        for axis, (x_limits, y_limits) in zip(chart_axes, limits):
            axis.set_xlim(x_limits)
            axis.set_ylim(y_limits)
        style_toggle_button(
            adaptive_button, adaptive_button_background, "adaptive y", _state["adaptive_y"]
        )
        style_toggle_button(
            dark_mode_button, dark_mode_button_background, "dark mode", _state["dark_mode"]
        )
        fig.canvas.draw_idle()

    dark_mode_button.on_clicked(_toggle_dark_mode)

    def _layout_controls(_event=None):
        adaptive_center = ADAPTIVE_BUTTON_CENTER_X
        dark_mode_center = DARK_MODE_BUTTON_CENTER_X
        if window_controls is not None:
            spacing = (CONTROL_BUTTON_GAP_INCHES + TOGGLE_BUTTON_WIDTH_INCHES / 2)
            dark_mode_center = max(
                dark_mode_center,
                window_controls.zoom_button_right() + spacing / fig.get_figwidth(),
            )
            adaptive_center = min(
                adaptive_center,
                window_controls.icon_buttons_left() - spacing / fig.get_figwidth(),
            )
        position_toggle_button(fig, adaptive_button.ax, adaptive_center)
        position_toggle_button(fig, dark_mode_button.ax, dark_mode_center)

        gs_outer.update(
            bottom=CONTROL_ROW_TOP + X_AXIS_LABEL_SPACE_INCHES / fig.get_figheight()
        )
        command_panel.layout()

    _layout_controls()
    fig.canvas.mpl_connect("resize_event", _layout_controls)

    def _remember_manual_view(event):
        if event.inaxes in chart_axes:
            toolbar = getattr(fig.canvas, "toolbar", None)
            if toolbar and toolbar.mode:
                _state["manual_view"] = True
                synchronize_x_axes(chart_axes, event.inaxes)
                for axis in chart_axes:
                    format_zoomed_xaxis(axis)
            if _state["adaptive_y"]:
                for axis, series in zip(chart_axes, SERIES):
                    set_y_axis(axis, series)
            command_panel.update(current_theme(), chart_axes[0].get_xlim())
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("button_release_event", _remember_manual_view)

    def _remember_scroll_zoom(event):
        if event.inaxes in chart_axes:
            _state["manual_view"] = True
            synchronize_x_axes(chart_axes, event.inaxes)
            for axis in chart_axes:
                format_zoomed_xaxis(axis)
            if _state["adaptive_y"]:
                for axis, series in zip(chart_axes, SERIES):
                    set_y_axis(axis, series)
            command_panel.update(current_theme(), chart_axes[0].get_xlim())
            fig.canvas.draw_idle()

    fig.canvas.mpl_connect("scroll_event", _remember_scroll_zoom)

    last_plot_revision = data_cache.revision

    def _update(_frame):
        nonlocal last_plot_revision
        render(
            fig,
            box_axes,
            chart_axes,
            range_axis,
            footer_text,
            preserve_view=_state["manual_view"], data_cache=data_cache,
            skip_unchanged=data_cache.revision == last_plot_revision,
        )
        last_plot_revision = data_cache.revision
        command_panel.update(current_theme(), chart_axes[0].get_xlim())

    connection_text = fig.text(0.5, 0.925, "connecting …" if collector else "",
                               ha="center", fontsize=8.5, fontweight="medium", color=current_theme()["muted"])
    last_setpoints = None
    last_card_state = None

    def _connection_status():
        nonlocal last_setpoints, last_card_state
        status = collector.latest_status() if collector else None
        if status:
            status = status[:1].lower() + status[1:]
        if status and status != connection_text.get_text():
            connection_text.set_text(status)
            connection_text.set_color(current_theme()["muted"])
            fig.canvas.draw_idle()
        setpoints = command_panel.update(current_theme(), chart_axes[0].get_xlim())
        if setpoints != last_setpoints:
            last_setpoints = setpoints
            render(fig, box_axes, chart_axes, range_axis, footer_text,
                   preserve_view=_state["manual_view"], data_cache=data_cache)
        if command_mode and command_panel.changed:
            fig.canvas.draw_idle()
        if collector:
            try:
                frame = data_cache.load(database, csv)
                if not frame.empty:
                    state = collector.control.snapshot()
                    samples = state["samples"]
                    card_state = (data_cache.revision, state["setpoints"], state["online"],
                                  state["enabled"], samples[-1]["timestamp"] if samples else None)
                    if card_state != last_card_state:
                        last_card_state = card_state
                        draw_value_boxes(box_axes, frame.iloc[-1], state["setpoints"], state)
                        fig.canvas.draw_idle()
            except Exception as error:
                message = f"Could not read measurements: {error}"
                if message != connection_text.get_text():
                    connection_text.set_text(message)
                    fig.canvas.draw_idle()

    status_timer = fig.canvas.new_timer(interval=1000)
    status_timer.add_callback(_connection_status)
    status_timer.start()
    refresh_timer = fig.canvas.new_timer(interval=REFRESH_INTERVAL_MS)
    refresh_timer.add_callback(_update, None)
    refresh_timer.start()

    try:
        plt.show()
    finally:
        refresh_timer.stop()
        status_timer.stop()
        data_cache.close()
    return return_home


def main() -> None:
    # Script launches must also support package-relative discovery modules.
    if not __package__:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    try:
        from logger.viewer_selection import LanceSelection
        from logger.lance_collection import LanceCollector
        from logger import logger as acquisition
        from logger.background_process import ensure_background_logger
    except ImportError as error:
        print(f"Missing dependency: {error}. Run: pip install -r logger/requirements.txt",
              file=sys.stderr)
        return

    ensure_background_logger(DB_FILE.parent)
    while True:
        selection = LanceSelection(DB_FILE.parent)
        lance = selection.show()
        if lance is None:
            return
        database = selection.registry.measurement_path(lance)
        # A newly registered device may precede the background worker by one scan.
        acquisition.connect(database).close()
        collector = LanceCollector(lance, database)
        collector.start()
        title = lance.label + (f" @ {lance.location}" if lance.location else "")
        try:
            return_home = show_charts(database, database.with_suffix(".csv"), title, collector)
        finally:
            collector.stop()
        if not return_home:
            return


if __name__ == "__main__":
    main()


