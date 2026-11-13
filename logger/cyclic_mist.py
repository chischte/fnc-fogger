"""Validated device-side cyclic mist settings and selectable minute values."""
from dataclasses import dataclass

MIST_TIME_LEVELS = tuple(range(0, 11))
MIST_PAUSE_LEVELS = tuple(range(10, 61))


@dataclass(frozen=True)
class CyclicMistSettings:
    enabled: bool = False
    mist_time_min: int = 1
    mist_pause_min: int = 10

    def __post_init__(self):
        if (not isinstance(self.enabled, bool)
                or type(self.mist_time_min) is not int
                or type(self.mist_pause_min) is not int
                or (self.enabled and self.mist_time_min == 0)
                or self.mist_time_min not in MIST_TIME_LEVELS
                or self.mist_pause_min not in MIST_PAUSE_LEVELS):
            raise ValueError("Mist time: 0 (off) or 1-10 min; pause: 10-60 min.")

    @classmethod
    def hourly(cls, minutes):
        return cls(minutes > 0, minutes, 60 - minutes)

    def fields(self):
        return {"enabled": int(self.enabled), "mist_time_min": self.mist_time_min,
                "mist_pause_min": self.mist_pause_min}

    @classmethod
    def from_payload(cls, payload):
        return cls(payload.get("enabled", False), payload.get("mist_time_min", 1),
                   payload.get("mist_pause_min", 10))
