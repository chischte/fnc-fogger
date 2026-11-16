"""Plot recorded actuator demand during settled automatic humidity control."""
import argparse
import json
import sqlite3
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

TIMEZONE = "Europe/Zurich"
REPLACEMENT = pd.Timestamp("2026-11-14 04:20", tz=TIMEZONE)
SETTLED_SECONDS = 15 * 60
MAX_GAP_SECONDS = 15
HUMIDITY_TOLERANCE = 2


def load_samples(database):
    query = """SELECT c.received_at, c.boot_id, c.mode, c.fogger_percent,
        c.fan_pwm_percent, c.fan_rpm, c.humidity_setpoint_rh, c.control_json,
        m.humidity_rh, m.humidity_offset_rh, m.valid_humidity,
        m.uptime_ms, m.sht_read_uptime_ms
        FROM control_samples c LEFT JOIN measurements m
        ON c.boot_id=m.boot_id AND c.measurement_sequence=m.sequence
        ORDER BY c.received_at"""
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        frame = pd.read_sql_query(query, connection)
    frame["timestamp"] = pd.to_datetime(frame.pop("received_at"), utc=True, format="mixed").dt.tz_convert(TIMEZONE)
    frame.sort_values("timestamp", inplace=True, ignore_index=True)
    frame["humidity"] = (frame["humidity_rh"] + frame["humidity_offset_rh"].fillna(0)).clip(0, 100)
    frame["error"] = frame["humidity"] - frame["humidity_setpoint_rh"]
    controls = frame.pop("control_json").map(json.loads)
    frame["fault"] = controls.map(lambda value: value.get("fault", False))
    frame["enabled"] = controls.map(lambda value: value.get("enabled", False))
    frame["fogger_enabled"] = controls.map(lambda value: value.get("fogger_enabled", True))
    frame["fogger_limit"] = controls.map(lambda value: value.get("parameters", {}).get("fogger_max_percent", np.nan))
    frame["fan_limit"] = controls.map(lambda value: value.get("parameters", {}).get("fan_max_percent", np.nan))
    frame["dt"] = frame["timestamp"].shift(-1).sub(frame["timestamp"]).dt.total_seconds().clip(0, MAX_GAP_SECONDS).fillna(0)
    return frame


def settled_samples(frame):
    sample_age = frame["uptime_ms"] - frame["sht_read_uptime_ms"]
    usable = (frame["mode"].eq("automatic_running") & frame["enabled"] & frame["fogger_enabled"] & ~frame["fault"]
              & frame["valid_humidity"].eq(1) & sample_age.between(0, 135000)
              & frame["error"].abs().le(HUMIDITY_TOLERANCE)
              & frame["fogger_percent"].notna() & frame["fan_pwm_percent"].notna())
    gap = frame["timestamp"].diff().dt.total_seconds().gt(MAX_GAP_SECONDS)
    changed = (frame["boot_id"].ne(frame["boot_id"].shift())
               | frame["humidity_setpoint_rh"].ne(frame["humidity_setpoint_rh"].shift())
               | frame["timestamp"].ge(REPLACEMENT).ne(frame["timestamp"].shift().ge(REPLACEMENT)))
    frame["segment"] = (usable.ne(usable.shift()) | gap | changed).cumsum()
    durations = frame["dt"].where(usable, 0).groupby(frame["segment"]).transform("sum")
    return frame.loc[usable & durations.ge(SETTLED_SECONDS)].copy()


def weighted_summary(frame):
    duration = frame["dt"].sum()
    result = {"stable_hours": duration / 3600}
    for column in ["fogger_percent", "fan_pwm_percent", "fan_rpm", "humidity", "humidity_setpoint_rh"]:
        result[column] = np.average(frame[column], weights=frame["dt"]) if duration else np.nan
    return result


def phase_table(frame):
    boundaries = [pd.Timestamp("2026-11-12", tz=TIMEZONE), pd.Timestamp("2026-11-13", tz=TIMEZONE),
                  pd.Timestamp("2026-11-14", tz=TIMEZONE), REPLACEMENT,
                  pd.Timestamp("2026-11-14 12:00", tz=TIMEZONE), pd.Timestamp("2026-11-14 18:00", tz=TIMEZONE),
                  pd.Timestamp("2026-11-15", tz=TIMEZONE), frame["timestamp"].max() + pd.Timedelta(seconds=1)]
    labels = ["12.11. alte Membranen", "13.11. alte Membranen", "14.11. 00:00-04:20 alt",
              "14.11. 04:20-12:00 neu", "14.11. 12:00-18:00 neu", "14.11. 18:00-24:00 neu", "15.11. neue Membranen"]
    rows = []
    for start, end, label in zip(boundaries, boundaries[1:], labels):
        selected = frame.loc[frame["timestamp"].ge(start) & frame["timestamp"].lt(end)]
        rows.append({"phase": label, **weighted_summary(selected)})
    return pd.DataFrame(rows)


