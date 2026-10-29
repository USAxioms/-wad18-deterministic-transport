"""End-to-end capsule execution (manuscript Section 5.1, steps 1-10)."""
import hashlib
import os
import platform
import sys

from . import CAPSULE_NAME, CAPSULE_VERSION
from . import wad18 as w
from . import jsonio, spec, pareto, r3, baselines, uq
from .evaluator import evaluate_once


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def fmt_rec(ctx, rec, full=True):
    d = {"key": list(rec["key"]), "status": rec["status"], "feasible": rec["feasible"],
         "tbr": w.fmt(rec["tbr"]), "dp": w.fmt(rec["dp"]),
         "violation": w.fmt(rec["violation"]), "n_violated": rec["n_violated"]}
    if full:
        d["design"] = {k: w.fmt(v) for k, v in ctx.values(rec["key"]).items()}
        if rec["outputs"] is not None:
            d["outputs"] = {k: w.fmt(v) for k, v in sorted(rec["outputs"].items())}
            d["constraints"] = [{"name": c["name"], "value": w.fmt(c["value"]),
                                 "limit": w.fmt(c["limit"]), "sense": c["sense"],
                                 "slack": w.fmt(c["slack"]), "ok": c["ok"]}
                                for c in rec["constraints"]]
    return d


def summarize(ctx, ev, ref_rec):
    recs = [ev.cache[k] for k in ev.order]
    fr = pareto.front_from_records(recs)
    pts = list(fr.items.values())
    hv = pareto.hypervolume(pts, ctx.hv_ref_tbr, ctx.hv_ref_dp)
    best_tbr = max([p[0] for p in pts if p[1] <= ref_rec["dp"]], default=None)
    min_dp = min([p[1] for p in pts if p[0] >= ref_rec["tbr"]], default=None)
    return {"evaluations": ev.used, "feasible_evaluations": sum(1 for r in recs if r["feasible"]),
            "domain_errors": ev.domain_errors, "front_size": len(pts), "hv": hv,
            "best_tbr_at_dp_le_reference": best_tbr, "min_dp_at_tbr_ge_reference": min_dp,
            "front": [{"key": list(k), "tbr": w.fmt(o[0]), "dp": w.fmt(o[1])} for k, o in fr.sorted()]}


def _fmt_summary(s):
    d = dict(s)
    d["hv"] = w.fmt(s["hv"])
    for k in ("best_tbr_at_dp_le_reference", "min_dp_at_tbr_ge_reference"):
        d[k] = w.fmt(s[k]) if s[k] is not None else None
    return d


