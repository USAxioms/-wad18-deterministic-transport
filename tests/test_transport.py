"""Verification tests for the integer S_N transport solver (analytic and conservation)."""
import os
from r3capsule import transport as T, wad18 as w, jsonio

W = w.WAD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _OneGroup:
    def __init__(self, st, ss):
        self.tot = [st]
        self.self_l = [[ss, 0, 0, 0]]
        self.into = [[]]
        self.out0 = [ss]
        self.h3_li = [0]
        self.h3_other = [0]


def test_gauss_legendre_s8_exactness():
    mus, wts = T.gauss_legendre(8)
    assert abs(sum(wts) - 2 * W) <= 10
    assert abs(sum(w.mul(a, w.mul(m, m)) for a, m in zip(wts, mus)) - 2 * W // 3) <= 20
    assert abs(sum(w.mul(a, w.pow_int(m, 14)) for a, m in zip(wts, mus)) - 2 * W // 15) <= 20
    assert w.fmt(mus[0]).startswith("0.96028985649753")       # published S8 node


def test_pure_absorber_matches_analytic_transmission():
    mus, wts = T.gauss_legendre(8)
    r = T.Slab([(10 * W, _OneGroup(W // 5, 0))], lmax=3, n_ang=8, hmax_cm=W).solve(0)
    jq = sum(w.mul(wts[m], mus[m]) for m in range(8) if mus[m] > 0)
    pin = w.div(W, jq)
    exact = sum(w.mul(w.mul(wts[m], mus[m]), w.mul(pin, w.exp(-w.div(2 * W, mus[m])))) for m in range(8) if mus[m] > 0)
    assert abs(r["leak_right"] - exact) <= 100


def test_balance_vacuum_and_white():
    for bc in ("vacuum", "white"):
        r = T.Slab([(20 * W, _OneGroup(W // 2, 9 * W // 20))], lmax=3, n_ang=8, hmax_cm=W).solve(0, left_bc=bc)
        assert abs(r["balance_residual"]) <= 10 ** 6
    r = T.Slab([(20 * W, _OneGroup(W // 2, W // 2))], lmax=3, n_ang=8, hmax_cm=W).solve(0, left_bc="white")
    assert abs(r["leak_right"] - W) <= 10 ** 6                  # c = 1, white: everything transmits


def test_recorded_blanket_runs_conserve_neutrons():
    d = os.path.join(ROOT, "results", "transport")
    for f in sorted(os.listdir(d)):
        if f.endswith(".json") and f != "TRANSPORT_CHECK.json":
            rec = jsonio.load(os.path.join(d, f))
            assert abs(w.parse(rec["balance_residual"])) * 10 ** 8 <= W     # < 1e-8 of the source
