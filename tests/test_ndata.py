"""Tests for the integer nuclear-data readers."""
import os
from r3capsule.ndata.matxs import Matxs, num, pow10
from r3capsule.ndata.endf import Endf, fnum
from r3capsule import wad18 as w

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data", "nuclear")


def test_number_parsing_exact_and_floor():
    assert num("1.24137E-03") == (1241370000000000, True)
    assert num("-2.0E+00") == (-2 * w.WAD, True)
    assert num("1.5E-20") == (0, False)
    assert num("-1.5E-20") == (-1, False)          # floor toward minus infinity
    assert fnum(" 1.000000-5") == (pow10(13), True)
    assert fnum(" 2.53+3") == (2530 * w.WAD, True)


def test_h1_structure_and_elastic_balance():
    m = Matxs(os.path.join(D, "01H_001.m"))
    assert m.material == "h1" and m.ngrp == [211, 42] and len(m.bounds["n"]) == 212
    assert m.bounds["n"][0] == 55000000 * w.WAD
    el = m.sub[0]["matrices"]["nelas"]
    assert len(el["data"]) == el["words_expected"] == el["lord"] * sum(el["jband"])
    out = [0] * 211
    pos = 0
    for l in range(211):
        for k in range(el["jband"][l]):
            out[el["ijj"][l] - k - 1] += el["data"][pos + k]
        pos += el["jband"][l] * el["lord"]
    v = m.vector("nelas")
    assert all(abs(out[g] - v[g]) * 100000 <= v[g] for g in range(211) if v[g] > 0)   # within 10 ppm


def test_li6_triton_thermal_magnitude():
    m = Matxs(os.path.join(D, "03Li006.m"))
    nt = m.vector("nt")
    assert 800 * w.WAD < nt[210] < 1200 * w.WAD        # Li-6(n,t) near thermal: order 10^3 barn
    e = Endf(os.path.join(D, "n_0325_3-Li-6.endf"))
    assert e.lrp() == 0 and (3, 105) in e.sections


def test_verification_record_is_pass():
    from r3capsule import jsonio
    rep = jsonio.load(os.path.join(ROOT, "results", "ndata_verification.json"))
    assert rep["verified"] is True
