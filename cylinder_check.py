"""Cylindrical transport check (docs/prereg/CYLINDER_CHECK.md).

python3 cylinder_check.py run CASE|all   -> results/cylinder/CASE.json
python3 cylinder_check.py summarize      -> results/cylinder/CYLINDER_CHECK.json (rules applied in integers)
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import model, jsonio, wad18 as w, blanket_transport as bt  # noqa: E402
from transport_check import DESIGNS, ctx_design  # noqa: E402

W = w.WAD
OUT = os.path.join(ROOT, "results", "cylinder")
SLAB = os.path.join(ROOT, "results", "transport")
REQ = 1155 * W // 1000
CASES = {"REF": ("REF", {}, {}), "REF_cells5cm": ("REF", {"max_cell_cm": "5"}, {}),
         "REF_az16": ("REF", {"azimuths": 16}, {}), "REF_gl4": ("REF", {"gl_order": 4}, {}),
         "S110": ("S110", {}, {}), "S140": ("S140", {}, {}),
         "REF_fw2p5m": ("REF", {}, {"plasma_radius_m": "2.3", "first_wall_radius_m": "2.5"}),
         "REF_fw4m": ("REF", {}, {"plasma_radius_m": "3.8", "first_wall_radius_m": "4.0"})}
CONV = ["REF_cells5cm", "REF_az16", "REF_gl4"]


def run(case):
    d, num, geo = CASES[case]
    ctx, x = ctx_design(d)
    out = model.evaluate_physics(x, ctx.const, ctx.theta_nominal)
    r = bt.tbr_cylinder(x, ctx.const, out, numerics=num, geometry=geo)
    rec = {"case": case, "design": d, "numerics_override": num, "geometry_override": geo,
           "surrogate_tbr": w.fmt(out["tbr"]), "cylinder_tbr": w.fmt(r["tbr"]), "tbr_1d": w.fmt(r["tbr_li"]),
           "tbr_by_zone": dict(zip(r["zones"], [w.fmt(v) for v in r["tbr_by_zone"]])),
           "tritium_other_nuclides": w.fmt(r["tritium_other"]), "leak_outer": w.fmt(r["leak_outer"]),
           "net_removal": w.fmt(r["net_removal"]), "balance_residual": w.fmt(r["balance_residual"]),
           "cells": r["cells"], "directions": r["directions"], "p1_iterations": r["p1_iterations"],
           "source_group": r["source_group"]}
    os.makedirs(OUT, exist_ok=True)
    jsonio.dump(rec, os.path.join(OUT, case + ".json"))
    print(case + ": cylinder TBR " + rec["cylinder_tbr"][:8] + " (surrogate " + rec["surrogate_tbr"][:8] + ")", flush=True)


def summarize():
    R = {c: jsonio.load(os.path.join(OUT, c + ".json")) for c in CASES}
    T = {c: w.parse(R[c]["cylinder_tbr"]) for c in R}

    def rel(a, b):
        return w.div(a, b) - W
    U = max(abs(rel(T[c], T["REF"])) for c in CONV)
    res = {"rules": "docs/prereg/CYLINDER_CHECK.md", "numerical_uncertainty_U": w.fmt(U),
           "convergence": {c: w.fmt(rel(T[c], T["REF"])) for c in CONV}, "designs": {}}
    for d in DESIGNS:
        sw = w.parse(jsonio.load(os.path.join(SLAB, d + "_white.json"))["transport_tbr"])
        sv = w.parse(jsonio.load(os.path.join(SLAB, d + "_vacuum.json"))["transport_tbr"])
        sur = w.parse(R[d]["surrogate_tbr"])
        e = {"cylinder_tbr": R[d]["cylinder_tbr"], "slab_vacuum": w.fmt(sv), "slab_white": w.fmt(sw),
             "surrogate": R[d]["surrogate_tbr"], "C1_within_slab_bracket": "YES" if sv <= T[d] <= sw else "NO",
             "C3_requirement_1p155": ("MET" if T[d] > w.mul(REQ, W + U) else
                                      "NOT_MET" if T[d] < w.mul(REQ, W - U) else "WITHIN_UNCERTAINTY"),
             "C4_surrogate_relative_error": w.fmt(rel(sur, T[d]))}
        if d != "REF":
            gap = T[d] - T["REF"]
            band = w.mul(U, T["REF"])
            e["C2_direction"] = "AGREE" if gap > band else "DISAGREE" if gap < -band else "INDETERMINATE"
            cg = rel(T[d], T["REF"])
            sg = rel(sur, w.parse(R["REF"]["surrogate_tbr"]))
            e["cylinder_relative_gain"], e["surrogate_relative_gain"] = w.fmt(cg), w.fmt(sg)
            e["C4_gain_within_U"] = "YES" if abs(sg - cg) <= U else "NO"
        res["designs"][d] = e
    res["sensitivity_first_wall_radius"] = {c: R[c]["cylinder_tbr"] for c in ("REF_fw2p5m", "REF", "REF_fw4m")}
    jsonio.dump(res, os.path.join(OUT, "CYLINDER_CHECK.json"))
    print("U", res["numerical_uncertainty_U"][:8], res["convergence"])
    for d, e in res["designs"].items():
        print(d, {k: (v[:8] if isinstance(v, str) and v[:1] in "0-" else v) for k, v in e.items()})
    print("first-wall radius sensitivity", res["sensitivity_first_wall_radius"])


if __name__ == "__main__":
    if sys.argv[1] == "run":
        for c in (CASES if sys.argv[2] == "all" else [sys.argv[2]]):
            run(c)
    else:
        summarize()
