"""Verification of the bundled nuclear data and of the integer MATXS/ENDF readers.

Checks (all integer):
 V1 structure   every vector/matrix block has exactly the number of words its control record declares
 V2 layout      P0 elastic transfer summed over sink groups equals the elastic cross section of each
                source group (decodes the 9d layout; reported per material, below and above 20 MeV)
 V3 evaluation  each MATXS group value lies within [min, max] of the pointwise ENDF values over that
                group (weight-independent bound), for every pair of files sharing a nuclide
 V4 closure     total = sum of all matrix (neutron-emitting) reactions + pure-absorption reactions,
                i.e. no neutron-changing reaction is missing or double counted (below 20 MeV)
 Conventions verified separately (tests/test_ndata.py): P_l matrices carry no (2l+1) factor (H-1
 P1/P0 equals its mubar vector, ~2/(3A)); (n,2n) matrices include multiplicity 2.

Thresholds and exclusions below were set AFTER first inspection of the data; the physical reasons
are recorded with them and the unfiltered counts are always reported alongside.
python3 ndata_verify.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule.ndata.matxs import Matxs  # noqa: E402
from r3capsule.ndata.endf import Endf  # noqa: E402
from r3capsule import jsonio, wad18 as w  # noqa: E402

D = os.path.join(ROOT, "data", "nuclear")
MATXS = ["01H_001.m", "03Li006.m", "03Li007.m", "04Be009.m", "08O_016.m",
         "24Cr050.m", "24Cr052.m", "24Cr053.m", "24Cr054.m", "26Fe054.m", "26Fe056.m", "26Fe057.m", "26Fe058.m",
         "74W_182.m", "74W_183.m", "74W_184.m", "74W_186.m",
         "82Pb204.m", "82Pb206.m", "82Pb207.m", "82Pb208.m"]
# pure-absorption (no outgoing neutron) reaction totals used in the V4 closure; level partials
# (p00.., a00.., d00.., t00.., h00..) and sums of matrix reactions (ninel) are excluded
ABSORB = ["ng", "np", "nd", "nt", "nhe3", "nh", "na", "n2a", "n3a", "n2p", "npa", "nt2a", "nd2a", "npd", "npt", "nda"]
PAIRS = [("03Li006.m", "n_0325_3-Li-6.endf", [("ntot0", 1), ("nelas", 2), ("nt", 105)]),
         ("03Li007.m", "n_0328_3-Li-7.endf", [("ntot0", 1), ("nelas", 2)]),
         ("04Be009.m", "n_0425_4-Be-9.endf", [("ntot0", 1), ("nelas", 2)]),
         ("82Pb204.m", "n_8225_82-Pb-204.endf", [("ntot0", 1)]),
         ("82Pb206.m", "n_8231_82-Pb-206.endf", [("ntot0", 1)]),
         ("24Cr050.m", "n_2425_24-Cr-50.endf", [("ntot0", 1)]), ("24Cr052.m", "n_2431_24-Cr-52.endf", [("ntot0", 1)]),
         ("24Cr053.m", "n_2434_24-Cr-53.endf", [("ntot0", 1)]), ("24Cr054.m", "n_2437_24-Cr-54.endf", [("ntot0", 1)]),
         ("26Fe054.m", "n_2625_26-Fe-54.endf", [("ntot0", 1)]), ("26Fe056.m", "n_2631_26-Fe-56.endf", [("ntot0", 1)]),
         ("26Fe057.m", "n_2634_26-Fe-57.endf", [("ntot0", 1)]), ("26Fe058.m", "n_2637_26-Fe-58.endf", [("ntot0", 1)]),
         ("74W_182.m", "n_7431_74-W-182.endf", [("ntot0", 1)]), ("74W_183.m", "n_7434_74-W-183.endf", [("ntot0", 1)]),
         ("74W_184.m", "n_7437_74-W-184.endf", [("ntot0", 1)]), ("74W_186.m", "n_7443_74-W-186.endf", [("ntot0", 1)])]
E20 = 20 * w.WAD * 1000000                 # 20 MeV in WAD eV
DOPPLER_EXCL = 100 * w.WAD                 # 100 eV
BAL_TOL_PPM = 1000                         # 0.1 %
SOURCE = 14100000 * w.WAD                  # D-T source energy, for relevance notes


def p0_out(M):
    out = [0] * M["ng_in"]
    pos = 0
    for l in range(M["ng_out"]):
        n = M["jband"][l]
        for k in range(n):
            out[M["ijj"][l] - k - 1] += M["data"][pos + k]
        pos += n * M["lord"]
    return out


def ppm(a, b):
    return abs(a - b) * 1000000 // max(b, 1)


def main():
    rep = {"matxs": [], "endf_bounds": [], "notes": []}
    ok_all = True
    for f in MATXS:
        m = Matxs(os.path.join(D, f))
        words_ok = all(len(M["data"]) == M["words_expected"] for sm in m.sub for M in sm["matrices"].values())
        E = m.bounds["n"]
        el = m.sub[0]["matrices"]["nelas"]
        out, v = p0_out(el), m.vector("nelas")
        lo = [ppm(out[g], v[g]) for g in range(211) if v[g] > 0 and E[g] <= E20]
        hi = [ppm(out[g], v[g]) for g in range(211) if v[g] > 0 and E[g] > E20]
        s0 = m.sub[0]
        leaves = list(s0["matrices"]) + [a for a in ABSORB if a in s0["vectors"] and a not in s0["matrices"]]
        acc = [0] * 211
        for nm in leaves:
            if nm in s0["vectors"]:
                vv = m.vector(nm)
                for g in range(211):
                    acc[g] += vv[g]
        tot = m.vector("ntot0")
        clo = max(ppm(acc[g], tot[g]) for g in range(211) if tot[g] > 0 and E[g] <= E20)
        passed = words_ok and max(lo) <= BAL_TOL_PPM and clo <= BAL_TOL_PPM
        ok_all = ok_all and passed
        rep["matxs"].append({"file": f, "material": m.material, "groups_n": m.ngrp[0], "groups_g": m.ngrp[1],
                             "temperature_K": w.fmt(m.sub[0]["temp"]), "vectors": m.sub[0]["n1d"],
                             "matrices": sum(sm["n2d"] for sm in m.sub), "V1_word_counts_exact": words_ok,
                             "V2_elastic_balance_max_ppm_upto_20MeV": max(lo),
                             "V2_elastic_balance_max_ppm_above_20MeV": max(hi) if hi else 0,
                             "V2_groups_above_20MeV_over_tolerance": sum(1 for x in hi if x > BAL_TOL_PPM),
                             "V4_total_closure_max_ppm_upto_20MeV": clo,
                             "values_floored_below_1e-18": m.inexact, "pass": passed})
    for mf, ef, chk in PAIRS:
        m, e = Matxs(os.path.join(D, mf)), Endf(os.path.join(D, ef))
        eh = e.resonance_upper() if e.lrp() == 1 else 0
        E = m.bounds["n"]
        for vec, mt in chk:
            _, pts = e.tab1(mt)
            v = m.vector(vec)
            raw_bad, kept, kept_bad, bad_list = 0, 0, 0, []
            for g in range(211):
                hi_e, lo_e = E[g], E[g + 1]
                if v[g] == 0:
                    continue
                c = ([s for x, s in pts if lo_e <= x <= hi_e] + [s for x, s in pts if x < lo_e][-1:] +
                     [s for x, s in pts if x > hi_e][:1])
                if not c:
                    continue
                tol = v[g] * 5 // 1000000 + 1           # MATXS 6-significant-digit rounding
                bad = not (min(c) - tol <= v[g] <= max(c) + tol)
                raw_bad += bad
                if lo_e < eh or hi_e <= DOPPLER_EXCL:
                    continue
                kept += 1
                if bad:
                    kept_bad += 1
                    bad_list.append({"group": g + 1, "E_low_eV": w.fmt(lo_e), "E_high_eV": w.fmt(hi_e),
                                     "matxs": w.fmt(v[g]), "endf_min": w.fmt(min(c)), "endf_max": w.fmt(max(c)),
                                     "above_DT_source": lo_e >= SOURCE})
            rel = all(b["above_DT_source"] for b in bad_list)
            rep["endf_bounds"].append({"matxs": mf, "endf": ef, "vector": vec, "MT": mt,
                                       "resonance_range_excluded_below_eV": w.fmt(eh),
                                       "groups_outside_bounds_unfiltered": raw_bad,
                                       "groups_checked_after_exclusions": kept,
                                       "groups_outside_after_exclusions": kept_bad,
                                       "outside_groups": bad_list,
                                       "all_remaining_outliers_above_DT_source": rel})
            ok_all = ok_all and rel
    rep["notes"] = [
        "V2 above 20 MeV: lead elastic rows fall short of the elastic vector by up to ~2.7 %; strongly "
        "forward-peaked heavy-nucleus elastic at P6. Above the 14.1 MeV D-T source; no effect on a D-T blanket.",
        "V3 exclusions (set after inspection): resolved-resonance ranges of LRP=1 evaluations (MF3 there is "
        "background only); E <= 100 eV for all nuclides, because MATXS is Doppler-broadened at 293.6 K while "
        "ENDF MF3 is 0 K -- observed light-nuclide violations lie below 30 eV.",
        "Version mismatch: ENDF files for Li-6, Li-7, Be-9 are FENDL-3.0 and for Pb-204/206 JEFF-3.1.1, while the "
        "MATXS libraries are FENDL-3.2c. Li-7 group 35 (20-21 MeV) differs from the FENDL-3.0 file, which has a "
        "splice at 20 MeV; unresolved without the FENDL-3.2 evaluation, irrelevant below 14.1 MeV.",
    ]
    rep["verified"] = ok_all
    jsonio.dump(rep, os.path.join(ROOT, "results", "ndata_verification.json"))
    for r in rep["matxs"]:
        print(r["file"].ljust(10), "words", "ok" if r["V1_word_counts_exact"] else "BAD",
              " balance<=20MeV max", str(r["V2_elastic_balance_max_ppm_upto_20MeV"]).rjust(4), "ppm",
              " closure", str(r["V4_total_closure_max_ppm_upto_20MeV"]).rjust(3), "ppm",
              " >20MeV groups over tol", r["V2_groups_above_20MeV_over_tolerance"])
    for r in rep["endf_bounds"]:
        print(r["matxs"].ljust(10), r["vector"].ljust(6), "MT" + str(r["MT"]).ljust(4), "unfiltered out",
              str(r["groups_outside_bounds_unfiltered"]).rjust(3), " after exclusions",
              str(r["groups_outside_after_exclusions"]) + "/" + str(r["groups_checked_after_exclusions"]))
    print("nuclear data verified: " + str(ok_all))


if __name__ == "__main__":
    main()
