"""Integer-exact 1-D cylindrical (r) multigroup discrete-ordinates transport (WAD-18).

Infinite cylinder, per unit length; areas A = r and volumes V = (r_out^2 - r_in^2)/2 (the common
factor 2*pi is dropped consistently). Conservative form for direction (mu, eta, xi), mu radial:
    mu (A+ psi+ - A- psi-) + (alpha_{m+1/2} psi_{m+1/2} - alpha_{m-1/2} psi_{m-1/2}) (A+ - A-)/w_m
        + St V psi_i = V q_i
with alpha_{1/2} = 0, alpha_{m+1/2} = alpha_{m-1/2} - w_m mu_m on each xi level (directions ordered
by increasing mu), so a spatially flat isotropic flux satisfies the discrete equation exactly.
Step differencing in space AND angle (outflow face and next-angle edge take the cell value):
first order, but positive and exactly conservative.

Quadrature: Gauss-Legendre levels in xi > 0 (symmetric in xi) times K Chebyshev azimuths on
(0, pi) (symmetric in eta); weights normalised to sum 1, so phi = sum w psi is the scalar flux
and J = sum w mu psi the radial current. Scattering to P1: q = S0 + 3 mu S1 with
S0 = sum Sigma_0 phi, S1 = sum Sigma_1 J (MATXS P_l carry no (2l+1); verified).
Within each group the P0 scattering source is solved implicitly (dense LU over material cells)
and the P1 source is iterated to convergence. The data must have no upscatter (asserted).
"""
from . import wad18 as w
from .transport import gauss_legendre, lu_factor, lu_solve

W = w.WAD
G = W * W
PI36 = 3141592653589793238462643383279502884      # pi at scale 10^36


def _cos36(x):
    """cos(x), x and result at scale 10^36, |x| <= pi, by Taylor series (exact integers)."""
    term, s, k = G, G, 0
    x2 = x * x // G
    while True:
        k += 2
        term = -term * x2 // G // (k * (k - 1))
        if term == 0:
            return s
        s += term


