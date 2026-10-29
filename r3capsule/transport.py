"""Integer-exact 1-D slab multigroup discrete-ordinates neutron transport (WAD-18).

Equation (per group g, slab coordinate x, direction cosine mu):
    mu dpsi/dx + St psi = sum_l (2l+1)/2 P_l(mu) S_l(x),
    S_l = sum_g' Sigma_l(g'->g) phi_l,g'   with   phi_l = sum_m w_m P_l(mu_m) psi_m.
MATXS P_l matrices carry no (2l+1) factor (verified: H-1 P1/P0 equals mubar); the factor is
applied here. (n,2n) multiplicity is inside the matrices (verified: row sum = 2 sigma).

Discretisation: Gauss-Legendre S_N (nodes/weights computed by integer Newton iteration),
step-characteristic spatial scheme (positive, exactly cell-conservative). Within each group
the P0 and P1 scattering sources are solved implicitly (dense LU on 2N unknowns); P2..PL are
iterated. Thermal groups with upscatter are iterated as a block (Gauss-Seidel).
No floating point anywhere.
"""
from . import wad18 as w
from .ndata.matxs import Matxs

W = w.WAD
G36 = W * W          # guard scale for quadrature construction


# ---------------------------------------------------------------- quadrature
def _legendre36(n, x):
    """(P_n(x), P_{n-1}(x)) at guard scale 10^36, x at guard scale."""
    p0, p1 = G36, x
    if n == 0:
        return p0, 0
    for k in range(2, n + 1):
        p0, p1 = p1, ((2 * k - 1) * x * p1 // G36 - (k - 1) * p0) // k
    return p1, p0


def gauss_legendre(n):
    """Nodes (descending, positive first) and weights of n-point Gauss-Legendre, WAD-18."""
    assert n % 2 == 0
    roots = []
    steps = 20000
    prev_x, prev_v = G36, _legendre36(n, G36)[0]
    for k in range(steps - 1, -1, -1):          # bracket roots on (0, 1]
        x = k * G36 // steps
        v = _legendre36(n, x)[0]
        if (v <= 0 < prev_v) or (v >= 0 > prev_v):
            lo, hi = x, prev_x
            for _ in range(140):                 # bisection to guard precision
                mid = (lo + hi) // 2
                vm = _legendre36(n, mid)[0]
                if (vm <= 0) == (_legendre36(n, lo)[0] <= 0):
                    lo = mid
                else:
                    hi = mid
            roots.append((lo + hi) // 2)
        prev_x, prev_v = x, v
    assert len(roots) == n // 2, ("roots found", len(roots))
    nodes, weights = [], []
    for r in roots:
        pn1 = _legendre36(n, r)[1]
        num = 2 * (G36 - r * r // G36)
        den = n * n * pn1 * pn1 // G36
        wt = num * G36 // den
        nodes.append(r // W)
        weights.append(wt // W)
    mus = nodes + [-x for x in nodes]
    wts = weights + weights
    return mus, wts


def legendre_wad(l, mu):
    p0, p1 = W, mu
    if l == 0:
        return W
    for k in range(2, l + 1):
        p0, p1 = p1, ((2 * k - 1) * w.mul(mu, p1) - (k - 1) * p0) // k
    return p1


# ---------------------------------------------------------------- nuclear data
class Nuclide:
    """Group data of one nuclide needed for transport: total, triton production, P_l transfer."""

    def __init__(self, path, lmax):
        m = Matxs(path)
        s = m.sub[0]
        self.name = m.material
        self.awr = m.amass
        self.ng = m.ngrp[0]
        self.bounds = m.bounds["n"]
        self.tot = m.vector("ntot0")
        self.h3 = m.vector(".h3") if ".h3" in s["vectors"] else [0] * self.ng
        trans = {}
        for M in s["matrices"].values():
            pos = 0
            L = M["lord"]
            for sink in range(M["ng_out"]):
                n = M["jband"][sink]
                for k in range(n):
                    src = M["ijj"][sink] - k - 1
                    vals = [M["data"][pos + l * n + k] if l < L else 0 for l in range(lmax + 1)]
                    if any(vals):
                        key = (src, sink)
                        cur = trans.get(key)
                        trans[key] = vals if cur is None else [a + b for a, b in zip(cur, vals)]
                pos += n * L
        self.trans = trans


class Mixture:
    """Macroscopic group constants, 1/cm, from atom densities in atoms/(barn cm) (WAD)."""

    def __init__(self, parts, lmax, ng):
        self.tot = [0] * ng
        self.h3_li = [0] * ng
        self.h3_other = [0] * ng
        acc = {}
        for nuc, dens in parts:
            for g in range(ng):
                self.tot[g] += w.mul(dens, nuc.tot[g])
                if nuc.name in ("li6", "li7"):
                    self.h3_li[g] += w.mul(dens, nuc.h3[g])
                else:
                    self.h3_other[g] += w.mul(dens, nuc.h3[g])
            for key, vals in nuc.trans.items():
                cur = acc.get(key)
                add = [w.mul(dens, v) for v in vals]
                acc[key] = add if cur is None else [a + b for a, b in zip(cur, add)]
        self.into = [[] for _ in range(ng)]       # sink -> [(src, [Sigma_l])]
        self.out0 = [0] * ng                      # P0 production out of source group
        self.self_l = [[0] * (lmax + 1) for _ in range(ng)]
        for (src, sink), vals in acc.items():
            self.out0[src] += vals[0]
            if src == sink:
                self.self_l[src] = vals
            else:
                self.into[sink].append((src, vals))


# ---------------------------------------------------------------- linear algebra
def lu_factor(A):
    """In-place LU with partial pivoting on a WAD matrix (list of rows). Returns (LU, piv)."""
    n = len(A)
    piv = list(range(n))
    for k in range(n):
        p = max(range(k, n), key=lambda r: abs(A[r][k]))
        if A[p][k] == 0:
            raise ArithmeticError("singular within-group matrix")
        if p != k:
            A[k], A[p] = A[p], A[k]
            piv[k], piv[p] = piv[p], piv[k]
        akk = A[k][k]
        rowk = A[k]
        for r in range(k + 1, n):
            if A[r][k]:
                f = A[r][k] * W // akk
                A[r][k] = f
                rr = A[r]
                for c in range(k + 1, n):
                    if rowk[c]:
                        rr[c] -= f * rowk[c] // W
    return A, piv


def lu_solve(LU, piv, b):
    n = len(LU)
    y = [b[piv[i]] for i in range(n)]
    for i in range(n):
        row = LU[i]
        s = y[i]
        for c in range(i):
            if row[c]:
                s -= row[c] * y[c] // W
        y[i] = s
    for i in range(n - 1, -1, -1):
        row = LU[i]
        s = y[i]
        for c in range(i + 1, n):
            if row[c]:
                s -= row[c] * y[c] // W
        y[i] = s * W // row[i]
    return y


# ---------------------------------------------------------------- solver
class Slab:
    """zones: list of (thickness_cm WAD, Mixture); left boundary carries the incident source."""

    def __init__(self, zones, lmax=3, n_ang=8, hmax_cm=2 * W):
        self.lmax = lmax
        self.mus, self.wts = gauss_legendre(n_ang)
        self.M = len(self.mus)
        self.cells = []                           # (h_cm, zone index)
        for zi, (t, _) in enumerate(zones):
            nc = max(1, -(-t // hmax_cm))
            for _ in range(nc):
                self.cells.append((t // nc, zi))
            rem = t - (t // nc) * nc               # put flooring remainder in the last cell
            h_last, _z = self.cells[-1]
            self.cells[-1] = (h_last + rem, zi)
        self.N = len(self.cells)
        self.mix = [m for _, m in zones]
        self.thick = [t for t, _ in zones]
        self.P = [[legendre_wad(l, mu) for mu in self.mus] for l in range(lmax + 1)]
        self.ng = len(self.mix[0].tot)

    # one transport sweep for group g with moment source S[l][i] and boundary inflow
    def _sweep(self, g, S, inL, inR, need_out=False):
        N, L = self.N, self.lmax
        mom = [[0] * N for _ in range(L + 1)]
        outL = outR = 0
        for m in range(self.M):
            mu, wt = self.mus[m], self.wts[m]
            amu = abs(mu)
            pl = [self.P[l][m] for l in range(L + 1)]
            fac = [w.mul((2 * l + 1) * W // 2, pl[l]) for l in range(L + 1)]
            order = range(N) if mu > 0 else range(N - 1, -1, -1)
            psi = inL[m] if mu > 0 else inR[m]
            for i in order:
                h, z = self.cells[i]
                st = self.mix[z].tot[g]
                q = 0
                for l in range(L + 1):
                    if S[l][i]:
                        q += w.mul(fac[l], S[l][i])
                key = (z, g, m, h)
                c = self._cache.get(key)
                if c is None:
                    tau = w.div(w.mul(st, h), amu)
                    eps = w.exp(-tau) if tau < 60 * W else 0
                    c = (eps, w.div(W, tau) if tau else 0, w.div(W, st) if st else 0, tau)
                    self._cache[key] = c
                eps, itau, ist, tau = c
                qs = w.mul(q, ist)
                if tau:
                    pout = w.mul(psi, eps) + w.mul(qs, W - eps)
                    pbar = qs + w.mul(psi - pout, itau)
                else:
                    pout = psi + w.div(w.mul(q, h), amu)
                    pbar = (psi + pout) // 2
                for l in range(L + 1):
                    mom[l][i] += w.mul(w.mul(wt, pl[l]), pbar)
                psi = pout
            if mu > 0:
                outR += w.mul(w.mul(wt, amu), psi)
            else:
                outL += w.mul(w.mul(wt, amu), psi)
        return mom, outL, outR

    def _group_setup(self, g):
        """Unit-source responses for implicit P0/P1 and the LU factor of (I - T_ll D_ll)."""
        N, L = self.N, self.lmax
        li = min(1, L)
        nlow = (li + 1) * N
        zero_in = [0] * self.M
        T = []                                    # columns: response (all moments) to unit low source
        for l in range(li + 1):
            for i in range(N):
                S = [[0] * N for _ in range(L + 1)]
                S[l][i] = W
                T.append(self._sweep(g, S, zero_in, zero_in)[0])
        D = [self.mix[self.cells[i][1]].self_l[g][l] for l in range(li + 1) for i in range(N)]
        A = [[0] * nlow for _ in range(nlow)]
        for c in range(nlow):
            col = T[c]
            for l in range(li + 1):
                for i in range(N):
                    r = l * N + i
                    A[r][c] = (W if r == c else 0) - w.mul(col[l][i], D[c])
        LU, piv = lu_factor(A)
        return {"T": T, "D": D, "LU": LU, "piv": piv, "li": li}

    def _solve_group(self, g, ext, inL, inR, setup, tol):
        N, L = self.N, self.lmax
        li = setup["li"]
        high = [[0] * N for _ in range(L + 1)]
        for it in range(500):
            S = [[ext[l][i] + (w.mul(self.mix[self.cells[i][1]].self_l[g][l], high[l][i]) if l > li else 0)
                  for i in range(N)] for l in range(L + 1)]
            R, oL, oR = self._sweep(g, S, inL, inR)
            x = lu_solve(setup["LU"], setup["piv"], [R[l][i] for l in range(li + 1) for i in range(N)])
            Dx = [w.mul(setup["D"][c], x[c]) for c in range(len(x))]
            new_high = [[0] * N for _ in range(L + 1)]
            for l in range(li + 1, L + 1):
                for i in range(N):
                    v = R[l][i]
                    for c in range(len(x)):
                        if Dx[c]:
                            v += w.mul(setup["T"][c][l][i], Dx[c])
                    new_high[l][i] = v
            mom = [[x[l * N + i] for i in range(N)] if l <= li else new_high[l] for l in range(L + 1)]
            if L <= li:
                break
            diff = max(abs(new_high[l][i] - high[l][i]) for l in range(li + 1, L + 1) for i in range(N))
            scale = max(1, max(abs(v) for v in mom[0]))
            high = new_high
            if diff * W // scale <= tol:
                break
        # boundary leakage of the converged solution: one final sweep with full sources
        S = [[ext[l][i] + w.mul(self.mix[self.cells[i][1]].self_l[g][l], mom[l][i]) for i in range(N)]
             for l in range(L + 1)]
        _, oL, oR = self._sweep(g, S, inL, inR)
        return mom, oL, oR, it + 1

    def _solve_group_bc(self, g, ext, inL, inR, setup, tol, psi_unit, white):
        """Within-group solve; with a white left boundary the outgoing left current re-enters
        isotropically. Exact by linear superposition: x = a + alpha * b, alpha = oL_a / (1 - oL_b)."""
        mom, oL, oR, n = self._solve_group(g, ext, inL, inR, setup, tol)
        if not white or oL == 0:
            return mom, oL, oR, n
        zero = [[0] * self.N for _ in range(self.lmax + 1)]
        unit_in = [psi_unit if self.mus[m] > 0 else 0 for m in range(self.M)]
        mb, oLb, oRb, nb = self._solve_group(g, zero, unit_in, inR, setup, tol)
        alpha = w.div(oL, W - oLb)
        mom = [[a + w.mul(alpha, b) for a, b in zip(ra, rb)] for ra, rb in zip(mom, mb)]
        return mom, 0, oR + w.mul(alpha, oRb), n + nb

    def solve(self, src_group, tol=W // 10 ** 9, max_outer=200, left_bc="vacuum"):
        """Unit incident current (isotropic-in-angle inflow) in src_group at the left boundary.
        left_bc 'vacuum': neutrons leaving towards the plasma are lost. 'white': they re-enter
        isotropically in the same group (closed-torus idealisation)."""
        white = left_bc == "white"
        N, L, ng = self.N, self.lmax, self.ng
        self._cache = {}
        jq = sum(w.mul(self.wts[m], self.mus[m]) for m in range(self.M) if self.mus[m] > 0)
        psi_in = w.div(W, jq)                       # quadrature current exactly 1
        inR = [0] * self.M
        phi = [None] * ng
        leakL, leakR = [0] * ng, [0] * ng
        up_first = ng
        for g in range(ng):
            for z in range(len(self.mix)):
                if any(src > g for src, _ in self.mix[z].into[g]):
                    up_first = min(up_first, g)
        setups = {}

        def ext_source(g):
            S = [[0] * N for _ in range(L + 1)]
            for i in range(N):
                z = self.cells[i][1]
                for src, vals in self.mix[z].into[g]:
                    ph = phi[src]
                    if ph is None:
                        continue
                    for l in range(L + 1):
                        if vals[l] and ph[l][i]:
                            S[l][i] += w.mul(vals[l], ph[l][i])
            return S

        inner_its = 0
        for g in range(up_first):
            inL = [psi_in if (g == src_group and self.mus[m] > 0) else 0 for m in range(self.M)]
            ext = ext_source(g)
            if g != src_group and not any(any(r) for r in ext):
                phi[g] = [[0] * N for _ in range(L + 1)]
                continue
            st = self._group_setup(g)
            phi[g], leakL[g], leakR[g], n = self._solve_group_bc(g, ext, inL, inR, st, tol, psi_in, white)
            inner_its += n
        outer = 0
        if up_first < ng:
            for g in range(up_first, ng):
                phi[g] = [[0] * N for _ in range(L + 1)]
                setups[g] = self._group_setup(g)
            for outer in range(1, max_outer + 1):
                change = 0
                scale = 1
                for g in range(up_first, ng):
                    old = phi[g]
                    inL = [psi_in if (g == src_group and self.mus[m] > 0) else 0 for m in range(self.M)]
                    phi[g], leakL[g], leakR[g], n = self._solve_group_bc(g, ext_source(g), inL, inR, setups[g], tol,
                                                                         psi_in, white)
                    inner_its += n
                    change = max(change, max(abs(phi[g][0][i] - old[0][i]) for i in range(N)))
                    scale = max(scale, max(phi[g][0]))
                if change * W // scale <= tol:
                    break
        return self._tally(phi, leakL, leakR, src_group, inner_its, outer)

    def _tally(self, phi, leakL, leakR, src_group, inner_its, outer):
        N, ng = self.N, self.ng
        tbr = other_t = removal = 0
        per_zone_t = [0] * len(self.mix)
        for g in range(ng):
            for i in range(N):
                h, z = self.cells[i]
                f = phi[g][0][i]
                if not f:
                    continue
                mx = self.mix[z]
                rt = w.mul(w.mul(mx.h3_li[g], f), h)
                tbr += rt
                per_zone_t[z] += rt
                other_t += w.mul(w.mul(mx.h3_other[g], f), h)
                removal += w.mul(w.mul(mx.tot[g] - mx.out0[g], f), h)
        jl, jr = sum(leakL), sum(leakR)
        balance = W - jl - jr - removal                # incident current is exactly 1
        return {"tbr_li": tbr, "tritium_other": other_t, "tbr_by_zone": per_zone_t,
                "leak_left": jl, "leak_right": jr, "net_removal": removal,
                "balance_residual": balance, "cells": N, "angles": self.M, "lmax": self.lmax,
                "inner_iterations": inner_its, "outer_iterations": outer, "phi": phi}
