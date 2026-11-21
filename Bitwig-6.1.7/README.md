# Bitwig Studio 6.1.7 and later

This folder contains the compressed Nitro builds for Bitwig Studio 6.1.7 and
later.

| Name | Type |
| --- | --- |
| [Ress-Amp](Ress-Amp.bwdevice) | Audio FX (native NAM player, four captures, built-in FX chain) |
| [Ress-Reverb](Ress-Reverb.bwdevice) | Audio FX (reverb/delay, Valhalla Supermassive control set, 20 modes) |

Ress-Amp is a single audio device: four NAM A2 captures are compiled into it and
picked with the switch in the middle of the panel. No plug-in is involved, so it
appears in Bitwig's own device browser once Patchbay's **Framework: Nitro Devices**
is enabled and this folder is listed under **Tools → Device Folders**.

Ress-Reverb is a single audio device built from the same deep-modelling work as
Ress-Amp: a four-line feedback delay network with 20 selectable modes, wired to
the control set of Valhalla Supermassive — Mix, Delay, Warp, Feedback, Density,
Width, Low Cut, High Cut, Mod Rate, Mod Depth, Mode and Clear. Its DSP is an
original design informed by the plug-in's documented modes, not Valhalla's code.
