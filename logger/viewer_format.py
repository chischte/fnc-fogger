"""Display rounding; recorded measurements retain their original precision."""
import math


def whole_percent(value):
    return "--" if value is None or not math.isfinite(value) else str(math.floor(value + 0.5))


def format_rpm(value):
    if value is None or not math.isfinite(value):
        return "--"
    return str(math.floor(value / 10 + 0.5) * 10)
