"""Tests for the v1.1.0 rules (margin-aware search, multiscale fixed point, empty-archive focus)."""
import os
from r3capsule import spec, r3, baselines, wad18 as w
from r3capsule.evaluator import evaluate_once

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V101 = spec.load(os.path.join(ROOT, "spec", "research_spec.json"))
V110 = spec.load(os.path.join(ROOT, "spec", "research_spec_v1.1.0.json"))


def test_versions_and_margins():
    assert V101.spec_version == "1.0.1" and V101.search_margin == 0
    assert V110.spec_version == "1.1.0" and V110.search_margin == w.parse("0.05")
    assert all(c["ok"] for c in spec.validate(V110))


def test_only_declared_fields_differ():
    a, b = V101.raw, V110.raw
    for key in ("design_space", "reference_design", "constants", "theta", "objectives", "constraints"):
        assert a[key] == b[key], key
    ea, eb = a["evaluation_protocol"], b["evaluation_protocol"]
    for key in ("budget_unique_evaluations", "hypervolume_reference", "baseline_seeds",
                "nsga2", "selection_rule", "selection_margin"):
        assert ea[key] == eb[key], key


def test_reference_feasible_declared_infeasible_tightened():
    k = V110.reference_key
    assert evaluate_once(V110, k, V110.theta_nominal, 0)["feasible"]
    r = evaluate_once(V110, k, V110.theta_nominal)
    assert not r["feasible"]
    assert [c["name"] for c in r["constraints"] if c["slack"] < V110.search_margin] == ["C08_structure_fraction"]


def test_margin_zero_matches_declared_ok_flags():
    r = evaluate_once(V101, V101.reference_key, V101.theta_nominal)
    assert r["feasible"] == all(c["ok"] for c in r["constraints"])


def test_r3_v110_starts_from_infeasible_and_finds_margin_feasible():
    res = r3.run(V110, 400)
    ev = res["evaluator"]
    assert not ev.cache[V110.reference_key]["feasible"]
    assert len(res["archive"].items) > 0
    for k in res["archive"].items:
        assert min(c["slack"] for c in ev.cache[k]["constraints"]) >= V110.search_margin


def test_r3_v110_study_budget_stops_before_any_restart():
    # recorded behaviour of the frozen study: budget runs out during the first cycle,
    # so rule (a) is in force but never triggered within 1000 evaluations
    res = r3.run(V110, V110.budget)
    assert res["stop"] == "BUDGET" and res["evaluator"].used == V110.budget
    assert not any("restart_cycle" in it for it in res["iterations"])


def test_restart_mechanism_with_large_budget():
    # mechanism check outside the study: a restart occurs after a gaining cycle,
    # and the run then terminates at a multiscale FIXED_POINT
    res = r3.run(V110, 4000)
    restarts = [it for it in res["iterations"] if "restart_cycle" in it]
    assert restarts and restarts[0]["unit_step"] and restarts[0]["hv_gain"] == 0
    assert res["stop"] == "FIXED_POINT"
    last = [it for it in res["iterations"] if "hv_gain" in it][-1]
    assert last["unit_step"] and last["hv_gain"] == 0


def test_restart_disabled_in_v101():
    res = r3.run(V101, V101.budget)
    assert not any("restart_cycle" in it for it in res["iterations"])
    assert res["stop"] == "FIXED_POINT" and res["evaluator"].used == 874


def test_baselines_see_same_tightened_feasibility():
    res = baselines.run_random(V110, 1, 100)
    for k in res["evaluator"].order:
        rec = res["evaluator"].cache[k]
        if rec["feasible"]:
            assert min(c["slack"] for c in rec["constraints"]) >= V110.search_margin
