"""Verification tests for the integer cylindrical S_N solver."""
import os
from r3capsule import cylinder as C, wad18 as w, jsonio

W = w.WAD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class _One:
    def __init__(self, st, s0, s1=0):
        self.tot = [st]
        self.self_l = [[s0, s1]]
        self.into = [[]]
        self.out0 = [s0]
        self.h3_li = [0]
        self.h3_other = [0]


def test_quadrature_moments():
    lv = C.quadrature(8, 8)
    assert abs(sum(sum(ws) for _, ws in lv) - W) <= 100
    assert abs(sum(w.mul(a, m) for mus, ws in lv for a, m in zip(ws, mus))) <= 100
    assert abs(sum(w.mul(a, w.mul(m, m)) for mus, ws in lv for a, m in zip(ws, mus)) - W // 3) <= 100


def test_flat_flux_infinite_medium():
    cyl = C.Cylinder([(50 * W, _One(W // 2, 0), 25, True)], 8, 8)
    N = cyl.N
    inb = {}
    for _ in range(200):
        p, j, _, out = cyl.sweep(0, [W] * N, [0] * N, inb)
        new = {}
        for l, (mus, _) in enumerate(cyl.levels):
            for m in range(len(mus)):
                if mus[m] < 0:
                    new[(l, m)] = out.get((l, len(mus) - 1 - m), 0)
        if new == inb:
            break
        inb = new
    assert all(abs(x - 2 * W) <= 10 ** 6 for x in p)          # phi = s / Sigma_t = 2, flat
    assert all(abs(x) <= 10 ** 6 for x in j)


def test_conservation_with_void_and_anisotropy():
    cyl = C.Cylinder([(30 * W, None, 3, True), (40 * W, None, 2, False),
                      (80 * W, _One(W // 5, 9 * W // 50, 9 * W // 100), 20, False)], 8, 8)
    r = cyl.solve(0)
    assert abs(r["balance_residual"]) <= 10 ** 7


def test_recorded_blanket_runs_conserve_neutrons():
    d = os.path.join(ROOT, "results", "cylinder")
    for f in sorted(os.listdir(d)):
        if f.endswith(".json") and f != "CYLINDER_CHECK.json":
            assert abs(w.parse(jsonio.load(os.path.join(d, f))["balance_residual"])) * 10 ** 10 <= W
