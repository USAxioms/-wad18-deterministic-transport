"""Transport-based TBR for a design vector, per spec/transport_model.json (all WAD-18)."""
import os
from . import wad18 as w, jsonio
from .transport import Nuclide, Mixture, Slab

W = w.WAD
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_NUC = {}


def model_spec():
    return jsonio.load(os.path.join(ROOT, "spec", "transport_model.json"))


def nuclide(fname, lmax):
    key = (fname, lmax)
    if key not in _NUC:
        _NUC[key] = Nuclide(os.path.join(ROOT, "data", "nuclear", fname), lmax)
    return _NUC[key]


def _elements(ms, lmax, e_li6):
    """element -> [(Nuclide, isotopic fraction WAD)], plus element atomic mass (g/mol, WAD)."""
    p = w.parse
    mn = p(ms["constants"]["neutron_mass_u"])
    ab = {k: v for k, v in ms["isotopic_abundance_atom_fraction"].items() if not k.startswith("_")}
    ab["Li"] = {"03Li006.m": w.fmt(e_li6), "03Li007.m": w.fmt(W - e_li6)}
    els = {}
    for el, iso in ab.items():
        tot = sum(p(f) for f in iso.values())
        parts = [(nuclide(fn, lmax), w.div(p(f), tot)) for fn, f in iso.items()]
        mass = sum(w.mul(fr, w.mul(nu.awr, mn)) for nu, fr in parts)
        els[el] = (parts, mass)
    return els


def material_densities(ms, lmax, e_li6):
    """material -> list of (Nuclide, atoms/(barn cm) WAD)."""
    p = w.parse
    na = p(ms["constants"]["avogadro_per_barn_cm"])
    els = _elements(ms, lmax, e_li6)
    mats = {}
    m = ms["materials"]
    # PbLi: atom fractions
    af = {k: p(v) for k, v in m["PbLi"]["atom_fraction"].items()}
    mbar = sum(w.mul(a, els[e][1]) for e, a in af.items())
    ntot = w.div(w.mul(p(m["PbLi"]["density_g_cm3"]), na), mbar)
    mats["PbLi"] = [(nu, w.mul(w.mul(ntot, a), fr)) for e, a in af.items() for nu, fr in els[e][0]]
    # EUROFER: weight fractions
    rho = p(m["EUROFER"]["density_g_cm3"])
    mats["EUROFER"] = [(nu, w.mul(w.div(w.mul(w.mul(rho, p(wf)), na), els[e][1]), fr))
                       for e, wf in m["EUROFER"]["weight_fraction"].items() for nu, fr in els[e][0]]
    # water
    mh2o = 2 * els["H"][1] + els["O"][1]
    n_h2o = w.div(w.mul(p(m["water"]["density_g_cm3"]), na), mh2o)
    mats["water"] = [(els["H"][0][0][0], 2 * n_h2o), (els["O"][0][0][0], n_h2o)]
    mats["Be"] = [(els["Be"][0][0][0], w.div(w.mul(p(m["Be"]["density_g_cm3"]), na), els["Be"][1]))]
    return mats


def _mix(mats, fractions, lmax, ng):
    parts = []
    for mat, f in fractions:
        if f:
            parts += [(nu, w.mul(f, d)) for nu, d in mats[mat]]
    return Mixture(parts, lmax, ng)


