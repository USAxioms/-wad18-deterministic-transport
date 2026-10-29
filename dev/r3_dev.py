"""R3 development harness (DEVELOPMENT SET ONLY).

Runs an R3 option variant on the development conditions (spec v1.1.0, budget 1000),
over R3 seeds 0-4 when the variant is stochastic (harness v2; variants 1-13 used v1 single runs),
and appends the outcome to docs/dev/R3_DEV_LOG.jsonl -- every variant, win or lose.
python3 dev/r3_dev.py '<json options>' "<rationale>"
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from r3capsule import spec, r3, pareto, jsonio, wad18 as w  # noqa: E402

DEV_SPEC = os.path.join(ROOT, "spec", "research_spec_v1.1.0.json")
LOG = os.path.join(ROOT, "docs", "dev", "R3_DEV_LOG.jsonl")
# dev baseline: recorded v1.1.0 NSGA-II hypervolumes (seeds 1-5, budget 1000)
DEV_NSGA2 = ["0.202709", "0.208245", "0.210875", "0.195982", "0.214107"]


def main():
    opts = jsonio.loads(sys.argv[1])
    why = sys.argv[2] if len(sys.argv) > 2 else ""
    hvs = []
    evs = []
    for sd in range(5):
        ctx = spec.load(DEV_SPEC)
        ctx.r3.update(opts)
        if ctx.r3.get("init_lhs_points", 0) or ctx.r3.get("reseed_on_fixed_point", 0):
            ctx.r3["init_lhs_seed"] = sd
        elif sd:
            break                      # deterministic variant: one run is the distribution
        res = r3.run(ctx, ctx.budget)
        hvs.append(pareto.hypervolume(list(res["archive"].items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp))
        evs.append(res["evaluator"].used)
    comp = jsonio.load(os.path.join(ROOT, "results", "v1.1.0", "07_comparison.json"))
    nsga = sorted(w.parse(s["hv"]) for s in comp["NSGA2"])
    r3s = sorted(hvs)
    med = r3s[len(r3s) // 2]
    hv = med
    beats = sum(1 for x in nsga if med > x)
    res = {"evaluator": None, "stop": "", "archive": None}
    n = 0
    if os.path.exists(LOG):
        with open(LOG, encoding="utf-8") as fh:
            n = sum(1 for _ in fh)
    rec = {"variant": n + 1, "harness": "v2-seed-distribution", "options": opts, "rationale": why,
           "hv": w.fmt(hv), "r3_hv_by_seed": [w.fmt(x) for x in hvs], "r3_min": w.fmt(r3s[0]),
           "evaluations_by_seed": evs,
           "median_beats_nsga2_seeds": beats, "of": len(nsga),
           "median_beats_nsga2_median": med > nsga[2], "r3_min_beats_nsga2_median": r3s[0] > nsga[2]}
    with open(LOG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(jsonio.dumps(rec).replace("\n", "") + "\n")
    print("variant " + str(rec["variant"]) + "  R3 median " + rec["hv"][:8] + "  min " + rec["r3_min"][:8] +
          "  median beats " + str(beats) + "/5 NSGA  evals " + str(evs))


if __name__ == "__main__":
    main()