def _median(xs):
    ys = sorted(xs)
    n = len(ys)
    return ys[n // 2] if n % 2 else (ys[n // 2 - 1] + ys[n // 2]) // 2


def select_candidate(ctx, r3res, ref_rec):
    ev = r3res["evaluator"]
    best = None
    for k, (tbr, dp) in r3res["archive"].sorted():
        rec = ev.cache[k]
        if not pareto.dominates((tbr, dp), (ref_rec["tbr"], ref_rec["dp"])):
            continue
        if min(c["slack"] for c in rec["constraints"]) < ctx.selection_margin:
            continue
        rank = (-tbr, dp, k)
        if best is None or rank < best[0]:
            best = (rank, k)
    return None if best is None else best[1]


def run(root, outdir, spec_path=None):
    os.makedirs(outdir, exist_ok=True)
    P = lambda name: os.path.join(outdir, name)
    if spec_path is None:
        spec_path = os.path.join(root, "spec", "research_spec.json")

    # 1. load and validate specification (method-level refinement)
    ctx = spec.load(spec_path)
    checks = spec.validate(ctx)
    jsonio.dump({"spec_sha256": _sha(spec_path), "checks": checks,
                 "all_ok": all(c["ok"] for c in checks)}, P("01_spec_validation.json"))

    # 2. freeze reference and protocol
    jsonio.dump({"spec_sha256": _sha(spec_path), "reference_key": list(ctx.reference_key),
                 "reference_design": {k: w.fmt(v) for k, v in ctx.values(ctx.reference_key).items()},
                 "budget_unique_evaluations": ctx.budget, "baseline_seeds": ctx.seeds,
                 "hv_reference": {"tbr": w.fmt(ctx.hv_ref_tbr), "dp": w.fmt(ctx.hv_ref_dp)},
                 "selection_margin": w.fmt(ctx.selection_margin),
                 "acceptance": ctx.raw["evaluation_protocol"]["acceptance"]},
                P("02_frozen_protocol.json"))

    # 3. reference evaluation
    ref = evaluate_once(ctx, ctx.reference_key, ctx.theta_nominal, 0)
    jsonio.dump(fmt_rec(ctx, ref), P("03_reference_evaluation.json"))
    if not ref["feasible"]:
        raise spec.SpecError("reference design infeasible under nominal theta")

    # 4-8. R3-directed search (domain-level refinement)
    rr = r3.run(ctx, ctx.budget)
    r3ev = rr["evaluator"]
    jsonio.dump_lines([fmt_rec(ctx, r3ev.cache[k]) for k in r3ev.order], P("04_r3_evaluations.jsonl"))
    jsonio.dump({"stop_reason": rr["stop"], "iterations": [
        {k: (w.fmt(v) if k in ("hv", "hv_gain") else v) for k, v in it.items()}
        for it in rr["iterations"]], "direction_success_tries": rr["direction_success"]},
        P("05_r3_iterations.json"))

    # baselines under the same unique-evaluation budget
    base = {"NSGA2": [], "RANDOM": []}
    base_lines = []
    for seed in ctx.seeds:
        for name, fn in (("NSGA2", baselines.run_nsga2), ("RANDOM", baselines.run_random)):
            res = fn(ctx, seed, ctx.budget)
            ev = res["evaluator"]
            s = summarize(ctx, ev, ref)
            s["seed"] = seed
            s["stop_reason"] = res["stop"]
            base[name].append(s)
            for k in ev.order:
                rec = fmt_rec(ctx, ev.cache[k], full=False)
                rec["method"] = name
                rec["seed"] = seed
                base_lines.append(rec)
    jsonio.dump_lines(base_lines, P("06_baseline_evaluations.jsonl"))

    # 9. comparison
    r3s = summarize(ctx, r3ev, ref)
    r3s["stop_reason"] = rr["stop"]
    hv_n = [s["hv"] for s in base["NSGA2"]]
    hv_r = [s["hv"] for s in base["RANDOM"]]
    comp = {"budget_unique_evaluations": ctx.budget,
            "R3": _fmt_summary(r3s),
            "NSGA2": [_fmt_summary(s) for s in base["NSGA2"]],
            "RANDOM": [_fmt_summary(s) for s in base["RANDOM"]],
            "hv_R3": w.fmt(r3s["hv"]),
            "hv_NSGA2_min_median_max": [w.fmt(min(hv_n)), w.fmt(_median(hv_n)), w.fmt(max(hv_n))],
            "hv_RANDOM_min_median_max": [w.fmt(min(hv_r)), w.fmt(_median(hv_r)), w.fmt(max(hv_r))],
            "R3_rank_among_all_runs": 1 + sum(1 for h in hv_n + hv_r if h > r3s["hv"]),
            "total_runs": 1 + len(hv_n) + len(hv_r)}
    jsonio.dump(comp, P("07_comparison.json"))

    # 10. candidate selection, robustness, output-level checks
    cand = select_candidate(ctx, rr, ref)
    po = {}
    if cand is None:
        cand_rec = None
        jsonio.dump({"selected": None}, P("08_selected_candidate.json"))
    else:
        cand_rec = r3ev.cache[cand]
        jsonio.dump({"selected": fmt_rec(ctx, cand_rec), "reference": fmt_rec(ctx, ref),
                     "selection_rule": ctx.raw["evaluation_protocol"]["selection_rule"]},
                    P("08_selected_candidate.json"))
        corners = uq.corners(ctx, cand)
        jsonio.dump(corners, P("09_uq_corners.json"))
        jsonio.dump({"candidate_key": list(cand), "rows": uq.sensitivity(ctx, cand)},
                    P("10_sensitivity.json"))

    # output-level refinement: independent re-evaluation and recomputation from logs
    out_checks = []
    if cand is not None:
        fresh = evaluate_once(ctx, cand, ctx.theta_nominal)
        out_checks.append({"check": "candidate_reevaluation_bit_identical",
                           "ok": fresh["outputs"] == cand_rec["outputs"]})
    re_hv = pareto.hypervolume(list(pareto.front_from_records(
        [r3ev.cache[k] for k in r3ev.order]).items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)
    out_checks.append({"check": "r3_hv_recomputed_from_log", "ok": re_hv == r3s["hv"]})
    out_checks.append({"check": "r3_archive_invariants",
                       "ok": rr["archive"].check_invariants(r3ev.cache)})
    out_checks.append({"check": "budgets_respected",
                       "ok": r3ev.used <= ctx.budget and all(
                           s["evaluations"] <= ctx.budget for v in base.values() for s in v)})
    jsonio.dump({"checks": out_checks, "all_ok": all(c["ok"] for c in out_checks)},
                P("11_output_checks.json"))

    # proof obligations
    po["PO1_reproducible_execution"] = {
        "status": "SEE_REPRODUCTION_CHECK",
        "detail": "Determined by reproduce.py, which re-executes the pipeline and compares every result file byte-for-byte. Independent third-party reproduction has not occurred."}
    # front diagnostics: how R3 front designs relate to the reference and to the margin
    diag = []
    n_dom = 0
    for k, (tbr, dp) in rr["archive"].sorted():
        rec = r3ev.cache[k]
        dom = pareto.dominates((tbr, dp), (ref["tbr"], ref["dp"]))
        n_dom += 1 if dom else 0
        diag.append({"key": list(k), "tbr": w.fmt(tbr), "dp": w.fmt(dp),
                     "dominates_reference_nominal": dom,
                     "min_normalised_slack": w.fmt(min(c["slack"] for c in rec["constraints"])),
                     "constraints_below_selection_margin": [
                         {"name": c["name"], "slack": w.fmt(c["slack"])}
                         for c in rec["constraints"] if c["slack"] < ctx.selection_margin]})
    jsonio.dump({"selection_margin": w.fmt(ctx.selection_margin),
                 "front_size": len(diag), "front_designs_dominating_reference_nominal": n_dom,
                 "front_designs_meeting_selection_rule": 0 if cand is None else 1,
                 "front": diag}, P("13_front_diagnostics.json"))

    if cand_rec is None:
        why = ("No R3 front design satisfies the predeclared selection rule (dominates the reference "
               "AND every normalised constraint slack >= selection_margin). " + str(n_dom) +
               " front designs dominate the reference at nominal theta, but each lies within the "
               "margin of at least one constraint; see 13_front_diagnostics.json.")
        po["PO2_constraint_satisfaction"] = {"status": "FAIL", "reason": "NO_CANDIDATE", "detail": why}
        po["PO3_engineering_improvement"] = {"status": "FAIL", "reason": "NO_CANDIDATE", "detail": why,
                                             "front_designs_dominating_reference_nominal": n_dom}
        po["PO5_robustness"] = {"status": "FAIL", "reason": "NO_CANDIDATE", "detail": why}
    else:
        declared = evaluate_once(ctx, cand, ctx.theta_nominal, 0)
        po["PO2_constraint_satisfaction"] = {
            "status": "PASS" if declared["feasible"] else "FAIL",
            "min_normalised_slack": w.fmt(min(c["slack"] for c in declared["constraints"])),
            "scope": "nominal theta, surrogate model"}
        imp = pareto.dominates((cand_rec["tbr"], cand_rec["dp"]), (ref["tbr"], ref["dp"]))
        po["PO3_engineering_improvement"] = {
            "status": "PASS" if imp else "FAIL",
            "tbr_reference": w.fmt(ref["tbr"]), "tbr_candidate": w.fmt(cand_rec["tbr"]),
            "dp_reference": w.fmt(ref["dp"]), "dp_candidate": w.fmt(cand_rec["dp"]),
            "scope": "nominal theta, surrogate model"}
        n_both = corners["feasible_and_dominates"]
        po["PO5_robustness"] = {
            "status": "PASS" if n_both == 64 else ("FAIL" if corners["candidate_feasible"] == 0 else "PARTIAL"),
            "corners": 64, "feasible": corners["candidate_feasible"],
            "dominates_reference": corners["candidate_dominates_reference"],
            "feasible_and_dominates": n_both}
    if "heldout" in ctx.raw["evaluation_protocol"]:
        s4 = "SEE_HELDOUT"
    elif r3s["hv"] > max(hv_n):
        s4 = "STRONG"
    elif r3s["hv"] > _median(hv_n):
        s4 = "PASS"
    else:
        s4 = "FAIL"
    po["PO4_contribution_of_R3"] = {
        "status": s4, "hv_R3": w.fmt(r3s["hv"]),
        "hv_NSGA2_median": w.fmt(_median(hv_n)), "hv_NSGA2_max": w.fmt(max(hv_n)),
        "hv_RANDOM_median": w.fmt(_median(hv_r)),
        "R3_evaluations_used": r3s["evaluations"], "R3_stop_reason": rr["stop"],
        "note": "R3 is deterministic (single run); baselines are 5 seeds each. Small-sample comparison."}
    po["PO6_physical_relevance"] = {
        "status": "NOT_ESTABLISHED",
        "detail": "Reduced-order surrogate correlations with declared, unvalidated constants. No Monte Carlo transport (e.g. OpenMC), CFD, benchmark, or experimental comparison was performed. No claim about a physical blanket follows from this capsule."}
    jsonio.dump(po, P("12_proof_obligations.json"))

    env = {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
           "system": platform.system(), "machine": platform.machine(),
           "capsule": CAPSULE_NAME, "capsule_version": CAPSULE_VERSION,
           "dependencies": "Python standard library only"}
    jsonio.dump(env, P("00_environment.json"))
    return {"ctx": ctx, "po": po, "comparison": comp, "candidate": cand}
