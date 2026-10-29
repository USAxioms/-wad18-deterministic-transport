"""Confirmatory held-out PO4 test (spec v1.2.0).

python3 heldout.py [spec_path] [out_dir]
Refuses to run if r3capsule/r3.py differs from the hash in docs/prereg/FREEZE_v1.2.0.md.
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
import importlib  # noqa: E402
from r3capsule import spec, baselines, pareto, jsonio, wad18 as w  # noqa: E402

# protocol version -> (R3 module file as frozen, freeze record holding its hash, held-out source)
FROZEN = {"1.2.0": ("r3_v120", "FREEZE_v1.2.0.md"),
          "1.3.0": ("r3_v130", "FREEZE_v1.3.0.md"),
          "1.4.0": ("r3", "FREEZE_v1.4.0.md")}


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def frozen_r3_hash(freeze="FREEZE_v1.2.0.md"):
    with open(os.path.join(ROOT, "docs", "prereg", freeze), encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("- r3capsule/r3.py SHA-256"):
                return line.split("`")[1]
    raise SystemExit("freeze record missing r3 hash")


def instance_ctx(sp, inst):
    ctx = spec.load(sp)
    for k, v in inst["constants"].items():
        ctx.const[k] = w.parse(v)
    for k, v in inst["theta"].items():
        ctx.theta_nominal[k] = w.parse(v)
    return ctx


def hv_of(ctx, ev):
    fr = pareto.front_from_records([ev.cache[k] for k in ev.order])
    return pareto.hypervolume(list(fr.items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)


def median(xs):
    ys = sorted(xs)
    return ys[len(ys) // 2]           # 7 seeds: exact middle element


def main():
    sp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec", "research_spec_v1.2.0.json")
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "results", "v1.2.0_heldout")
    version = spec.load(sp).raw["metadata"]["spec_version"]
    mod_name, freeze = FROZEN[version]
    if sha(os.path.join(ROOT, "r3capsule", mod_name + ".py")) != frozen_r3_hash(freeze):
        raise SystemExit(mod_name + ".py differs from frozen v" + version + " hash; refusing to run")
    r3 = importlib.import_module("r3capsule." + mod_name)
    os.makedirs(out, exist_ok=True)
    ho = spec.load(sp).raw["evaluation_protocol"]["heldout"]
    runs = []
    cells = []
    for inst in ho["instances"]:
        for budget in ho["budgets"]:
            hv = {"R3": [], "NSGA2": [], "RANDOM": []}
            for seed in ho["seeds"]:
                ctx = instance_ctx(sp, inst)
                ctx.r3["init_lhs_seed"] = seed
                res = {"R3": r3.run(ctx, budget)["evaluator"],
                       "NSGA2": baselines.run_nsga2(ctx, seed, budget)["evaluator"],
                       "RANDOM": baselines.run_random(ctx, seed, budget)["evaluator"]}
                for m, ev in res.items():
                    h = hv_of(ctx, ev)
                    hv[m].append(h)
                    runs.append({"instance": inst["name"], "budget": budget, "seed": seed,
                                 "method": m, "hv": w.fmt(h), "evaluations": ev.used})
            med = {m: median(v) for m, v in hv.items()}
            cells.append({"instance": inst["name"], "budget": budget,
                          "median_hv": {m: w.fmt(v) for m, v in med.items()},
                          "nsga2_max_hv": w.fmt(max(hv["NSGA2"])),
                          "r3_median_gt_nsga2_median": med["R3"] > med["NSGA2"],
                          "r3_median_gt_nsga2_max": med["R3"] > max(hv["NSGA2"]),
                          "r3_seeds_beating_nsga2_median": sum(1 for x in hv["R3"] if x > med["NSGA2"]),
                          "r3_median_gt_random_median": med["R3"] > med["RANDOM"]})
            jsonio.dump_lines(runs, os.path.join(out, "heldout_runs.jsonl"))
            print(inst["name"] + " budget " + str(budget) + " done", flush=True)
    wins = sum(1 for c in cells if c["r3_median_gt_nsga2_median"])
    strong = sum(1 for c in cells if c["r3_median_gt_nsga2_max"])
    status = "STRONG" if (wins >= 6 and strong >= 6) else ("PASS" if wins >= 6 else "FAIL")
    jsonio.dump({"spec_sha256": sha(sp), "r3_sha256": frozen_r3_hash(freeze),
                 "cells": cells, "cells_total": len(cells),
                 "cells_r3_median_beats_nsga2_median": wins,
                 "cells_r3_median_beats_nsga2_max": strong,
                 "rule": spec.load(sp).raw["evaluation_protocol"]["acceptance"]["PO4_contribution_of_R3"],
                 "PO4_status": status}, os.path.join(out, "heldout_summary.json"))
    print("PO4 held-out: " + status + " (" + str(wins) + "/8 cells)")


if __name__ == "__main__":
    main()