def tbr(x, c, out_surrogate, ms=None, numerics=None, left_bc="vacuum"):
    """x: design (WAD), c: surrogate constants, out_surrogate: surrogate outputs for f_steel etc."""
    ms = ms or model_spec()
    nm = dict(ms["numerics"])
    nm.update(numerics or {})
    L, nang = int(nm["legendre_order"]), int(nm["sn_order"])
    hmax = w.parse(nm["max_cell_cm"])
    mats = material_densities(ms, L, x["e_li6"])
    ng = nuclide("01H_001.m", L).ng
    fs, fc = out_surrogate["f_steel"], x["f_cool"]
    zones = []
    cm = 100
    if x["t_mult"] > 0:
        zones.append((x["t_mult"] * cm, _mix(mats, [("Be", W)], L, ng)))
    zones.append((x["t_b"] * cm, _mix(mats, [("EUROFER", fs), ("water", fc), ("PbLi", W - fs - fc)], L, ng)))
    zones.append((c["t_manifold"] * cm, _mix(mats, [("EUROFER", W // 2), ("PbLi", W // 4), ("water", W // 4)], L, ng)))
    t_sh = c["radial_build"] - x["t_mult"] - x["t_b"] - c["t_manifold"]
    if t_sh > 0:
        zones.append((t_sh * cm, _mix(mats, [("EUROFER", 4 * W // 5), ("water", W // 5)], L, ng)))
    bounds = nuclide("01H_001.m", L).bounds
    e_src = w.parse(ms["source"]["energy_eV"])
    src = next(g for g in range(ng) if bounds[g + 1] <= e_src < bounds[g])
    slab = Slab(zones, lmax=L, n_ang=nang, hmax_cm=hmax)
    r = slab.solve(src, tol=w.parse(nm["tolerance"]), left_bc=left_bc)
    r["left_bc"] = left_bc
    r["tbr"] = w.mul(r["tbr_li"], c["coverage"])
    r["source_group"] = src + 1
    r["zones"] = [z for z in ("multiplier", "breeding", "manifold", "shield")
                  if not (z == "multiplier" and x["t_mult"] == 0) and not (z == "shield" and t_sh <= 0)]
    return r


def tbr_cylinder(x, c, out_surrogate, ms=None, numerics=None, geometry=None):
    """TBR in the 1-D cylindrical model (spec/transport_model.json -> cylinder)."""
    from .cylinder import Cylinder
    ms = ms or model_spec()
    cy = ms["cylinder"]
    nm = dict(cy["numerics"])
    nm.update(numerics or {})
    geo = {"plasma_radius_m": cy["plasma_radius_m"], "first_wall_radius_m": cy["first_wall_radius_m"]}
    geo.update(geometry or {})
    L = int(nm["legendre_order"])
    hmax = w.parse(nm["max_cell_cm"])
    mats = material_densities(ms, L, x["e_li6"])
    ng = nuclide("01H_001.m", L).ng
    fs, fc = out_surrogate["f_steel"], x["f_cool"]
    cm = 100
    rp, rfw = w.parse(geo["plasma_radius_m"]) * cm, w.parse(geo["first_wall_radius_m"]) * cm
    layers = []
    if x["t_mult"] > 0:
        layers.append(("multiplier", x["t_mult"] * cm, _mix(mats, [("Be", W)], L, ng)))
    layers.append(("breeding", x["t_b"] * cm, _mix(mats, [("EUROFER", fs), ("water", fc), ("PbLi", W - fs - fc)], L, ng)))
    layers.append(("manifold", c["t_manifold"] * cm,
                   _mix(mats, [("EUROFER", W // 2), ("PbLi", W // 4), ("water", W // 4)], L, ng)))
    t_sh = c["radial_build"] - x["t_mult"] - x["t_b"] - c["t_manifold"]
    if t_sh > 0:
        layers.append(("shield", t_sh * cm, _mix(mats, [("EUROFER", 4 * W // 5), ("water", W // 5)], L, ng)))
    zones = [(rp, None, int(nm["plasma_cells"]), True), (rfw, None, int(nm["gap_cells"]), False)]
    r = rfw
    for _, t, mx in layers:
        r += t
        zones.append((r, mx, max(1, -(-t // hmax)), False))
    bounds = nuclide("01H_001.m", L).bounds
    e_src = w.parse(ms["source"]["energy_eV"])
    src = next(g for g in range(ng) if bounds[g + 1] <= e_src < bounds[g])
    cyl = Cylinder(zones, n_levels=int(nm["gl_order"]), k_az=int(nm["azimuths"]))
    res = cyl.solve(src, tol=w.parse(nm["tolerance"]))
    res["tbr"] = w.mul(res["tbr_li"], c["coverage"])
    res["zones"] = ["plasma", "gap"] + [n for n, _, _ in layers]
    res["source_group"] = src + 1
    return res
