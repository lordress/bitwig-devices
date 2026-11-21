# Bitwig devices

Native Bitwig devices, installed through Patchbay's **Framework: Nitro Devices**.

| Device | What it is |
| --- | --- |
| [Ress-Amp](Bitwig-6.1.7/Ress-Amp.bwdevice) | four NAM captures compiled into one device |

Everything below describes Ress-Amp.

---

# Ress-Amp

A native Bitwig device that plays four NAM captures with no plug-in in the chain:
the four models are compiled into the device itself.

- **One device, four captures.** A four-way switch in the middle of the panel
  picks the amp; the DSP runs the selected model with its weights baked in.
- **Real tone stack.** Bass / Mid / Treb are biquads — 100 Hz low shelf,
  800 Hz bell, 3.2 kHz high shelf — with +20 dB boost and −30 dB cut. The
  coefficients are baked as tables, so nothing is computed with trig at run time.
- **Input and output metering** on the device's own display (left = in, right = out).
- **Noise gate** with threshold and an Off/On switch.
- **Cab** filter and a post EQ (Press / Depth).

## Install with Patchbay

1. Copy `Ress-Amp.bwdevice` into a folder Patchbay scans, or add **this repository
   folder** itself as one:

   ```
   git clone https://github.com/lordress/bitwig-devices
   ```

2. In Patchbay, enable **Framework: Nitro Devices**.
3. **Tools → Device Folders** → add the folder you put `Ress-Amp.bwdevice` in.
4. Press **Load** and start Bitwig. Search **Ress-Amp** in the device browser.

A native device is compiled into the project when it is inserted. Replacing the
file does not update a device already on a track — delete it and insert a fresh one.

If the device is silent or missing after an update, check Bitwig's log
(`~/Library/Logs/Bitwig/BitwigStudio.log`) for `Error compiling nitro atom code`;
that is the device failing to compile, and the message names the type and line.

## The captures

The four `.nam` files the device was built from are in `captures/`, so the device
can be rebuilt from this repository alone:

```
captures/DZL V4 III Gain FAT CAB FREE.nam
captures/FNDR BFSR VB Edge WRM2 CAB FREE.nam
captures/Peavey 5150_4x12 MESA_TS9 BOOST_SM57.nam
captures/VX TB30 BR Edge0 BAL2 CAB FREE.nam
```

They are A2 `SlimmableContainer` files; the device bakes the full 8-channel
submodel (12,146 weights) of each.

## The four captures

| Slot | Capture | Loudness |
|---|---|---|
| 1 | DZL V4 III Gain FAT CAB FREE (Diezel VH4) | −12.0 dB |
| 2 | FNDR BFSR VB Edge WRM2 CAB FREE (Fender Super Reverb) | −15.8 dB |
| 3 | Peavey 5150_4x12 MESA_TS9 BOOST_SM57 | −16.4 dB |
| 4 | VX TB30 BR Edge0 BAL2 CAB FREE (Vox AC30) | −10.1 dB |

Each is the full 8-channel submodel of its A2 `SlimmableContainer`
(12,146 weights). The captures themselves are not in this repository: the
device contains their weights, and their `.nam` files belong to whoever
trained them (TONE3000 / amalgamaudio / autoguitarrig).

## Build from source

The device is generated, not hand-written:

```sh
./build.sh
```

That runs `tools/nam4nitro.py` (bake the captures into Nitro), then
`device/gen_project.py` (manifest), `device/gen_panel.py` (the panel shader,
from the spec) and `device/build.py` (compile and package), copies the result to `~/Documents/Bitwig Devices` and runs Bitwig's own
preflight.

Building needs the Bitwig Device Blueprints devkit with compiler inputs taken
from an installed Bitwig 6.1.7, which is not included here — `build.sh` points at
a sibling `ress-vocal/devkit`. The prebuilt `.bwdevice` needs none of that.

## Editing the panel

See [EDITING.md](EDITING.md): the face — sections, meters, widgets and their
coordinates — lives in `device/panel_spec.py`; custom drawing in
`device/panel_body.sksl`; parameters in `device/spec.py`. `panel.sksl` is
generated, and `../../ress-vocal/devkit/.venv/bin/python -m bwui preview device/panel_spec.py`
shows the panel without building it.

## Licence

MIT for this device's code and packaging. Neural Amp Modeler and Bitwig Studio
are their owners' products; neither is included. Capture metadata and weights
remain the property of their trainers.
