#!/usr/bin/env python3
"""Bake N NAM A2 captures into one Nitro component.

Each capture is a SlimmableContainer; the submodel with max_value == 1.0 is the
full one and is what gets baked. The weight stream order, the per-sample
forward pass and the ring indexing follow NAM v0.7's A2 path:

    rechannel(1->C, no bias)
    per layer: conv(C->C, kernel K, bias), input mixin(1->C, no bias),
               layer1x1(C->C, bias)
    head conv(C->1, kernel 16, bias), head_scale

The four models share one component: a `model` parameter picks which runs.

    python3 nam4nitro.py --out ress_amp.nitro
"""
from __future__ import annotations

import argparse
import json
import pathlib

import eqtable

C = 8            # channels == bottleneck in these captures
HEAD_K = 16


class A2:
    def __init__(self, path: pathlib.Path, label: str):
        data = json.loads(path.read_text())
        cfg = data.get("config") or {}
        subs = cfg.get("submodels")
        if not subs:
            raise SystemExit(f"{path.name}: not a SlimmableContainer")
        best = max(subs, key=lambda s: float(s.get("max_value", 0)))
        model = best["model"]
        mcfg = model["config"]
        layer = mcfg["layers"][0]
        if layer["channels"] != C:
            raise SystemExit(f"{path.name}: channels {layer['channels']} != {C}")
        for key in ("conv_pre_film", "conv_post_film", "input_mixin_pre_film",
                    "input_mixin_post_film", "activation_pre_film",
                    "activation_post_film", "layer1x1_post_film", "head1x1_post_film"):
            if layer[key].get("active"):
                raise SystemExit(f"{path.name}: FiLM {key} is active, not baked")
        if any(g != "none" for g in layer["gating_mode"]):
            raise SystemExit(f"{path.name}: gated layers, not baked")
        if layer["head1x1"].get("active"):
            raise SystemExit(f"{path.name}: head1x1 active, not baked")
        if not layer["layer1x1"].get("active"):
            raise SystemExit(f"{path.name}: layer1x1 inactive, not baked")
        md = (best.get("model") or {}).get("metadata") or data.get("metadata") or {}
        self.loudness = float(md.get("loudness", -14.0))
        self.path = path
        self.label = label
        self.weights = [float(w) for w in model["weights"]]
        self.ks = [int(v) for v in layer["kernel_sizes"]]
        self.ds = [int(v) for v in layer["dilations"]]
        self.n = len(self.ks)
        if len(self.ds) != self.n:
            raise SystemExit(f"{path.name}: kernel_sizes / dilations length differ")
        self.head_scale = float(mcfg["head_scale"])
        self.head_bias = float(layer["head"].get("bias", True))
        if not self.head_bias:
            raise SystemExit(f"{path.name}: head without bias, not baked")
        self.layout()

    def layout(self):
        """Offsets into the weight stream and into the state block."""
        w = 0
        self.re_off = w
        w += C
        self.layers = []
        h = 0
        for li in range(self.n):
            k, d = self.ks[li], self.ds[li]
            ring = (k - 1) * d + 1
            lay = {
                "k": k, "d": d, "ring": ring,
                "w_conv": w, "w_cbias": w + C * C * k,
                "w_mixin": w + C * C * k + C,
                "w_l1x1": w + C * C * k + 2 * C,
                "w_l1bias": w + C * C * k + 2 * C + C * C,
                "h": h,
            }
            w += C * C * k + 2 * C + C * C + C
            h += ring * C
            self.layers.append(lay)
        self.w_head = w
        w += C * HEAD_K
        self.w_hbias = w
        w += 1
        self.w_scale = w
        w += 1
        if w != len(self.weights):
            raise SystemExit(f"{self.path.name}: consumed {w}, file has {len(self.weights)}")
        self.state_size = h + HEAD_K * C

    def tail(self) -> str:
        got = self.weights[self.w_scale]
        if abs(got - self.head_scale) > 1e-6:
            raise SystemExit(f"{self.path.name}: trailing float {got} != head_scale {self.head_scale}")
        return f"{got:.9g}"


