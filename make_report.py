"""Assemble CAPSULE_REPORT.json and REPORT.md from result files (no recomputation)."""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import jsonio, CAPSULE_NAME, CAPSULE_VERSION  # noqa: E402

RD = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "v1.1.0")
R = lambda n: os.path.join(RD, n)


def main():
    po = jsonio.load(R("12_proof_obligations.json"))
    comp = jsonio.load(R("07_comparison.json"))
    ref = jsonio.load(R("03_reference_evaluation.json"))
    diag = jsonio.load(R("13_front_diagnostics.json"))
    repro = jsonio.load(R("15_reproduction_check.json"))
    tests = jsonio.load(os.path.join(ROOT, "results", "test_results.json"))
    oc = jsonio.load(R("11_output_checks.json"))
    ho_path = os.path.join(os.path.dirname(RD), os.path.basename(RD) + "_heldout", "heldout_summary.json")
    ho = jsonio.load(ho_path) if os.path.exists(ho_path) else None
    if ho is not None:
        hrep = os.path.join(os.path.dirname(ho_path), "heldout_reproduction.json")
        po["PO4_contribution_of_R3"] = {
            "status": ho["PO4_status"], "decided_on": "held-out cells",
            "cells_r3_median_beats_nsga2_median": ho["cells_r3_median_beats_nsga2_median"],
            "cells_total": ho["cells_total"],
            "heldout_byte_identical_rerun": jsonio.load(hrep)["byte_identical_rerun"] if os.path.exists(hrep) else None,
            "development_instance_single_run": po["PO4_contribution_of_R3"]}
    po["PO1_reproducible_execution"] = {"status": repro["PO1_status"],
                                        "files_identical": repro["identical"],
                                        "files_compared": repro["files_compared"],
                                        "scope": repro["scope"]}
    rep = {"capsule": CAPSULE_NAME, "version": CAPSULE_VERSION,
           "arithmetic": "WAD-18 pure integer; see results/zero_float_audit.json",
           "model_class": "REDUCED_ORDER_SURROGATE",
           "proof_obligations": po,
           "no_single_overall_status": "Deliberately omitted: per-obligation outcomes must not be collapsed into one PASS/FAIL string.",
           "reference": {"tbr": ref["tbr"], "dp": ref["dp"]},
           "hypervolume": {"R3": comp["hv_R3"], "NSGA2_min_median_max": comp["hv_NSGA2_min_median_max"],
                           "RANDOM_min_median_max": comp["hv_RANDOM_min_median_max"],
                           "R3_rank_among_all_runs": comp["R3_rank_among_all_runs"],
                           "total_runs": comp["total_runs"]},
           "R3_stop_reason": comp["R3"]["stop_reason"], "R3_evaluations": comp["R3"]["evaluations"],
           "front_designs_dominating_reference_nominal": diag["front_designs_dominating_reference_nominal"],
           "front_designs_meeting_selection_rule": diag["front_designs_meeting_selection_rule"],
           "tests": {"passed": tests["passed"], "failed": tests["failed"]},
           "output_checks_all_ok": oc["all_ok"]}
    jsonio.dump(rep, R("CAPSULE_REPORT.json"))

    best = diag["front"][-1] if diag["front"] else None
    L = []
    L.append("# Study report: spec " + jsonio.load(R("02_frozen_protocol.json"))["spec_sha256"][:12] + "\n")
    L.append("Generated from `results/` by `make_report.py`. All numbers are exact WAD-18 decimal renderings.\n")
    L.append("## Proof obligations\n")
    L.append("| Obligation | Status |")
    L.append("|---|---|")
    for k in sorted(po):
        L.append("| " + k + " | " + po[k]["status"] + " |")
    L.append("")
    L.append("## Search comparison (equal budget: " + str(comp["budget_unique_evaluations"]) + " unique evaluations)\n")
    L.append("| Method | Hypervolume (min / median / max) |")
    L.append("|---|---|")
    L.append("| R3 (deterministic, 1 run, stopped: " + comp["R3"]["stop_reason"] + " after " +
             str(comp["R3"]["evaluations"]) + " evals) | " + comp["hv_R3"] + " |")
    L.append("| NSGA-II (5 seeds) | " + " / ".join(comp["hv_NSGA2_min_median_max"]) + " |")
    L.append("| Random (5 seeds) | " + " / ".join(comp["hv_RANDOM_min_median_max"]) + " |")
    L.append("")
    hv3 = comp["hv_R3"]
    def gt(a, b):
        ia, fa = a.split(".")
        ib, fb = b.split(".")
        return (int(ia), int(fa.ljust(18, "0"))) > (int(ib), int(fb.ljust(18, "0")))
    n_beat_n = sum(1 for s in comp["NSGA2"] if gt(s["hv"], hv3))
    n_beat_r = sum(1 for s in comp["RANDOM"] if gt(s["hv"], hv3))
    L.append("R3 ranks " + str(comp["R3_rank_among_all_runs"]) + " of " + str(comp["total_runs"]) +
             " runs: " + str(n_beat_n) + " of " + str(len(comp["NSGA2"])) + " NSGA-II runs and " +
             str(n_beat_r) + " of " + str(len(comp["RANDOM"])) + " random runs exceed it. "
             "PO4 status under the predeclared rule: " + po["PO4_contribution_of_R3"]["status"] + ".\n")
    if ho is not None:
        L.append("## Held-out PO4 test (decides PO4)\n")
        L.append("| Instance | Budget | R3 median | NSGA-II median | Random median | R3 > NSGA-II |")
        L.append("|---|---|---|---|---|---|")
        for c in ho["cells"]:
            m = c["median_hv"]
            L.append("| " + c["instance"] + " | " + str(c["budget"]) + " | " + m["R3"][:8] + " | " +
                     m["NSGA2"][:8] + " | " + m["RANDOM"][:8] + " | " +
                     ("yes" if c["r3_median_gt_nsga2_median"] else "no") + " |")
        L.append("")
        L.append("R3 median beats NSGA-II median in " + str(ho["cells_r3_median_beats_nsga2_median"]) +
                 " of " + str(ho["cells_total"]) + " cells; rule requires 6. PO4: " + ho["PO4_status"] + ".\n")
    L.append("## Front versus reference\n")
    L.append("Reference: TBR " + ref["tbr"][:8] + ", dp " + ref["dp"][:9] + " Pa.\n")
    nd = diag["front_designs_dominating_reference_nominal"]
    if diag["front_designs_meeting_selection_rule"] == 0:
        L.append(str(nd) + " of " + str(diag["front_size"]) + " R3 front designs dominate the reference "
                 "at nominal theta, but none meets the predeclared selection rule (every normalised "
                 "constraint slack >= " + diag["selection_margin"][:4] + "). Each sits on or near at "
                 "least one constraint, so PO2, PO3 and PO5 are FAIL with reason NO_CANDIDATE. "
                 "See `13_front_diagnostics.json`.\n")
    else:
        sel = jsonio.load(R("08_selected_candidate.json"))["selected"]
        L.append(str(nd) + " of " + str(diag["front_size"]) + " R3 front designs dominate the "
                 "reference at nominal theta. The selection rule picked:\n")
        L.append("| Quantity | Reference | Selected |")
        L.append("|---|---|---|")
        for q in ("tbr", "dp", "T_wall", "T_peak", "velocity", "atten_exponent"):
            L.append("| " + q + " | " + ref["outputs"][q][:12] + " | " + sel["outputs"][q][:12] + " |")
        L.append("")
        L.append("Selected design: " + ", ".join(k + " = " + v.rstrip("0").rstrip(".")
                                                for k, v in sorted(sel["design"].items())) + ".\n")
    L.append("## Physical relevance\n")
    L.append(po["PO6_physical_relevance"]["detail"] + "\n")
    L.append("## Integrity\n")
    L.append("- Tests: " + str(tests["passed"]) + " passed, " + str(tests["failed"]) + " failed.")
    L.append("- Reproduction: " + str(repro["identical"]) + "/" + str(repro["files_compared"]) +
             " pipeline files byte-identical on re-execution.")
    L.append("- Output-level checks all OK: " + str(oc["all_ok"]).lower() + ".")
    L.append("- Zero-floating-point audit: `results/zero_float_audit.json` (run last, all studies).")
    with open(R("REPORT.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(L) + "\n")
    print("report written")


if __name__ == "__main__":
    main()
