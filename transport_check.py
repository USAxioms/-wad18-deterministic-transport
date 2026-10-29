"""Transport check of the surrogate's design claims (docs/prereg/TRANSPORT_CHECK.md).

python3 transport_check.py run CASE      run one case -> results/transport/CASE.json
python3 transport_check.py run all       run every case (about 10 minutes)
python3 transport_check.py summarize     apply the pre-declared rules -> results/transport/TRANSPORT_CHECK.json
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import spec, model, jsonio, wad18 as w, blanket_transport as bt  # noqa: E402

W = w.WAD
OUT = os.path.join(ROOT, "results", "transport")
DESIGNS = {"REF": None,
           "S110": {"t_b": "0.47", "e_li6": "0.9", "t_mult": "0.05", "f_struct": "0.105", "f_cool": "0.03", "d_h": "0.011"},
           "S140": {"t_b": "0.46", "e_li6": "0.9", "t_mult": "0.05", "f_struct": "0.105", "f_cool": "0.03", "d_h": "0.011"}}
CASES = {}
for d in DESIGNS:
    for bc in ("white", "vacuum"):
        CASES[d + "_" + bc] = (d, bc, {})
CASES["REF_white_cells5cm"] = ("REF", "white", {"max_cell_cm": "5"})
CASES["REF_white_S4"] = ("REF", "white", {"sn_order": 4})
CASES["REF_white_P1"] = ("REF", "white", {"legendre_order": 1})
MESH_UNC_PPM = 14000          # 1.4 % (pre-declared)
REQ = 1155 * W // 1000        # 1.10 x 1.05


def ctx_design(name):
    ctx = spec.load(os.path.join(ROOT, "spec", "research_spec_v1.1.0.json"))
    x = ctx.values(ctx.reference_key) if DESIGNS[name] is None else {k: w.parse(v) for k, v in DESIGNS[name].items()}
    return ctx, x


def run(case):
    d, bc, num = CASES[case]
    ctx, x = ctx_design(d)
    out = model.evaluate_physics(x, ctx.const, ctx.theta_nominal)
    r = bt.tbr(x, ctx.const, out, numerics=num, left_bc=bc)
    rec = {"case": case, "design": d, "design_values": {k: w.fmt(v) for k, v in x.items()}, "left_bc": bc,
           "numerics_override": num, "surrogate_tbr": w.fmt(out["tbr"]), "transport_tbr": w.fmt(r["tbr"]),
           "tbr_1d": w.fmt(r["tbr_li"]), "tbr_by_zone": dict(zip(r["zones"], [w.fmt(v) for v in r["tbr_by_zone"]])),
           "tritium_other_nuclides": w.fmt(r["tritium_other"]), "leak_left": w.fmt(r["leak_left"]),
           "leak_right": w.fmt(r["leak_right"]), "net_removal": w.fmt(r["net_removal"]),
           "balance_residual": w.fmt(r["balance_residual"]), "cells": r["cells"], "angles": r["angles"],
           "lmax": r["lmax"], "source_group": r["source_group"], "inner_iterations": r["inner_iterations"]}
    os.makedirs(OUT, exist_ok=True)
    jsonio.dump(rec, os.path.join(OUT, case + ".json"))
    print(case + ": transport TBR " + rec["transport_tbr"][:8] + " (surrogate " + rec["surrogate_tbr"][:8] + ")", flush=True)


def summarize():
    R = {c: jsonio.load(os.path.join(OUT, c + ".json")) for c in CASES}
    T = {c: w.parse(R[c]["transport_tbr"]) for c in R}
    S = {d: w.parse(R[d + "_white"]["surrogate_tbr"]) for d in DESIGNS}
    res = {"rules": "docs/prereg/TRANSPORT_CHECK.md", "designs": {}}

    def rel(a, b):                          # (a/b - 1) in WAD
        return w.div(a, b) - W
    for d in ("S110", "S140"):
        gw, gv = T[d + "_white"] - T["REF_white"], T[d + "_vacuum"] - T["REF_vacuum"]
        big_w = abs(gw) * 1000000 > MESH_UNC_PPM * T["REF_white"]
        big_v = abs(gv) * 1000000 > MESH_UNC_PPM * T["REF_vacuum"]
        q1 = ("AGREE" if gw > 0 and gv > 0 and big_w and big_v else
              "DISAGREE" if gw < 0 and gv < 0 and big_w and big_v else "INDETERMINATE")
        sg = rel(S[d], S["REF"])
        tw, tv = rel(T[d + "_white"], T["REF_white"]), rel(T[d + "_vacuum"], T["REF_vacuum"])
        q2 = "YES" if min(tw, tv) <= sg <= max(tw, tv) else "NO"
        mw, mv = T[d + "_white"] >= REQ, T[d + "_vacuum"] >= REQ
        q3 = "MET" if mw and mv else "NOT_MET" if not mw and not mv else "DEPENDS_ON_BOUNDARY"
        res["designs"][d] = {"Q1_direction": q1, "Q2_magnitude_within_transport_range": q2,
                             "surrogate_relative_gain": w.fmt(sg), "transport_relative_gain_white": w.fmt(tw),
                             "transport_relative_gain_vacuum": w.fmt(tv), "Q3_requirement_1p155": q3}
    res["Q4_surrogate_within_bounds"] = {d: (min(T[d + "_white"], T[d + "_vacuum"]) <= S[d] <=
                                             max(T[d + "_white"], T[d + "_vacuum"])) for d in DESIGNS}
    base = w.parse(R["REF_white"]["tbr_1d"])
    res["convergence_REF_white"] = {c: w.fmt(rel(w.parse(R[c]["tbr_1d"]), base))
                                    for c in ("REF_white_cells5cm", "REF_white_S4", "REF_white_P1")}
    res["table"] = {d: {"surrogate": w.fmt(S[d]), "vacuum": R[d + "_vacuum"]["transport_tbr"],
                        "white": R[d + "_white"]["transport_tbr"]} for d in DESIGNS}
    jsonio.dump(res, os.path.join(OUT, "TRANSPORT_CHECK.json"))
    for d in ("S110", "S140"):
        print(d, res["designs"][d])
    print("Q4", res["Q4_surrogate_within_bounds"])


if __name__ == "__main__":
    if sys.argv[1] == "run":
        for c in (CASES if sys.argv[2] == "all" else [sys.argv[2]]):
            run(c)
    else:
        summarize()
