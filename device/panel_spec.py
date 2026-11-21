"""Ress-Amp's panel: the device's one description of its face.

Sections, meter wells, captions and widget rectangles live here; the DSP ports
stay in ``spec.py`` and the build order in ``document.py``. Change a coordinate
here and the panel, its preview and its generated shader all follow.

    cd ress-amp/device
    ../../ress-vocal/devkit/.venv/bin/python -m bwui preview panel_spec.py -o /tmp/ress.html
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # workspace root

from bwui import Panel, Theme  # noqa: E402

THEME = Theme(accent_index=0, pie_index=6)
PANEL = Panel(87, 53, theme=THEME, name="Main", title="Ress-Amp")

# ---- background ---------------------------------------------------------
# Sections are in grid units; one unit is 469/87 design pixels. The three wells
# hold the amp switch and the two meters, the bottom strip holds the knobs.
PANEL.display()
PANEL.section("input well", (0.52, 0.72, 11.87, 35.74), style="well")
PANEL.section("amp well", (13.14, 0.72, 43.23, 35.74), style="well")
PANEL.section("output well", (57.29, 0.91, 11.87, 35.81), style="well")
PANEL.section("strip", (0.33, 37.09, 69.00, 15.40), style="strip")
PANEL.section("side strip", (70.09, 1.09, 16.33, 51.39), style="strip")

# Two meter bars per side, both driven by one lane: audioLow.x in, audioLow.y out.
PANEL.meter("in", (3.86, 1.86, 2.41, 33.23), lane=0)
PANEL.meter("in", (6.64, 1.86, 2.41, 33.23), lane=0)
PANEL.meter("out", (60.63, 1.86, 2.41, 33.23), lane=1)
PANEL.meter("out", (63.42, 1.86, 2.41, 33.23), lane=1)

# ---- widgets ------------------------------------------------------------
# The amp switch: four captures, two per row.
PANEL.segments("model", 16.3, 4.1, 37.0, 29.0, wrap=2,
               choices=["DZL V4", "FNDR BFSR", "5150 TS9", "VX TB30"],
               tooltip="Amp capture: DZL V4, FNDR BFSR, 5150 TS9, VX TB30")

# Tone stack, right-hand strip.
PANEL.knob_column(75.0, 7.0, [("treble", "Treb"), ("mid", "Mid"), ("bass", "Bass")],
                  gap=6.1)

# Bottom row. The gate switch sits between the gate and presence knobs.
PANEL.knob("input", 3.0, 39.6, label="In")
PANEL.knob("gate", 17.6, 39.6, label="Gate")
PANEL.segments("gate_on", 24.4, 40.4, 9.6, 4.4, choices=["Off", "On"],
               tooltip="Noise gate on or off")
PANEL.knob("presence", 39.5, 39.6, label="Press")
PANEL.knob("depth", 48.5, 39.6, label="Depth")
PANEL.knob("output", 60.0, 39.6, label="Out")

# Sample values for the preview only; the device reads real audio.
PANEL.demo_values.update({"in": 0.62, "out": 0.47, "model": 0.75})
