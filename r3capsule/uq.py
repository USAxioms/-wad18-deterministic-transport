"""Uncertainty corners (2^6 = 64) and one-at-a-time sensitivity, all WAD-18."""
from . import wad18 as w
from . import pareto
from .evaluator import evaluate_once


def corners(ctx, cand_key):
    ref_key = ctx.reference_key
    rows = []
    min_slack = {}
    n_feas = 0
    n_dom = 0
    n_both = 0
    for mask in range(64):
        th = ctx.theta_corner(mask)
        rc = evaluate_once(ctx, cand_key, th, 0)
        rr = evaluate_once(ctx, ref_key, th, 0)
        dom = (rc["status"] == "OK" and rr["status"] == "OK" and
               pareto.dominates((rc["tbr"], rc["dp"]), (rr["tbr"], rr["dp"])))
        n_feas += 1 if rc["feasible"] else 0
        n_dom += 1 if dom else 0
        n_both += 1 if (dom and rc["feasible"]) else 0
        if rc["constraints"]:
            for c in rc["constraints"]:
                if c["name"] not in min_slack or c["slack"] < min_slack[c["name"]]:
                    min_slack[c["name"]] = c["slack"]
        rows.append({"mask": mask,
                     "theta": {k: w.fmt(v) for k, v in sorted(th.items())},
                     "candidate_feasible": rc["feasible"],
                     "candidate_tbr": w.fmt(rc["tbr"]), "candidate_dp": w.fmt(rc["dp"]),
                     "reference_feasible": rr["feasible"],
                     "reference_tbr": w.fmt(rr["tbr"]), "reference_dp": w.fmt(rr["dp"]),
                     "candidate_dominates_reference": dom,
                     "violated": [c["name"] for c in (rc["constraints"] or []) if not c["ok"]]})
    return {"corners": 64, "candidate_feasible": n_feas,
            "candidate_dominates_reference": n_dom,
            "feasible_and_dominates": n_both,
            "min_slack_over_corners": {k: w.fmt(v) for k, v in sorted(min_slack.items())},
            "rows": rows}


def sensitivity(ctx, key):
    base = evaluate_once(ctx, key, ctx.theta_nominal, 0)
    out = []
    for name in sorted(ctx.theta_nominal):
        nom = ctx.theta_nominal[name]
        d = w.mul(nom, ctx.theta_rel[name])
        for label, val in (("low", nom - d), ("high", nom + d)):
            th = dict(ctx.theta_nominal)
            th[name] = val
            r = evaluate_once(ctx, key, th, 0)
            out.append({"parameter": name, "level": label, "value": w.fmt(val),
                        "d_tbr": w.fmt(r["tbr"] - base["tbr"]),
                        "d_dp": w.fmt(r["dp"] - base["dp"]),
                        "d_T_peak": w.fmt(r["outputs"]["T_peak"] - base["outputs"]["T_peak"]),
                        "d_T_wall": w.fmt(r["outputs"]["T_wall"] - base["outputs"]["T_wall"]),
                        "feasible": r["feasible"],
                        "violated": [c["name"] for c in r["constraints"] if not c["ok"]]})
    return out
