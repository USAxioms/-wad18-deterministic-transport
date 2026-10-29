# Study report: spec 29b701f225f0

Generated from `results/` by `make_report.py`. All numbers are exact WAD-18 decimal renderings.

## Proof obligations

| Obligation | Status |
|---|---|
| PO1_reproducible_execution | PASS |
| PO2_constraint_satisfaction | FAIL |
| PO3_engineering_improvement | FAIL |
| PO4_contribution_of_R3 | FAIL |
| PO5_robustness | FAIL |
| PO6_physical_relevance | NOT_ESTABLISHED |

## Search comparison (equal budget: 1000 unique evaluations)

| Method | Hypervolume (min / median / max) |
|---|---|
| R3 (deterministic, 1 run, stopped: FIXED_POINT after 874 evals) | 0.264212248006163532 |
| NSGA-II (5 seeds) | 0.249450769789242098 / 0.266526526117472924 / 0.270991614679426319 |
| Random (5 seeds) | 0.147793768145882294 / 0.198204959596962005 / 0.209311809606698041 |

R3 ranks 4 of 11 runs: 3 of 5 NSGA-II runs and 0 of 5 random runs exceed it. PO4 status under the predeclared rule: FAIL.

## Front versus reference

Reference: TBR 1.160212, dp 20797.644 Pa.

16 of 20 R3 front designs dominate the reference at nominal theta, but none meets the predeclared selection rule (every normalised constraint slack >= 0.05). Each sits on or near at least one constraint, so PO2, PO3 and PO5 are FAIL with reason NO_CANDIDATE. See `13_front_diagnostics.json`.

## Physical relevance

Reduced-order surrogate correlations with declared, unvalidated constants. No Monte Carlo transport (e.g. OpenMC), CFD, benchmark, or experimental comparison was performed. No claim about a physical blanket follows from this capsule.

## Integrity

- Tests: 49 passed, 0 failed.
- Reproduction: 12/12 pipeline files byte-identical on re-execution.
- Output-level checks all OK: true.
- Zero-floating-point audit: `results/zero_float_audit.json` (run last, all studies).
