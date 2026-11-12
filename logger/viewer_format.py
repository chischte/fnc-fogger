"""Display rounding; recorded measurements retain their original precision."""
import math


def whole_percent(value):
    return "--" if value is None or not math.isfinite(value) else str(math.floor(value + 0.5))


def rounded_rpm(value):
    if value is None or not math.isfinite(value):
        return "--"
    step = 50 if value < 1000 else 100
    return str(math.floor(value / step + 0.5) * step)
