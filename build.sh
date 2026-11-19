#!/bin/sh
# Regenerate the DSP, build the device, install it, and run the preflight.
set -e
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEVKIT="$HERE/../ress-vocal/devkit"
PY="$DEVKIT/.venv/bin/python"
INPUTS="$DEVKIT/local/host-tools/macos-arm64-bitwig-6.1.7/compiler-inputs.json"
DEST="${DEST:-$HOME/Documents/Bitwig Devices}"

cd "$HERE"
python3 tools/nam4nitro.py --out device/ress_amp.nitro
cd device
PYTHONPATH=. "$PY" gen_project.py
PYTHONPATH=.:"$DEVKIT" "$PY" build.py --compiler-inputs "$INPUTS"
cp "build/macos-6.1.7/Ress-Amp.bwdevice" "$DEST/"
echo "installed to $DEST"
cd "$DEVKIT"
"$PY" scripts/device_preflight.py "$HERE/device" \
  --project-file "$HERE/device/ress-amp.json" --compiler-inputs "$INPUTS" 2>&1 | tail -3