def plot(frame, settled, output):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10})
    figure, axes = plt.subplots(3, 1, figsize=(15, 9), sharex=True,
                                gridspec_kw={"height_ratios": [3, 3, 1.5]})
    figure.patch.set_facecolor("#101b1a")
    text, muted, grid = "#e7efeb", "#b3c1ba", "#41534b"
    for axis in axes:
        axis.set_facecolor("#192721")
        axis.tick_params(colors=muted)
        axis.spines[["top", "right"]].set_visible(False)
        axis.spines[["bottom", "left"]].set_color(grid)
        axis.grid(axis="y", color=grid, alpha=.6, linestyle=":")
        axis.yaxis.label.set_color(text)
        axis.axvspan(frame["timestamp"].min(), REPLACEMENT, color="#e7ac55", alpha=.08)
        axis.axvspan(REPLACEMENT, frame["timestamp"].max(), color="#75c7a0", alpha=.06)
        axis.axvline(REPLACEMENT, color="#f1c879", linestyle="--", linewidth=1.4)
    for segment, group in settled.groupby("segment"):
        for axis, column, color in zip(axes, ["fogger_percent", "fan_pwm_percent", "error"],
                                      ["#62c4e8", "#b496ed", "#7ed3a7"]):
            minute = group.set_index("timestamp")[column].resample("1min").mean()
            axis.plot(minute.index, minute, color=color, linewidth=1.3)
    for axis, column in zip(axes[:2], ["fogger_limit", "fan_limit"]):
        axis.plot(frame["timestamp"], frame[column], color="#e7c45a", linewidth=.7, linestyle=":", alpha=.8)
        axis.set_ylim(0, 100)
        axis.set_yticks([0, 20, 40, 60, 80, 100])
    axes[0].set_ylabel("Fogger-Ansteuerung [%]")
    axes[1].set_ylabel("Lüfter-Ansteuerung [%]")
    axes[2].set_ylabel("RH − Soll\n[%rF]")
    axes[2].set_ylim(-2.4, 2.4)
    axes[2].set_yticks([-2, 0, 2])
    axes[2].axhline(0, color=muted, linewidth=.6)
    axes[2].xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18], tz=TIMEZONE))
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%d.%m.  %H:%M", tz=TIMEZONE))
    axes[2].set_xlim(frame["timestamp"].min(), frame["timestamp"].max())
    axes[0].text(.02, .91, "Alte Membranen", color="#f1c879", transform=axes[0].transAxes, weight="bold")
    axes[0].text(.98, .91, "Neue Membranen", ha="right", color="#8bd5b0", transform=axes[0].transAxes, weight="bold")
    axes[0].annotate("Membranwechsel\n14.11. ca. 04:20", xy=(REPLACEMENT, 98),
                     xytext=(12, -39), textcoords="offset points", va="top", color="#f1c879", fontsize=10)
    figure.suptitle("Foggerbedarf bei eingeregelter Feuchte", color=text, fontsize=21, weight="bold", x=.08, ha="left", y=.98)
    end = frame["timestamp"].max().strftime("%d.%m.%Y %H:%M")
    figure.text(.08, .925, f"Primus Popinus @ Lilith | Aufgezeichnete Ansteuerung ab 12.11.2026 bis {end} (Zürich)", color=muted)
    figure.text(.08, .055, "Filter: mindestens 15 min zusammenhängend innerhalb Soll ±2 %rF; kalibrierter SHT45. Nur normaler PI-Betrieb.", color=text, fontsize=9)
    figure.text(.08, .033, "Lücken = keine geeignete Phase. Manuell, Cyclic Mist, Fehler und Datenlücken ausgeschlossen. Gelb gepunktet: jeweilige PI-Obergrenze.", color=muted, fontsize=9)
    figure.text(.08, .011, "Keine Messung der Wasserabgabe oder des Luftdurchsatzes. Eine alte Membran war defekt; Beginn unbekannt. Dochtpflege und Abluftänderung nicht exakt datiert.", color=muted, fontsize=9)
    figure.subplots_adjust(left=.08, right=.98, top=.89, bottom=.12, hspace=.15)
    for suffix in ["png", "svg", "pdf"]:
        figure.savefig(output.with_suffix("." + suffix), dpi=220, facecolor=figure.get_facecolor())
        if suffix == "svg":
            path = output.with_suffix(".svg")
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join(line.rstrip() for line in lines) + "\n", encoding="utf-8")
    plt.close(figure)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=Path("logger/data/devices/b81f3f27f4e0.db"))
    parser.add_argument("--output", type=Path, default=Path("docs/analysis/fogger-demand-2026-11-15"))
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    frame = load_samples(args.database)
    settled = settled_samples(frame)
    summary = phase_table(settled)
    summary.to_csv(args.output.with_suffix(".csv"), index=False)
    plot(frame, settled, args.output)
    print(summary.round(2).to_string(index=False))
    print("Eligible hours:", settled["dt"].sum() / 3600)
    print("Stable segments:", settled["segment"].nunique())


if __name__ == "__main__":
    main()
