import os
from r3capsule import spec, model, wad18 as w
from r3capsule.evaluator import evaluate_once

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CTX = spec.load(os.path.join(ROOT, "spec", "research_spec.json"))
W = w.WAD


def _ev(**changes):
    x = CTX.values(CTX.reference_key)
    for k, v in changes.items():
        x[k] = w.parse(v)
    return model.evaluate_physics(x, CTX.const, CTX.theta_nominal)


def test_spec_validates():
    assert all(c["ok"] for c in spec.validate(CTX))


def test_reference_golden_values():
    out = _ev()
    assert w.fmt(out["tbr"], 6) == "1.160212"
    assert w.fmt(out["dp"], 3) == "20797.644"
    assert w.fmt(out["T_peak"], 3) == "497.064"
    assert w.fmt(out["sigma_hoop"], 0) == "77500000"


def test_reference_feasible():
    assert evaluate_once(CTX, CTX.reference_key, CTX.theta_nominal)["feasible"]


def test_hand_calculable_quantities():
    out = _ev()
    assert out["sigma_hoop"] == 77500000 * W
    assert out["t_shield"] == w.parse("0.35")
    assert out["f_struct_min"] == w.parse("0.10")
    assert out["f_struct_ratio"] == W
    assert out["prandtl"] == w.parse("0.86")


def test_monotonic_physics():
    assert _ev(e_li6="0.60")["tbr"] < _ev(e_li6="0.90")["tbr"]
    assert _ev(t_b="0.40")["tbr"] < _ev(t_b="0.50")["tbr"]
    assert _ev(t_mult="0.03")["tbr"] > _ev()["tbr"]
    assert _ev(f_cool="0.0300")["dp"] < _ev()["dp"]
    assert _ev(d_h="0.0120")["dp"] < _ev()["dp"]
    assert _ev(e_li6="0.60")["T_peak"] < _ev()["T_peak"]
    assert _ev(f_struct="0.120")["tbr"] < _ev()["tbr"]
    assert _ev(t_b="0.55")["atten_exponent"] < _ev()["atten_exponent"]


def test_constraint_detection():
    x = CTX.values(CTX.reference_key)
    x["e_li6"] = w.parse("0.30")
    rec = evaluate_once(CTX, CTX.key_from_values(x), CTX.theta_nominal)
    assert "C01_tbr_min" in [c["name"] for c in rec["constraints"] if not c["ok"]]
    assert not rec["feasible"]
    x = CTX.values(CTX.reference_key)
    x["t_b"] = w.parse("0.60")
    rec = evaluate_once(CTX, CTX.key_from_values(x), CTX.theta_nominal)
    names = [c["name"] for c in rec["constraints"] if not c["ok"]]
    assert "C06_shield_attenuation" in names and "C08_structure_fraction" in names


def test_outputs_are_ints():
    for v in _ev().values():
        assert type(v) is int