def f(x: float) -> str:
    """A decimal literal; the Bitwig 6.1 Nitro parser rejects 1.2e-05."""
    from decimal import Decimal
    s = format(Decimal(repr(float(x))), "f")
    if s in ("-0", "0"):
        return "0.0"
    # an f32 array literal is type-checked: a bare "1" is an int and fails
    if "." not in s:
        s += ".0"
    return s


def consts(m: A2, idx: int) -> list[str]:
    out = [f"    // ---- {m.label}: {m.n} layers, {len(m.weights)} weights"]
    out.append(f"    f32[{len(m.weights)}] M{idx}_W;")
    return out


def weight_init(m: A2, idx: int) -> list[str]:
    """The table, element by element: no array literal for the parser to type-check."""
    out = []
    for i, x in enumerate(m.weights):
        out.append(f"        M{idx}_W[{i}] = {f(x)};")
    return out


def state(m: A2, idx: int) -> list[str]:
    out = [f"    f32[{m.state_size}] M{idx}_H;", f"    i32[{m.n}] M{idx}_WP;",
           f"    i32 M{idx}_HWP = 0;", f"    f32[{C}] M{idx}_LIN;",
           f"    f32[{C}] M{idx}_Z;", f"    f32[{C}] M{idx}_A;",
           f"    f32[{C}] M{idx}_HS;"]
    return out


def clear(m: A2, idx: int) -> list[str]:
    out = [f"        for (i32 i = 0; (i < {m.state_size}); ++i) M{idx}_H[i] = 0.0;",
           f"        for (i32 i = 0; (i < {m.n}); ++i) M{idx}_WP[i] = 0;",
           f"        M{idx}_HWP = 0;"]
    for arr in ("LIN", "Z", "A", "HS"):
        out.append(f"        for (i32 i = 0; (i < {C}); ++i) M{idx}_{arr}[i] = 0.0;")
    return out


def forward(m: A2, idx: int) -> list[str]:
    out = [f"    f32 run_m{idx}(f32 s)", "    {"]
    out.append(f"        f32 cond = s;")
    out.append(f"        for (i32 c = 0; (c < {C}); ++c)")
    out.append(f"            M{idx}_LIN[c] = (M{idx}_W[{m.re_off} + c] * s);")
    out.append(f"        for (i32 c = 0; (c < {C}); ++c)")
    out.append(f"            M{idx}_HS[c] = 0.0;")
    out.append("")
    for li, lay in enumerate(m.layers):
        K, D, R, base, hb = lay["k"], lay["d"], lay["ring"], lay["h"], lay["h"]
        wc, wb = lay["w_conv"], lay["w_cbias"]
        wm, w1, w1b = lay["w_mixin"], lay["w_l1x1"], lay["w_l1bias"]
        out.append(f"        // layer {li}: K={K} D={D} ring={R}")
        out.append(f"        M{idx}_H[(({hb}) + (M{idx}_WP[{li}] * {C}))] = M{idx}_LIN[0];")
        out.append(f"        for (i32 c = 1; (c < {C}); ++c)")
        out.append(f"            M{idx}_H[(({hb}) + (M{idx}_WP[{li}] * {C})) + c] = M{idx}_LIN[c];")
        out.append(f"        for (i32 i = 0; (i < {C}); ++i)")
        out.append("        {")
        out.append(f"            f32 acc = M{idx}_W[{wb} + i];")
        out.append(f"            for (i32 k = 0; (k < {K}); ++k)")
        out.append("            {")
        out.append(f"                i32 idx = ((M{idx}_WP[{li}] - (({K - 1} - k) * {D})) + {R}) % {R};")
        out.append(f"                for (i32 j = 0; (j < {C}); ++j)")
        out.append(f"                    acc = (acc + (M{idx}_W[(({wc} + (i * {C * K})) + (j * {K})) + k]"
                   f" * M{idx}_H[(({hb}) + (idx * {C})) + j]));")
        out.append("            }")
        out.append(f"            acc = (acc + (M{idx}_W[{wm} + i] * cond));")
        out.append(f"            M{idx}_Z[i] = acc;")
        out.append("        }")
        out.append(f"        for (i32 i = 0; (i < {C}); ++i)")
        out.append("        {")
        out.append(f"            f32 v = M{idx}_Z[i];")
        out.append(f"            M{idx}_A[i] = (0.0 < v) ? v : (0.01 * v);")
        out.append(f"            M{idx}_HS[i] = (M{idx}_HS[i] + M{idx}_A[i]);")
        out.append("        }")
        out.append(f"        for (i32 i = 0; (i < {C}); ++i)")
        out.append("        {")
        out.append(f"            f32 acc = M{idx}_W[{w1b} + i];")
        out.append(f"            for (i32 j = 0; (j < {C}); ++j)")
        out.append(f"                acc = (acc + (M{idx}_W[(({w1} + (i * {C})) + j)] * M{idx}_A[j]));")
        out.append(f"            M{idx}_LIN[i] = (M{idx}_LIN[i] + acc);")
        out.append("        }")
        out.append(f"        M{idx}_WP[{li}] = ((M{idx}_WP[{li}] + 1) % {R});")
        out.append("")
    out.append(f"        M{idx}_H[(({m.state_size - HEAD_K * C}) + (M{idx}_HWP * {C}))] = M{idx}_HS[0];")
    out.append(f"        for (i32 c = 1; (c < {C}); ++c)")
    out.append(f"            M{idx}_H[(({m.state_size - HEAD_K * C}) + (M{idx}_HWP * {C})) + c] = M{idx}_HS[c];")
    out.append(f"        f32 y = M{idx}_W[{m.w_hbias}];")
    out.append(f"        for (i32 k = 0; (k < {HEAD_K}); ++k)")
    out.append("        {")
    out.append(f"            i32 idx = ((M{idx}_HWP - ({HEAD_K - 1} - k)) + {HEAD_K}) % {HEAD_K};")
    out.append(f"            for (i32 j = 0; (j < {C}); ++j)")
    out.append(f"                y = (y + (M{idx}_W[({m.w_head} + (j * {HEAD_K})) + k]"
               f" * M{idx}_H[(({m.state_size - HEAD_K * C}) + (idx * {C})) + j]));")
    out.append("        }")
    out.append(f"        M{idx}_HWP = ((M{idx}_HWP + 1) % {HEAD_K});")
    out.append(f"        return (y * M{idx}_W[{m.w_scale}]);")
    out.append("    }")
    return out


