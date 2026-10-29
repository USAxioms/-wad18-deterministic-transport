"""Cycle-2 R3 development harness (DEVELOPMENT DATA ONLY).

Development cells: the v1.1.0 conditions (budget 1000; R3 seeds 0-4 vs recorded NSGA-II
seeds 1-5) plus the used cycle-1 held-out cells H1-H4 x {1000, 2000} (R3 seeds 101-107 vs
recorded NSGA-II seeds 101-107). The cycle-2 held-out set (docs/prereg/
CYCLE2_HELDOUT_DECLARATION.json) is never touched here. Every variant is appended to
docs/dev/R3_DEV_LOG_CYCLE2.jsonl.
python3 dev/r3_dev_cycle2.py '<json options>' "<rationale>"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from r3capsule import spec, r3, pareto, jsonio, wad18 as w  # noqa: E402
import heldout  # noqa: E402

SP = os.path.join(ROOT, "spec", "research_spec_v1.2.0.json")
LOG = os.path.join(ROOT, "docs", "dev", "R3_DEV_LOG_CYCLE2.jsonl")


def med(xs):
    ys = sorted(xs)
    return ys[len(ys) // 2]


def r3_hv(ctx, opts, seed, budget):
    ctx.r3.update(opts)
    ctx.r3["init_lhs_seed"] = seed
    res = r3.run(ctx, budget)
    return pareto.hypervolume(list(res["archive"].items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)


def main():
    opts = jsonio.loads(sys.argv[1])
    why = sys.argv[2] if len(sys.argv) > 2 else ""
    cells = []
    # development instance
    comp = jsonio.load(os.path.join(ROOT, "results", "v1.1.0", "07_comparison.json"))
    nsga = [w.parse(s["hv"]) for s in comp["NSGA2"]]
    r3s = [r3_hv(spec.load(SP), opts, sd, 1000) for sd in range(5)]
    cells.append(("DEV", 1000, med(r3s), med(nsga)))
    # used cycle-1 held-out cells
    runs = []
    with open(os.path.join(ROOT, "results", "v1.2.0_heldout", "heldout_runs.jsonl"), encoding="utf-8") as fh:
        for line in fh:
            runs.append(jsonio.loads(line))
    ho = spec.load(SP).raw["evaluation_protocol"]["heldout"]
    for inst in ho["instances"]:
        for b in ho["budgets"]:
            ns = [w.parse(r["hv"]) for r in runs if r["instance"] == inst["name"] and r["budget"] == b
                  and r["method"] == "NSGA2"]
            rs = [r3_hv(heldout.instance_ctx(SP, inst), opts, sd, b) for sd in ho["seeds"]]
            cells.append((inst["name"][:2], b, med(rs), med(ns)))
    wins = sum(1 for c in cells if c[2] > c[3])
    n = 0
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            n = sum(1 for _ in fh)
    rec = {"variant": n + 1, "options": opts, "rationale": why, "cells_won": wins, "cells": len(cells),
           "detail": [{"cell": c[0] + "/" + str(c[1]), "r3_median": w.fmt(c[2]), "nsga2_median": w.fmt(c[3])}
                      for c in cells]}
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(jsonio.dumps(rec).replace("\n", "") + "\n")
    print("variant " + str(rec["variant"]) + ": won " + str(wins) + "/" + str(len(cells)) + "  " +
          "  ".join(c[0] + "/" + str(c[1]) + " " + ("+" if c[2] > c[3] else "-") +
                    w.fmt(c[2] - c[3])[:7] for c in cells))


if __name__ == "__main__":
    main()
