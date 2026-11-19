"""Ress-Amp parameter and panel specification.

One source of truth for the Nitro port order, the document builder and the
preflight control contract. Four captures are baked into the device; `model`
picks one, `gate_on` is a two-state switch.
"""

# key, panel title, preset id, min, max, default, unit (0 none, 1 %, 2 dB)
PARAMS = [
    ("model",    "Amp",      "MODEL",     1.0,   4.0,   1.0, 0),
    ("input",    "In",       "INPUT",   -24.0,  24.0,   0.0, 0),
    ("gate",     "Gate",     "GATE",    -90.0,   0.0, -60.0, 0),
    ("bass",     "Bass",     "BASS",    -30.0,  20.0,   0.0, 0),
    ("mid",      "Mid",      "MID",     -30.0,  20.0,   0.0, 0),
    ("treble",   "Treb",     "TREBLE",  -30.0,  20.0,   0.0, 0),
    ("output",   "Out",      "OUTPUT",  -24.0,  12.0,   0.0, 0),
    ("presence", "Press",    "PRESENCE", -10.0, 10.0,   0.0, 0),
    ("depth",    "Depth",    "DEPTH",   -10.0,  10.0,   0.0, 0),
]

# parameters that are a choice, not a number: key -> item names
INDEXED = {
    "model": ["DZL", "FNDR", "5150", "VX"],
    "gate_on": ["Off", "On"],
}

# key, panel title, preset id, default
TOGGLES = [
    ("cab_on", "Cab", "CAB_ON", True),
]

PANEL_WIDTH = 87
PANEL_HEIGHT = 53

# The four bakes, in panel order. Index is the `model` parameter's value.
MODELS = [
    ("DZL V4 III Gain FAT CAB FREE", "DZL V4"),
    ("FNDR BFSR VB Edge WRM2 CAB FREE", "FNDR BFSR"),
    ("Peavey 5150_4x12 MESA_TS9 BOOST_SM57", "5150 TS9"),
    ("VX TB30 BR Edge0 BAL2 CAB FREE", "VX TB30"),
]

MODEL_DIR = "/Users/ressa/Documents/Bitwig Devices/NAM"

# The amp switch: two rows of two, where the tiles used to be.
SWITCH = (16.3, 4.1, 37.0, 29.0)
SWITCH_BREAK = 2

# Tone stack to the right of the switch: x, y per knob.
TONE = [("treble", 75.0, 7.0), ("mid", 75.0, 22.1), ("bass", 75.0, 37.2)]

# Bottom row.
KNOB_Y = 39.6
LABEL_Y = 46.4
STRIP = [("input", 3.0), ("gate", 17.6), ("presence", 39.5), ("depth", 48.5)]
GATE_SWITCH = (24.4, 40.4, 9.6, 4.4)
OUT_KNOB = (60.0, 39.6, 6.4, 6.4)
OUT_LABEL = (59.2, 46.8)
