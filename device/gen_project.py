"""Write the Ress-Amp project manifest with its preflight control contract."""
from __future__ import annotations

import json
from pathlib import Path

from spec import INDEXED, MODELS, PANEL_HEIGHT, PARAMS, TOGGLES

HERE = Path(__file__).resolve().parent
UUID = "8dd21e55-6502-4be5-ab1d-a7320f6df05b"

# Widget geometry by parameter, derived from the panel columns.
KNOB_SIZE = {}
for key, _title, _p, _mn, _mx, _d, _u in PARAMS:
    KNOB_SIZE[key] = 1

controls = []
for key, title, preset, minimum, maximum, default, unit in PARAMS:
    if key in ("model", "gate_on"):
        states = [i / (len(INDEXED[key]) - 1) for i in range(len(INDEXED[key]))]
        controls.append({
            "parameter": "GATE_ON" if key == "gate_on" else key.upper(),
            "widgetClass": 1712,
            "drawOwners": ["native"],
            "inputOwner": "native",
            "gestures": ["select"],
            "statesNormalized": states,
            "defaultNormalized": states[-1] if key == "gate_on" else states[0],
        })
        continue
    controls.append({
        "parameter": key.upper(),
        "widgetClass": 1687,
        "drawOwners": ["native"],
        "inputOwner": "native",
        "knobSize": KNOB_SIZE[key],
        "gestures": ["drag", "reset"],
        "defaultNormalized": (default - minimum) / (maximum - minimum),
    })

states_gate = [i / (len(INDEXED["gate_on"]) - 1) for i in range(len(INDEXED["gate_on"]))]
controls.append({
    "parameter": "GATE_ON",
    "widgetClass": 1712,
    "drawOwners": ["native"],
    "inputOwner": "native",
    "gestures": ["select"],
    "statesNormalized": states_gate,
    "defaultNormalized": states_gate[-1],
})

project = {
    "schemaVersion": 1,
    "projectId": "ress.ress-amp",
    "name": "Ress-Amp",
    "surface": "device",
    "target": {"bitwigVersion": "6.1.7", "platform": "macos-arm64"},
    "identity": {"uuid": UUID, "creator": "Ressa", "category": "Audio FX"},
    "presentation": {
        "type": "audio-fx",
        "description": "Neural amp player with four NAM captures baked in: input trim, noise gate, "
                       "bass / mid / treble and output, with a live input/output meter display.",
        "tags": "nam neural amp modeler guitar amp capture cabinet",
    },
    "sources": {"nitro": ["ress_amp.nitro"], "sksl": ["panel.sksl"]},
    "adapter": {"type": "external-builder", "argv": ["python", "{workspace}/build.py", "--out", "{output}"]},
    "output": {"path": "build/macos-6.1.7/Ress-Amp.bwdevice", "libraryPath": "Ress-Amp.bwdevice"},
    "preflight": {
        "profile": "bitwig-6.1.3-hybrid",
        "expectedNitroInputs": 1 + len(PARAMS) + 1 + len(TOGGLES),  # gate_on is its own switch
        "expectedNitroOutputs": 2,
        "maxDrawingVectors": 1,
        "requiredAudioInputSourceClassId": 1371,
        "requiredDelayCompensationInputSourceClassId": 154,
        "requiredProxyInputCount": 2,
        "requireSkiaCompiler": True,
        "recallSafety": {
            "canary": "runtime_magic",
            "arrays": [
                {"name": f"M{i}_H", "initialization": "explicit-clear",
                 "requiredBeforeFirstAccess": ["clearState()"]}
                for i in range(len(MODELS))
            ],
        },
        "controlContract": {"schema": 1, "shaderRole": "non-interactive-display", "controls": controls},
    },
}

(HERE / "ress-amp.json").write_text(json.dumps(project, indent=2) + "\n", encoding="utf-8")
print(f"wrote {HERE / 'ress-amp.json'} ({len(controls)} controls, height {PANEL_HEIGHT})")
