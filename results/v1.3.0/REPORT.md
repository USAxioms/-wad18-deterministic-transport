# Study report: spec 04925a7c6fe3

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
| R3 (deterministic, 1 run, stopped: BUDGET after 1000 evals) | 0.208529645607884278 |
| NSGA-II (5 seeds) | 0.195982004936059637 / 0.208245845255379326 / 0.214107675253899371 |
| Random (5 seeds) | 0.110737981520642929 / 0.129937064295187681 / 0.137945395899606731 |

R3 ranks 3 of 11 runs: 2 of 5 NSGA-II runs and 0 of 5 random runs exceed it. PO4 status under the predeclared rule: FAIL.

## Held-out PO4 test (decides PO4)

| Instance | Budget | R3 median | NSGA-II median | Random median | R3 > NSGA-II |
|---|---|---|---|---|---|
| H5_low_blanket_coverage | 1500 | 0.148736 | 0.148711 | 0.095496 | yes |
| H5_low_blanket_coverage | 3000 | 0.148736 | 0.148736 | 0.101760 | no |
| H6_long_coolant_path | 1500 | 0.200554 | 0.207093 | 0.150116 | no |
| H6_long_coolant_path | 3000 | 0.212314 | 0.209689 | 0.158835 | yes |
| H7_pessimistic_nuclear_data | 1500 | 0.157241 | 0.157154 | 0.104292 | yes |
| H7_pessimistic_nuclear_data | 3000 | 0.159659 | 0.158704 | 0.110893 | yes |
| H8_hot_low_conductivity | 1500 | 0.203155 | 0.204521 | 0.132973 | no |
| H8_hot_low_conductivity | 3000 | 0.209149 | 0.208052 | 0.143540 | yes |

R3 median beats NSGA-II median in 5 of 8 cells; rule requires 6. PO4: FAIL.

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
