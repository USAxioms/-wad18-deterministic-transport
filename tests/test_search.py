import os
from r3capsule import spec, r3, baselines

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = spec.load(os.path.join(ROOT, "spec", "research_spec.json"))


def test_r3_deterministic_and_within_budget():
    a = r3.run(CTX, 300)
    b = r3.run(CTX, 300)
    assert a["evaluator"].order == b["evaluator"].order
    assert a["evaluator"].used <= 300
    assert a["archive"].check_invariants(a["evaluator"].cache)


def test_r3_full_budget_reaches_declared_stop_with_monotone_hv():
    res = r3.run(CTX, CTX.budget)
    assert res["stop"] in ("FIXED_POINT", "BUDGET", "MAX_ITERATIONS")
    hvs = [it["hv"] for it in res["iterations"] if "hv" in it]
    assert all(hvs[i] <= hvs[i + 1] for i in range(len(hvs) - 1))


def test_baselines_deterministic_and_budgeted():
    for fn in (baselines.run_nsga2, baselines.run_random):
        x = fn(CTX, 3, 200)
        y = fn(CTX, 3, 200)
        assert x["evaluator"].order == y["evaluator"].order
        assert x["evaluator"].used == 200
        assert x["evaluator"].order[0] == CTX.reference_key


def test_different_seeds_differ():
    x = baselines.run_random(CTX, 1, 50)["evaluator"].order
    y = baselines.run_random(CTX, 2, 50)["evaluator"].order
    assert x != y
