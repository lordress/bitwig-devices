"""RBJ biquad coefficients for the three band EQ, computed at build time.

The device cannot compute sin/cos at run time (that path is what silenced it),
so the coefficients are baked as plain numbers: one table per sample rate,
51 gain steps from -30 dB to +20 dB, five coefficients per step.

Layout per rate:  band 0 (bass shelf) 0..254, band 1 (mid bell) 255..509,
band 2 (treble shelf) 510..764, each step being [b0, b1, b2, a1, a2].
"""
from __future__ import annotations

import math

RATES = (44100, 48000, 96000)
STEPS = 51          # -30 .. +20 dB
GAIN_MIN = -30.0
GAIN_MAX = 20.0

BANDS = (
    ("low", 100.0, 0.707),
    ("peak", 800.0, 1.8),
    ("high", 3200.0, 0.707),
)


def _coeffs(kind: str, f: float, q: float, gain_db: float, sr: float) -> list[float]:
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * math.pi * f / sr
    cw, sw = math.cos(w0), math.sin(w0)
    if kind == "peak":
        al = sw / (2.0 * q)
        b0, b1, b2 = 1.0 + al * A, -2.0 * cw, 1.0 - al * A
        a0, a1, a2 = 1.0 + al / A, -2.0 * cw, 1.0 - al / A
    else:
        al = sw / 2.0 * math.sqrt(2.0)
        root = math.sqrt(A)
        if kind == "low":
            b0 = A * ((A + 1) - (A - 1) * cw + 2 * root * al)
            b1 = 2 * A * ((A - 1) - (A + 1) * cw)
            b2 = A * ((A + 1) - (A - 1) * cw - 2 * root * al)
            a0 = (A + 1) + (A - 1) * cw + 2 * root * al
            a1 = -2 * ((A - 1) + (A + 1) * cw)
            a2 = (A + 1) + (A - 1) * cw - 2 * root * al
        else:
            b0 = A * ((A + 1) + (A - 1) * cw + 2 * root * al)
            b1 = -2 * A * ((A - 1) + (A + 1) * cw)
            b2 = A * ((A + 1) + (A - 1) * cw - 2 * root * al)
            a0 = (A + 1) - (A - 1) * cw + 2 * root * al
            a1 = 2 * ((A - 1) - (A + 1) * cw)
            a2 = (A + 1) - (A - 1) * cw - 2 * root * al
    return [b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0]


def table(sr: float) -> list[float]:
    out: list[float] = []
    for kind, f, q in BANDS:
        for step in range(STEPS):
            db = GAIN_MIN + (GAIN_MAX - GAIN_MIN) * step / (STEPS - 1)
            out.extend(_coeffs(kind, f, q, db, sr))
    return out


def all_tables() -> list[float]:
    out: list[float] = []
    for sr in RATES:
        out.extend(table(float(sr)))
    return out


BAND_STRIDE = STEPS * 5          # 255
RATE_STRIDE = BAND_STRIDE * 3    # 765
