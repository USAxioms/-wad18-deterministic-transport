"""Tests for the cycle-2/3 R3 options and frozen-module integrity."""
import os
import hashlib
from r3capsule import spec, r3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def test_frozen_modules_match_freeze_records():
    import heldout
    for version, (mod, freeze) in heldout.FROZEN.items():
        assert _sha(os.path.join(ROOT, "r3capsule", mod + ".py")) == heldout.frozen_r3_hash(freeze), version


def test_escalation_runs_full_budget_with_valid_archive():
    ctx = spec.load(os.path.join(ROOT, "spec", "research_spec_v1.4.0.json"))
    ctx.r3["init_lhs_seed"] = 301
    res = r3.run(ctx, 700)
    assert res["stop"] == "BUDGET" and res["evaluator"].used == 700
    assert res["archive"].check_invariants(res["evaluator"].cache)


def test_new_options_default_off():
    ctx = spec.load(os.path.join(ROOT, "spec", "research_spec_v1.1.0.json"))
    for k in ("escalate", "escalate_trigger", "infeasible_focus", "pair_cap"):
        assert k not in ctx.r3


def test_heldout_sets_pairwise_disjoint():
    seen_seeds = set()
    seen_names = set()
    for v in ("1.2.0", "1.3.0", "1.4.0"):
        ho = spec.load(os.path.join(ROOT, "spec", "research_spec_v" + v + ".json")).raw["evaluation_protocol"]["heldout"]
        assert seen_seeds.isdisjoint(ho["seeds"])
        seen_seeds.update(ho["seeds"])
        names = {i["name"] for i in ho["instances"]}
        assert seen_names.isdisjoint(names)
        seen_names.update(names)
