"""Shared chart themes and fixed measurement scales."""

LIGHT_THEME = {
    "zoom_selection": "#007acc",
    "page": "#f3f6f4",
    "card": "#ffffff",
    "plot": "#f9faf9",
    "grid": "#d9e2dc",
    "text": "#2a3630",
    "muted": "#607068",
    "track": "#9aada6",
    "selected": "#3b8c62",
    "button_on": "#638372",
    "button_off": "#cdd3d0",
    "button_text_on": "#ffffff",
    "button_text_off": "#46504b",
}
DARK_THEME = {
    "zoom_selection": "#7ce8ff",
    "page": "#171e1b",
    "card": "#242e29",
    "plot": "#1d2621",
    "grid": "#3c4b43",
    "text": "#e6eee9",
    "muted": "#adbbb3",
    "track": "#778e81",
    "selected": "#78c79b",
    "button_on": "#638372",
    "button_off": "#3c4b43",
    "button_text_on": "#ffffff",
    "button_text_off": "#d3dfd7",
}

SERIES = [
    {"col": "humidity_corrected_rh", "label": "Humidity",    "unit": "%RH", "color": "#2878a8", "ymin": 85, "ymax": 100,   "step": 5,    "fmt": ".1f",
     "line_label": "Inbox (SHT45)",
     "overlay_col": "humidity_scd_rh",
     "overlay_color": "#78a9c4", "overlay_label": "Inbox (SCD41)", "overlay_style": ":",
     "extra_overlays": [{"col": "humidity_ambient_rh", "color": "#2878a8",
                         "style": "--", "label": "Ambient (SHTC3)"}]},
    {"col": "co2_ppm",     "label": "CO2",        "unit": "ppm", "color": "#7b2cbf", "ymin": 0,  "ymax": 15000, "step": None, "fmt": ".0f",
     "line_label": "SCD41"},
    {"col": "temp_box_c",  "label": "Temperature", "unit": "°C",  "color": "#d65a4a", "ymin": 20, "ymax": 30,    "step": 2,    "fmt": ".1f",
     "line_label": "Inbox (SHT45)", "ticks": [20, 22, 24, 26, 28, 30],
     "overlay_col": "temp_ambient_c", "overlay_color": "#e89489",
     "overlay_label": "Ambient (SHTC3)"},
]
