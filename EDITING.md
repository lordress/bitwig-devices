# Rearranging the panel yourself

Everything on the device's face is described in two files: **what** is there
(`document.py`) and **where** it is (`spec.py`). Nothing is hard-coded in the
compiled device, so you can move things and rebuild in about a minute.

```
device/spec.py       parameter ranges, and the grid positions of every control
device/document.py   the item list: labels, knobs, toggles, in build order
device/panel.sksl    the drawn background, in the mockup's 469 x 286 coordinates
tools/nam4nitro.py   the DSP and its parameter ports
```

## The coordinate system

The panel is **87 grid units wide and 53 tall** (Bitwig fixes the height; width
you can change). One unit is about 19 px at 150 % UI scale. Positions are
`(x, y)` with **y down from the top-left of the panel**.

```python
# spec.py
KNOB_Y  = 38.4      # top of the knob row
LABEL_Y = 46.2      # the text under each knob
COLUMNS = [
    {"label": "INPUT", "x": 3.0,  "knob": "input"},
    {"label": "BASS",  "x": 11.2, "knob": "bass"},
]
```

Move a knob by changing its `x`; move the whole row by changing `KNOB_Y` and
`LABEL_Y` together. Add a control by adding an entry — the key must match a
`PARAMS` entry.

## The item list

`document()` in `document.py` appends the widgets in order:

```python
items.append(label("RESS-AMP", 14, 0.6, 11, 3, align=0))      # text, x, y, w, h
items.append(knob(ref(params["input"]), x, KNOB_Y, 6.4, 6.4, "", 1))
items.append(toggle(ref(toggles["gate_on"]), 72.6, 4.4, 11, 3.6, "GATE"))
```

- `knob(...)` — the last number is Bitwig's knob size preset, **0–3** (1 = small,
  3 = large). The box after it (6.4 × 6.4) is the cell it occupies.
- `toggle(...)`, `label(...)`, `number_field(...)` take the same `x, y, w, h`.
- Widgets may not overlap: the build's preflight fails on an overlap, which is
  the fastest way to find a bad coordinate.

## The drawn background

`panel.sksl` paints everything that is not a Bitwig widget — panel bodies, meter
wells, the four capture tiles, the gate LED. It uses the **same coordinates as
your SVG** (469 × 286), so a rectangle from the mockup can be copied straight in:

```glsl
color = mix(color, well, inBox(p, float2(2.8, 3.9), float2(66.8, 196.9)));
```

Nitro's `display` output feeds it: lanes are (input level, output level, gate,
model), each 0–1.

## Rebuild

```sh
cd ~/Documents/deepseek-harness/default-workspace/ress-amp
./build.sh              # regenerate, build, copy to Bitwig Devices, run preflight
```

Then in Bitwig: **delete the old device from the track and insert a fresh one** —
a device already on a track keeps the compiled code it was inserted with, so the
file on disk can change without the instance changing.

## If you only want to move things

Edit `spec.py` coordinates, run `./build.sh`, re-insert. `panel.sksl` only needs
touching when you move a *panel body*, not when you move a knob.