def generate(models: list[A2], comp: str, caption: str) -> str:
    L: list[str] = []
    L.append(f"// {caption}")
    L.append("// Four NAM captures baked in: the weight tables below are theirs.")
    L.append(f"component {comp}")
    L.append("{")
    L.append("    audio_inport f32<2> in;")
    L.append("    value_inport i32 p_model;")
    L.append("    audio_inport f32 p_input = 0.0;")
    L.append("    audio_inport f32 p_gate = 0.0;")
    L.append("    audio_inport f32 p_bass = 0.0;")
    L.append("    audio_inport f32 p_mid = 0.0;")
    L.append("    audio_inport f32 p_treble = 0.0;")
    L.append("    audio_inport f32 p_output = 0.0;")
    L.append("    audio_inport f32 p_presence = 0.0;")
    L.append("    audio_inport f32 p_depth = 0.0;")
    L.append("    value_inport i32 gate_on;")
    L.append("    value_inport bool cab_on;")
    L.append("    audio_outport f32<2> out;")
    L.append("    audio_outport f32<4> display;")
    L.append("")
    L.append("    const f32 SR = EC.samplerate;")
    L.append("")
    for i, m in enumerate(models):
        L.extend(consts(m, i))
        # index table for the rechannel weights (kept out of the hot loop)
        L.append("")
    L.append("    // state")
    for i, m in enumerate(models):
        L.extend(state(m, i))
    L.append("    f32 gate_env = 1.0;")
    L.append(f"    f32[{len(eqtable.all_tables())}] EQ;")
    for band in ("bs", "md", "tr"):
        L.append(f"    f32 {band}_z1 = 0.0;")
        L.append(f"    f32 {band}_z2 = 0.0;")
    L.append("    f32 low_state = 0.0;")
    L.append("    f32 hi_state = 0.0;")
    L.append("    f32 cab_lp = 0.0;")
    L.append("    f32 cab_hp = 0.0;")
    L.append("    f32 in_env = 0.0;")
    L.append("    f32 out_env = 0.0;")
    L.append("    i32 runtime_magic = 0;")
    L.append("")
    L.append("    f32 db(f32 decibels)")
    L.append("    {")
    L.append("        return pow(10.0, (decibels * 0.05));")
    L.append("    }")
    L.append("")
    L.append("    f32 clampf(f32 value, f32 low, f32 high)")
    L.append("    {")
    L.append("        return fmin(high, fmax(low, value));")
    L.append("    }")
    L.append("")
    L.append("    // NAM's BasicNamToneStack: RBJ biquads, bass 150 Hz shelf, mid 425 Hz bell, treble 1.8 kHz shelf")
    L.append("    void clearState()")
    L.append("    {")
    for i, m in enumerate(models):
        L.extend(clear(m, i))
    L.append("        gate_env = 1.0;")
    L.append("        bs_z1 = 0.0; bs_z2 = 0.0; md_z1 = 0.0; md_z2 = 0.0; tr_z1 = 0.0; tr_z2 = 0.0;")
    L.append("        low_state = 0.0;")
    L.append("        hi_state = 0.0;")
    L.append("        cab_lp = 0.0;")
    L.append("        cab_hp = 0.0;")
    L.append("        in_env = 0.0;")
    L.append("        out_env = 0.0;")
    L.append("        runtime_magic = 91301;")
    L.append("    }")
    L.append("")
    for i, m in enumerate(models):
        L.extend(forward(m, i))
        L.append("")
    L.append("    init")
    L.append("    {")
    for i, x in enumerate(eqtable.all_tables()):
        L.append(f"        EQ[{i}] = {f(x)};")
    for i, m in enumerate(models):
        L.extend(weight_init(m, i))
    L.append("        clearState();")
    L.append("    }")
    L.append("")
    L.append("    reset")
    L.append("    {")
    L.append("        clearState();")
    L.append("    }")
    L.append("")
    L.append("    process")
    L.append("    {")
    L.append("        // recall guard: the rings must be cleared before the first read")
    L.append("        if (runtime_magic != 91301)")
    L.append("        {")
    L.append("            clearState();")
    L.append("            runtime_magic = 91301;")
    L.append("        }")
    L.append("        f32 s = ((in[0] + in[1]) * 0.5);")
    L.append("        s = (s * db(clampf(p_input, -24.0, 24.0)));")
    L.append("        i32 sel = p_model;")
    L.append("        if ((sel < 0))")
    L.append("            sel = 0;")
    L.append("        if ((sel > 3))")
    L.append("            sel = 3;")
    L.append("        f32 mi = cast(sel, f32);")
    L.append("        f32 y = 0.0;")
    L.append("        if ((mi < 0.5))")
    L.append("            y = run_m0(s);")
    L.append("        if (((0.5 <= mi) && (mi < 1.5)))")
    L.append("            y = run_m1(s);")
    L.append("        if (((1.5 <= mi) && (mi < 2.5)))")
    L.append("            y = run_m2(s);")
    L.append("        if ((2.5 <= mi))")
    L.append("            y = run_m3(s);")
    L.append("")
    L.append("        // noise gate")
    L.append("        f32 thr = db(clampf(p_gate, -90.0, 0.0));")
    L.append("        if ((gate_on > 0))")
    L.append("        {")
    L.append("            if ((fabs(s) > thr))")
    L.append("                gate_env = (gate_env + ((1.0 - gate_env) * 0.02));")
    L.append("            else")
    L.append("                gate_env = (gate_env * exp((-1.0 / (0.03 * SR))));")
    L.append("        }")
    L.append("        else")
    L.append("            gate_env = 1.0;")
    L.append("")
    L.append("        // tone: biquad coefficients looked up from the baked table")
    L.append("        i32 rbase = 1530;")
    L.append("        if ((SR < 46000.0))")
    L.append("            rbase = 0;")
    L.append("        else if ((SR < 70000.0))")
    L.append("            rbase = 765;")
    L.append("        i32 sb = cast(clampf((p_bass + 30.0), 0.0, 50.0), i32);")
    L.append("        i32 sm = cast(clampf((p_mid + 30.0), 0.0, 50.0), i32);")
    L.append("        i32 st = cast(clampf((p_treble + 30.0), 0.0, 50.0), i32);")
    L.append("        i32 ob = (rbase + (sb * 5));")
    L.append("        i32 om = ((rbase + 255) + (sm * 5));")
    L.append("        i32 ot = ((rbase + 510) + (st * 5));")
    L.append("        f32 yb = ((EQ[ob] * y) + bs_z1);")
    L.append("        bs_z1 = (((EQ[(ob + 1)] * y) - (EQ[(ob + 3)] * yb)) + bs_z2);")
    L.append("        bs_z2 = ((EQ[(ob + 2)] * y) - (EQ[(ob + 4)] * yb));")
    L.append("        f32 ym = ((EQ[om] * yb) + md_z1);")
    L.append("        md_z1 = (((EQ[(om + 1)] * yb) - (EQ[(om + 3)] * ym)) + md_z2);")
    L.append("        md_z2 = ((EQ[(om + 2)] * yb) - (EQ[(om + 4)] * ym));")
    L.append("        f32 w = ((EQ[ot] * ym) + tr_z1);")
    L.append("        tr_z1 = (((EQ[(ot + 1)] * ym) - (EQ[(ot + 3)] * w)) + tr_z2);")
    L.append("        tr_z2 = ((EQ[(ot + 2)] * ym) - (EQ[(ot + 4)] * w));")
    L.append("        if ((w != w) || (fabs(w) > 64.0))")
    L.append("        {")
    L.append("            bs_z1 = 0.0; bs_z2 = 0.0; md_z1 = 0.0; md_z2 = 0.0; tr_z1 = 0.0; tr_z2 = 0.0;")
    L.append("            w = y;")
    L.append("        }")
    L.append("")
    L.append("        w = (w * gate_env);")
    L.append("")
    L.append("        // post: depth (low shelf 90 Hz), presence (high shelf 3 kHz), cabinet")
    L.append("        low_state = (low_state + (0.0012 * (w - low_state)));")
    L.append("        hi_state = (hi_state + (0.38 * (w - hi_state)));")
    L.append("        f32 dep = (db(clampf(p_depth, -10.0, 10.0)) - 1.0);")
    L.append("        f32 pre = (db(clampf(p_presence, -10.0, 10.0)) - 1.0);")
    L.append("        w = (w + (low_state * dep) + ((w - hi_state) * pre));")
    L.append("        if (cab_on)")
    L.append("        {")
    L.append("            cab_lp = (cab_lp + (0.36 * (w - cab_lp)));")
    L.append("            cab_hp = (cab_hp + (0.009 * (w - cab_hp)));")
    L.append("            w = ((cab_lp - cab_hp) * 1.08);")
    L.append("        }")
    L.append("        w = (w * db(clampf(p_output, -24.0, 12.0)));")
    L.append("        out = <w, w>;")
    L.append("")
    L.append("        f32 in_db = (20.0 * log10(fmax(0.000001, fabs(s))));")
    L.append("        in_env = fmax(fabs(s), (in_env * exp((-1.0 / (0.30 * SR)))));")
    L.append("        out_env = fmax(fabs(w), (out_env * exp((-1.0 / (0.30 * SR)))));")
    L.append("        f32 out_db = (20.0 * log10(fmax(0.000001, out_env)));")
    L.append("        display = <clampf(((in_db + 60.0) / 60.0), 0.0, 1.0),"
             " clampf(((out_db + 60.0) / 60.0), 0.0, 1.0), gate_env, (mi * 0.25)>;")
    L.append("    }")
    L.append("}")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=pathlib.Path, required=True)
    ap.add_argument("--component", default="ress_amp")
    ap.add_argument("--caption", default="Ress-Amp")
    ap.add_argument("--dir", default="/Users/ressa/Documents/Bitwig Devices/NAM")
    ap.add_argument("--models", nargs="*", default=None)
    args = ap.parse_args()

    sys_path = pathlib.Path(__file__).resolve().parent
    import sys
    sys.path.insert(0, str(sys_path.parent / "device"))
    from spec import MODELS  # noqa: E402

    wanted = args.models or [m[0] for m in MODELS]
    labels = {m[0]: m[1] for m in MODELS}
    models = [A2(pathlib.Path(args.dir) / f"{name}.nam", labels.get(name, name[:16]))
              for name in wanted]
    src = generate(models, args.component, args.caption)
    args.out.write_text(src)
    total = sum(len(m.weights) for m in models)
    print(f"{args.out}  {len(src)} bytes  {total} weights  "
          f"{sum(m.state_size for m in models)} state floats")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
