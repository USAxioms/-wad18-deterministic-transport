# Protocol, decision rules, and R3 implementation

## Execution sequence (manuscript Section 5.1)

1. The spec is loaded and validated (28 method-level checks, `01`).
2. The reference and protocol are frozen, with the spec SHA-256 recorded (`02`).
3. The reference design is evaluated (`03`).
4. R3 runs with a budget of 1000 unique evaluations, logging every evaluation (`04`, `05`).
5. The baselines run under the same budget: NSGA-II and random search, seeds 1–5 each (`06`).
6. The methods are compared by exact 2-D hypervolume with reference point (TBR 1.10, Δp 200 kPa), with Δp normalised (`07`).
7. A candidate is selected from the R3 front by the predeclared rule (`08`).
8. The candidate goes through 64 θ-corner uncertainty analysis and one-at-a-time sensitivity, if a candidate exists (`09`, `10`).
9. Output-level checks are run: bit-identical re-evaluation, HV recomputed from the log, archive invariants, and budgets (`11`).
10. Proof obligations are recorded (`12`), along with front diagnostics (`13`).

Cached designs cost nothing, so every method is charged only for **unique** evaluations.

## R3 = I ∘ V ∘ F ∘ A

- **A (analyze).** The focus set is the front extremes plus the pair bounding the largest
  hypervolume gap. At unit step, the whole front becomes the focus. Binding constraints
  (slack < 0.05) are logged. Move directions are ranked by recorded success.
- **F (refine).** Each focus design gets ±step coordinate moves in every variable and a
  pattern extrapolation of its last successful move. Single-violation designs that would
  dominate their parent also get unit "repair" combinations in every other variable, at most 4 per iteration.
- **V (validate).** Each design passes grid and budget invariants and a full constraint
  evaluation. It is admitted to the archive only if it is feasible and non-dominated. The
  archive is then checked for invariants and monotone hypervolume.
- **I (iterate).** On a hypervolume gain, the steps are kept. Otherwise each step is halved.
  At unit steps with the whole front as focus and no gain, Φ(A) = A, which is a fixed point,
  and the run stops.

## Decision rules

These are verbatim from `spec/research_spec.json` → `evaluation_protocol.acceptance`.
There is deliberately no single overall PASS: the per-obligation outcomes are reported separately.

## v1.1.0 additions

- **Search feasibility.** A design is feasible during search only if every normalised slack
  is at least 0.05. This applies identically to R3, NSGA-II, and random search, and violation
  is measured below that margin. The reference evaluation, PO2, the PO5 corners, and the
  sensitivity analysis use the declared limits.
- **R3 rule (a).** At a unit-step no-gain iteration, if the current cycle gained hypervolume, the
  steps reset to their initial values. FIXED_POINT means a complete cycle with no gain.
- **R3 rule (b).** With an empty archive, the focus is the least-violation evaluated design.

## v1.2.0 additions

- **R3 initialisation.** R3 is seeded with a deterministic Latin-hypercube sample of 20 designs. The sample is drawn
  continuously and then floored onto the grid, so the j-th smallest value of each variable lies in
  stratum j. Seeding makes R3 stochastic, so it is compared by its distribution over seeds.
- **Re-seeding.** At a local fixed point R3 draws a new 20-design batch instead of stopping, and so stops only
  at the budget.
- **PO4.** PO4 is decided only on held-out cells: 4 unseen instances × budgets {1000, 2000} × seeds 101–107.
  It is PASS iff the R3 median HV exceeds the NSGA-II median HV in at least 6 of 8 cells.

## v1.3.0 and v1.4.0 additions

- **Escalation.** When single-coordinate proposals are exhausted (v1.3.0), or also after any no-gain iteration
  (v1.4.0), R3 proposes coupled two-coordinate moves (capped), then recombination of front designs.
- **Held-out sets.** Each confirmatory cycle uses a fresh held-out set, declared and hashed before that cycle's
  development. Used sets become development data. The decision rule is unchanged across cycles.
- **Multiplicity.** `po4_multiplicity.py` reports the exact chance, under an idealised null, that any cycle passes.