def quadrature(n_levels_gl, k_az):
    """Returns per level: (mu list ascending, weight list), with symmetric mu so sum w mu = 0 exactly."""
    xs, gw = gauss_legendre(n_levels_gl)
    half = n_levels_gl // 2
    levels = []
    for n in range(half):
        xi, g = xs[n], gw[n]                     # positive node, weight; sum over positive half = 1
        s = w.sqrt(W - w.mul(xi, xi))
        mus = []
        for k in range(1, k_az // 2 + 1):        # omega_k = pi (k - 1/2) / K, k <= K/2: cos > 0
            c = _cos36(PI36 * (2 * k - 1) // (2 * k_az)) // W
            mus.append(w.mul(s, c))
        pos = sorted(mus)
        mu_lv = [-m for m in reversed(pos)] + pos      # ascending, exactly antisymmetric
        wt = g // k_az
        levels.append((mu_lv, [wt] * k_az))
    return levels


class Cylinder:
    """zones: list of (outer radius cm WAD, Mixture or None for void, n_cells, source flag)."""

    def __init__(self, zones, n_levels=8, k_az=8):
        self.levels = quadrature(n_levels, k_az)
        self.r = [0]
        self.zone_of = []
        self.mix = []
        self.src_cell = []
        r0 = 0
        for zi, (rout, mix, nc, src) in enumerate(zones):
            self.mix.append(mix)
            for j in range(1, nc + 1):
                self.r.append(r0 + (rout - r0) * j // nc)
                self.zone_of.append(zi)
                self.src_cell.append(src)
            self.r[-1] = rout
            r0 = rout
        self.N = len(self.zone_of)
        self.A = self.r                                  # A_{i+1/2} = r_{i+1/2}
        self.V = [(self.r[i + 1] * self.r[i + 1] - self.r[i] * self.r[i]) // (2 * W) for i in range(self.N)]
        ref = next(m for m in self.mix if m is not None)
        self.ng = len(ref.tot)
        self._geo = None

    def _tot(self, i, g):
        m = self.mix[self.zone_of[i]]
        return m.tot[g] if m is not None else 0

    def _self(self, i, g):
        m = self.mix[self.zone_of[i]]
        return m.self_l[g][:2] if m is not None else [0, 0]

    def _geometry(self):
        """Group-independent coefficients per (level, direction, cell)."""
        N, A, V = self.N, self.A, self.V
        geo = []
        for mus, wts in self.levels:
            alpha_lo = 0
            lv = []
            for mu, wt in zip(mus, wts):
                alpha_hi = alpha_lo - w.mul(wt, mu)
                amu = abs(mu)
                cin, base, alo = [0] * N, [0] * N, [0] * N
                for i in range(N):
                    rd = w.div(A[i + 1] - A[i], wt)
                    if mu < 0:
                        cin[i] = w.mul(amu, A[i + 1])
                        base[i] = w.mul(amu, A[i]) + w.mul(alpha_hi, rd)
                    else:
                        cin[i] = w.mul(mu, A[i])
                        base[i] = w.mul(mu, A[i + 1]) + w.mul(alpha_hi, rd)
                    alo[i] = w.mul(alpha_lo, rd)
                lv.append((mu, wt, 3 * mu, w.mul(wt, mu), cin, base, alo))
                alpha_lo = alpha_hi
            geo.append(lv)
        return geo

    def sweep(self, g, S0, S1, outer_in=None):
        """One transport sweep; returns (phi, J, leakage through the outer surface, outgoing psi).
        outer_in: optional dict (level, mu index) -> incoming psi at the outer boundary."""
        N, V = self.N, self.V
        if self._geo is None:
            self._geo = self._geometry()
        stv = [w.mul(self._tot(i, g), V[i]) for i in range(N)]
        anyS1 = any(S1)
        phi, J = [0] * N, [0] * N
        leak = 0
        out_psi = {}
        down, up = range(N - 1, -1, -1), range(N)
        AN = self.A[N]
        for lv, dirs in enumerate(self._geo):
            prev = [0] * N
            for m, (mu, wt, mu3, wmu, cin, base, alo) in enumerate(dirs):
                cur = [0] * N
                if mu < 0:
                    psi_face = outer_in.get((lv, m), 0) if outer_in else 0
                    rng = down
                else:
                    psi_face = 0
                    rng = up
                for i in rng:
                    q = S0[i] + (mu3 * S1[i] // W if anyS1 else 0)
                    num = V[i] * q // W + cin[i] * psi_face // W + alo[i] * prev[i] // W
                    den = base[i] + stv[i]
                    psi = num * W // den if den else 0
                    cur[i] = psi
                    psi_face = psi
                    phi[i] += wt * psi // W
                    J[i] += wmu * psi // W
                if mu > 0:
                    leak += wmu * AN // W * psi_face // W
                    out_psi[(lv, m)] = psi_face
                prev = cur
        return phi, J, leak, out_psi

    def _setup(self, g):
        """P0 implicit: responses (phi and J) to unit P0 sources in material cells; LU of I - T00 D0."""
        N = self.N
        mat = [i for i in range(N) if self.mix[self.zone_of[i]] is not None]
        cols = []
        for i in mat:
            S0, S1 = [0] * N, [0] * N
            S0[i] = W
            p, j, _, _ = self.sweep(g, S0, S1)
            cols.append((p, j))
        D0 = [self._self(i, g)[0] for i in mat]
        n = len(mat)
        Amat = [[(W if r == c else 0) - w.mul(cols[c][0][mat[r]], D0[c]) for c in range(n)] for r in range(n)]
        LU, piv = lu_factor(Amat)
        return LU, piv, D0, mat, cols

    def solve(self, src_group, src_density=W, tol=W // 10 ** 13):
        """Uniform isotropic volumetric source in src_group in cells flagged as source.
        P0 within-group scattering solved implicitly, P1 iterated. Normalised per source neutron."""
        N, ng = self.N, self.ng
        for m in self.mix:
            if m is not None:
                for g in range(ng):
                    assert all(src < g for src, _ in m.into[g]), "upscatter present: not supported"
        phi = [None] * ng
        cur = [None] * ng
        leaks = [0] * ng
        its = 0
        for g in range(ng):
            S0, S1 = [0] * N, [0] * N
            for i in range(N):
                m = self.mix[self.zone_of[i]]
                if g == src_group and self.src_cell[i]:
                    S0[i] += src_density
                if m is None:
                    continue
                for src, vals in m.into[g]:
                    if phi[src] is not None:
                        S0[i] += w.mul(vals[0], phi[src][i])
                        S1[i] += w.mul(vals[1], cur[src][i])
            if not any(S0) and not any(S1):
                phi[g], cur[g] = [0] * N, [0] * N
                continue
            LU, piv, D0, mat, cols = self._setup(g)
            D1 = [self._self(i, g)[1] for i in range(N)]
            Jl = [0] * N
            for it in range(1000):
                S1x = [S1[i] + w.mul(D1[i], Jl[i]) for i in range(N)]
                p, j, _, _ = self.sweep(g, S0, S1x)
                x = lu_solve(LU, piv, [p[i] for i in mat])
                ph = list(p)
                Jn = list(j)
                for c, i in enumerate(mat):
                    ph[i] = x[c]
                Dx = [w.mul(D0[c], x[c]) for c in range(len(mat))]
                for c in range(len(mat)):
                    if Dx[c]:
                        pc, jc = cols[c]
                        for r in range(N):
                            if r not in mat:
                                ph[r] += w.mul(pc[r], Dx[c])
                            Jn[r] += w.mul(jc[r], Dx[c])
                diff = max(abs(Jn[i] - Jl[i]) for i in range(N))
                scale = max(1, max(ph))
                Jl = Jn
                if not any(D1) or diff * W // scale <= tol:
                    break
            its += it + 1
            phi[g], cur[g] = ph, Jl
            S0f = [S0[i] + (w.mul(self._self(i, g)[0], ph[i])) for i in range(N)]
            S1f = [S1[i] + w.mul(D1[i], Jl[i]) for i in range(N)]
            _, _, leaks[g], _ = self.sweep(g, S0f, S1f)
        r = self._tally(phi, leaks, src_group, src_density)
        r["p1_iterations"] = its
        return r

    def _tally(self, phi, leaks, src_group, src_density):
        N, ng = self.N, self.ng
        source = sum(self.V[i] for i in range(N) if self.src_cell[i])
        source = w.mul(source, src_density)
        tbr = other = removal = 0
        by_zone = [0] * len(self.mix)
        for g in range(ng):
            for i in range(N):
                m = self.mix[self.zone_of[i]]
                if m is None or not phi[g][i]:
                    continue
                v = w.mul(self.V[i], phi[g][i])
                t = w.mul(m.h3_li[g], v)
                tbr += t
                by_zone[self.zone_of[i]] += t
                other += w.mul(m.h3_other[g], v)
                removal += w.mul(m.tot[g] - m.out0[g], v)
        leak = sum(leaks)
        return {"source": source, "tbr_li": w.div(tbr, source), "tritium_other": w.div(other, source),
                "tbr_by_zone": [w.div(x, source) for x in by_zone], "leak_outer": w.div(leak, source),
                "net_removal": w.div(removal, source),
                "balance_residual": w.div(source - leak - removal, source), "cells": N,
                "directions": sum(len(lv[0]) for lv in self.levels), "phi": phi}
