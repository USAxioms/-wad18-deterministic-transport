# Study report: spec 0d89796a2d4f

Generated from `results/` by `make_report.py`. All numbers are exact WAD-18 decimal renderings.

## Proof obligations

| Obligation | Status |
|---|---|
| PO1_reproducible_execution | PASS |
| PO2_constraint_satisfaction | PASS |
| PO3_engineering_improvement | PASS |
| PO4_contribution_of_R3 | FAIL |
| PO5_robustness | PASS |
| PO6_physical_relevance | NOT_ESTABLISHED |

## Search comparison (equal budget: 1000 unique evaluations)

| Method | Hypervolume (min / median / max) |
|---|---|
| R3 (deterministic, 1 run, stopped: BUDGET after 1000 evals) | 0.201450854654089172 |
| NSGA-II (5 seeds) | 0.195982004936059637 / 0.208245845255379326 / 0.214107675253899371 |
| Random (5 seeds) | 0.110737981520642929 / 0.129937064295187681 / 0.137945395899606731 |

R3 ranks 5 of 11 runs: 4 of 5 NSGA-II runs and 0 of 5 random runs exceed it. PO4 status under the predeclared rule: FAIL.

## Front versus reference

Reference: TBR 1.160212, dp 20797.644 Pa.

13 of 15 R3 front designs dominate the reference at nominal theta. The selection rule picked:

| Quantity | Reference | Selected |
|---|---|---|
| tbr | 1.1602120821 | 1.3023583421 |
| dp | 20797.644947 | 17559.556365 |
| T_wall | 412.86927776 | 422.21758238 |
| T_peak | 497.06467382 | 519.18478169 |
| velocity | 0.6982919528 | 0.6646426016 |
| atten_exponent | 5.8888888888 | 5.7966666666 |

Selected design: d_h = 0.011, e_li6 = 0.9, f_cool = 0.03, f_struct = 0.105, t_b = 0.47, t_mult = 0.05.

## Physical relevance

Reduced-order surrogate correlations with declared, unvalidated constants. No Monte Carlo transport (e.g. OpenMC), CFD, benchmark, or experimental comparison was performed. No claim about a physical blanket follows from this capsule.

## Integrity

- Tests: 49 passed, 0 failed.
- Reproduction: 14/14 pipeline files byte-identical on re-execution.
- Output-level checks all OK: true.
- Zero-floating-point audit: `results/zero_float_audit.json` (run last, all studies).
