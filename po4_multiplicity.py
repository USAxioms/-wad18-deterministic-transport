"""Exact (integer) multiplicity analysis of the PO4 confirmatory cycles.

Null model: R3 and NSGA-II are exchangeable, so each cell is won with probability 1/2,
independently. Under that null, P(a cycle scores >= k of 8) = sum_{j>=k} C(8,j) / 2^8, and
the chance that at least one of c cycles does so is 1 - (1 - p)^c. Cells within a cycle share
instances, so independence is an idealisation; seed-level counts are reported as a secondary
descriptive statistic (seeds within a cell are not independent either).
python3 po4_multiplicity.py
"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import jsonio, wad18 as w  # noqa: E402

CYCLES = [("cycle 1", "v1.2.0_heldout"), ("cycle 2", "v1.3.0_heldout"), ("cycle 3", "v1.4.0_heldout")]


def comb(n, k):
    """Binomial coefficient by exact integer multiplication (no math module)."""
    r = 1
    for i in range(k):
        r = r * (n - i) // (i + 1)
    return r


def ipow(b, e):
    """Non-negative integer power by repeated multiplication."""
    r = 1
    for _ in range(e):
        r *= b
    return r


def frac(num, den):
    return {"numerator": num, "denominator": den, "wad": w.fmt(num * w.WAD // den)}


def tail(n, k):
    return sum(comb(n, j) for j in range(k, n + 1)), ipow(2, n)


def main():
    rows = []
    for name, rd in CYCLES:
        s = jsonio.load(os.path.join(ROOT, "results", rd, "heldout_summary.json"))
        seeds_won = sum(c["r3_seeds_beating_nsga2_median"] for c in s["cells"])
        rows.append({"cycle": name, "status": s["PO4_status"], "cells_won": s["cells_r3_median_beats_nsga2_median"],
                     "cells": s["cells_total"], "r3_seeds_beating_nsga2_median": seeds_won,
                     "seeds": 7 * s["cells_total"]})
    c = len(rows)
    num6, den = tail(8, 6)
    num7, _ = tail(8, 7)
    final = rows[-1]
    sn, sd = tail(final["seeds"], final["r3_seeds_beating_nsga2_median"])
    out = {
        "cycles": rows,
        "null_model": "each cell a fair coin, cells independent",
        "p_single_cycle_pass_ge6": frac(num6, den),
        "p_any_of_cycles_pass_ge6": frac(ipow(den, c) - ipow(den - num6, c), ipow(den, c)),
        "p_single_cycle_ge_observed": frac(*tail(8, final["cells_won"])),
        "p_any_of_cycles_ge_observed": frac(ipow(den, c) - ipow(den - tail(8, final["cells_won"])[0], c), ipow(den, c)),
        "p_seed_level_final_cycle_ge_observed": frac(sn, sd),
        "reading": ("A single confirmatory pass after " + str(c) + " cycles is weaker evidence than one first-attempt "
                    "pass. Under the idealised null, the chance that at least one of " + str(c) +
                    " cycles reaches the observed cell count is p_any_of_cycles_ge_observed."),
    }
    _ = num7
    jsonio.dump(out, os.path.join(ROOT, "results", "PO4_multiplicity.json"))
    print("cycles " + str([r["cells_won"] for r in rows]) + "  P(any cycle >= observed) = " +
          out["p_any_of_cycles_ge_observed"]["wad"][:6] + "  seed-level P = " +
          out["p_seed_level_final_cycle_ge_observed"]["wad"][:8])


if __name__ == "__main__":
    main()
