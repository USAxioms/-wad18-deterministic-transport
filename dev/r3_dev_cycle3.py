"""Cycle-3 R3 development harness (DEVELOPMENT DATA ONLY).

Development cells (17): the v1.1.0 conditions (budget 1000; R3 seeds 0-4 vs recorded NSGA-II
seeds 1-5) plus the used held-out cells of cycle 1 (H1-H4 x {1000, 2000}) and cycle 2
(H5-H8 x {1500, 3000}), each with its recorded NSGA-II runs on the same seeds. The cycle-2 held-out set (docs/prereg/
CYCLE3_HELDOUT_DECLARATION.json) is never touched here. Every variant is appended to
docs/dev/R3_DEV_LOG_CYCLE3.jsonl.
python3 dev/r3_dev_cycle2.py '<json options>' "<rationale>"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from r3capsule import spec, r3, pareto, jsonio, wad18 as w  # noqa: E402
import heldout  # noqa: E402

SP = os.path.join(ROOT, "spec", "research_spec_v1.3.0.json")   # base R3 settings + ctx; options overlay
LOG = os.path.join(ROOT, "docs", "dev", "R3_DEV_LOG_CYCLE3.jsonl")


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
    # used held-out cells of cycles 1 and 2 (now development data)
    for sp_used, rdir in (("research_spec_v1.2.0.json", "v1.2.0_heldout"),
                          ("research_spec_v1.3.0.json", "v1.3.0_heldout")):
        sp_u = os.path.join(ROOT, "spec", sp_used)
        runs = []
        with open(os.path.join(ROOT, "results", rdir, "heldout_runs.jsonl"), encoding="utf-8") as fh:
            for line in fh:
                runs.append(jsonio.loads(line))
        ho = spec.load(sp_u).raw["evaluation_protocol"]["heldout"]
        for inst in ho["instances"]:
            for b in ho["budgets"]:
                ns = [w.parse(r["hv"]) for r in runs if r["instance"] == inst["name"] and r["budget"] == b
                      and r["method"] == "NSGA2"]
                rs = [r3_hv(heldout.instance_ctx(SP, inst), opts, sd, b) for sd in ho["seeds"]]
                cells.append((inst["name"].split("_")[0], b, med(rs), med(ns)))
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
