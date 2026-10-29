"""Tests for v1.2.0 R3 options and held-out integrity guards."""
import os
from r3capsule import spec, r3

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
V120 = spec.load(os.path.join(ROOT, "spec", "research_spec_v1.2.0.json"))


def test_lhs_is_latin_and_deterministic():
    a = r3._lhs(V120, 20, 7)
    assert a == r3._lhs(V120, 20, 7) and a != r3._lhs(V120, 20, 8)
    # continuous Latin hypercube floored onto the grid: the j-th smallest value of each
    # variable lies in stratum j, i.e. floor(j*size/n) <= v_j <= floor(((j+1)*size-1)/n)
    for i, size in enumerate(V120.n):
        vals = sorted(k[i] for k in a)
        for j, v in enumerate(vals):
            assert (j * size) // 20 <= v <= ((j + 1) * size - 1) // 20, (i, j, v)


def test_v120_r3_seeded_uses_full_budget_and_valid_archive():
    for sd in (0, 101):
        ctx = spec.load(os.path.join(ROOT, "spec", "research_spec_v1.2.0.json"))
        ctx.r3["init_lhs_seed"] = sd
        res = r3.run(ctx, 600)
        assert res["stop"] == "BUDGET" and res["evaluator"].used == 600
        assert res["archive"].check_invariants(res["evaluator"].cache)


def test_heldout_conditions_disjoint_from_development():
    ho = V120.raw["evaluation_protocol"]["heldout"]
    assert set(ho["seeds"]).isdisjoint({0, 1, 2, 3, 4, 5})
    assert 2000 in ho["budgets"]
    for inst in ho["instances"]:
        assert inst["constants"] or inst["theta"]   # every instance differs from development


def test_heldout_refuses_modified_r3():
    import heldout
    assert heldout.frozen_r3_hash("FREEZE_v1.2.0.md") == heldout.sha(os.path.join(ROOT, "r3capsule", "r3_v120.py"))
