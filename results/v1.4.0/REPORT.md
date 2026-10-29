# Study report: spec 67c94308ffae

Generated from `results/` by `make_report.py`. All numbers are exact WAD-18 decimal renderings.

## Proof obligations

| Obligation | Status |
|---|---|
| PO1_reproducible_execution | PASS |
| PO2_constraint_satisfaction | PASS |
| PO3_engineering_improvement | PASS |
| PO4_contribution_of_R3 | PASS |
| PO5_robustness | PASS |
| PO6_physical_relevance | NOT_ESTABLISHED |

## Search comparison (equal budget: 1000 unique evaluations)

| Method | Hypervolume (min / median / max) |
|---|---|
| R3 (deterministic, 1 run, stopped: BUDGET after 1000 evals) | 0.208529645607884278 |
| NSGA-II (5 seeds) | 0.195982004936059637 / 0.208245845255379326 / 0.214107675253899371 |
| Random (5 seeds) | 0.110737981520642929 / 0.129937064295187681 / 0.137945395899606731 |

R3 ranks 3 of 11 runs: 2 of 5 NSGA-II runs and 0 of 5 random runs exceed it. PO4 status under the predeclared rule: PASS.

## Held-out PO4 test (decides PO4)

| Instance | Budget | R3 median | NSGA-II median | Random median | R3 > NSGA-II |
|---|---|---|---|---|---|
| H9_high_enrichment_cost | 1200 | 0.205926 | 0.203895 | 0.123372 | yes |
| H9_high_enrichment_cost | 2500 | 0.206865 | 0.206865 | 0.144463 | no |
| H10_thin_manifold | 1200 | 0.235292 | 0.226816 | 0.165311 | yes |
| H10_thin_manifold | 2500 | 0.237976 | 0.234989 | 0.173009 | yes |
| H11_weak_heat_transfer | 1200 | 0.208930 | 0.206158 | 0.134187 | yes |
| H11_weak_heat_transfer | 2500 | 0.213190 | 0.209216 | 0.153260 | yes |
| H12_short_attenuation | 1200 | 0.236660 | 0.224477 | 0.156783 | yes |
| H12_short_attenuation | 2500 | 0.238276 | 0.229137 | 0.175654 | yes |

R3 median beats NSGA-II median in 7 of 8 cells; rule requires 6. PO4: PASS.

## Front versus reference

Reference: TBR 1.160212, dp 20797.644 Pa.

8 of 15 R3 front designs dominate the reference at nominal theta. The selection rule picked:

| Quantity | Reference | Selected |
|---|---|---|
| tbr | 1.1602120821 | 1.2947214353 |
| dp | 20797.644947 | 18193.098369 |
| T_wall | 412.86927776 | 422.58162507 |
| T_peak | 497.06467382 | 521.43669100 |
| velocity | 0.6982919528 | 0.6775826121 |
| atten_exponent | 5.8888888888 | 5.8677777777 |

Selected design: d_h = 0.011, e_li6 = 0.9, f_cool = 0.03, f_struct = 0.105, t_b = 0.46, t_mult = 0.05.

## Physical relevance

Reduced-order surrogate correlations with declared, unvalidated constants. No Monte Carlo transport (e.g. OpenMC), CFD, benchmark, or experimental comparison was performed. No claim about a physical blanket follows from this capsule.

## Integrity

- Tests: 49 passed, 0 failed.
- Reproduction: 14/14 pipeline files byte-identical on re-execution.
- Output-level checks all OK: true.
- Zero-floating-point audit: `results/zero_float_audit.json` (run last, all studies).
