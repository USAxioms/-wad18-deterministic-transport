# Revision log

Every change made after the first full execution is recorded here with its effect on the results.
None of these changes was made to alter a proof-obligation outcome. The PO statuses
were identical before and after each change.

## R1: spec 1.0.0 → 1.0.1, constraint C08 normalisation (method-level refinement)

- **Defect.** In 1.0.0, C08 was written as `f_struct − f_struct_min ≥ 0` with limit 0. Because
  slacks are normalised by |limit|, a zero limit left C08's slack un-normalised. The 0.05
  selection margin therefore demanded 0.05 of *absolute* extra structure fraction, which is
  dimensionally inconsistent with every other constraint.
- **Change.** C08 now uses the output `f_struct_ratio = f_struct / f_struct_min ≥ 1`.
- **Effect on feasibility.** None. The two forms are equivalent for f_struct_min > 0.
- **Effect on R3.** None. The trajectory is bit-identical in evaluated keys, order, feasibility, and objectives, which was verified by direct comparison.
- **Effect on NSGA-II.** Small. Its comparison between two infeasible designs uses total violation magnitude, and C08's scale changed.
  - 1.0.0: NSGA-II HV median 0.266526048865863476, max 0.271345104059701532.
  - 1.0.1: NSGA-II HV median 0.266526526117472924, max 0.270991614679426319.
- **Effect on outcomes.** PO4 was FAIL in both. The selected candidate was none in both.
- **Not changed.** The selection margin (0.05) was kept, even though it yields no candidate.
  Relaxing it after seeing the result would be outcome-driven.

## R2: SplitMix64.below() for bounds above 2^64

- **Defect.** For n > 2^64 the rejection window was empty, causing an infinite loop. The
  tests exposed it; no search uses such bounds.
- **Effect.** None on results. For n ≤ 2^64 the code path is byte-identical, and this is
  covered by the regression test `test_below_unchanged_for_small_bounds`.

## R3: test bound for exp(a)·exp(−a)

- The original 64-ulp tolerance was arbitrary and wrong. The analytically derived bound is
  2·e^a ulps + 2, and the test now uses it.

## R4: audit self-flags

- The audit flagged its own docstring example and its detector's reference to the `float`
  type name. Both were rewritten. No exemption mechanism exists.

## R5: protocol v1.1.0 (new study; v1.0.1 retained)

- **Freeze.** The spec was frozen, with its SHA-256 recorded in `docs/prereg/FREEZE_v1.1.0.md`,
  before the implementing code existed and before any v1.1.0 execution.
- **Implementation.** It is controlled entirely by spec fields, which default to v1.0.1 behaviour.
  After implementation, all 12 v1.0.1 pipeline files were re-checked and are byte-identical to
  the original v1.0.1 run.
- **First and only execution, as frozen:**
  - PO2, PO3, and PO5 PASS.
  - PO4 FAIL: R3 HV 0.201450854654089172 versus NSGA-II median 0.208245845255379326.
  - PO6 NOT_ESTABLISHED.
- **Restart rule.** Rule (a), the multiscale restart, was in force but did **not** trigger
  within the budget. R3 consumed all 1000 evaluations during its first cycle, because the
  tightened feasible region gave it more to explore. A mechanism test with a 4000 budget
  confirms that the rule works: one restart, then a multiscale FIXED_POINT at 1249 evaluations.
- **Test correction.** A test I wrote before reading the log assumed a restart would occur. It was
  replaced with tests of the recorded behaviour and of the mechanism.

## R6: protocol v1.2.0 (R3 applied to R3; held-out confirmatory test)

- **Leftover code.** Three R3 options were found in `r3.py` from an interrupted earlier step: Latin-hypercube
  seeding, contribution-ranked focus, and earlier scale refinement. They were reviewed, and a budget-accounting
  bug was fixed (initial seeding now runs inside the budget guard). Their defaults leave
  v1.0.1 and v1.1.0 byte-identical, which was verified.
- **New option.** `reseed_on_fixed_point` was added: at a local fixed point, a new Latin-hypercube batch is drawn
  instead of stopping.
- **Development.** 21 variants were run on the development conditions. All are logged in `docs/dev/R3_DEV_LOG.jsonl`.
  - Variants 1–13 were scored on single runs.
  - Variants 12–13 revealed that the apparent single-run win (variant 7) was seed luck.
  - The harness then switched to comparing R3's seed distribution (seeds 0–4).
- **Chosen design.** 20 initial Latin-hypercube points plus a 20-point re-seed. The development median was
  0.210398 versus the NSGA-II median 0.208245: a small, selection-biased edge.
- **Freeze.** The spec, the r3.py hash, and the dev-log hash were recorded in `docs/prereg/FREEZE_v1.2.0.md`
  before the held-out runner existed. The runner refuses to execute if r3.py changes.
- **Held-out result: FAIL, 2 of 8 cells (6 required).** The development edge did not generalise.
  - Worst cell: H1, budget 1000, R3 median 0.12983 versus NSGA-II 0.20126.
  - R3 beats random search in all 8 cells.
  - In H2 its median is identical at budgets 1000 and 2000, which indicates stagnation.
  - The held-out run reproduces byte-identically.
- **Correction.** A test asserting an exact discrete Latin property was wrong; with 20 points on grids
  of 9–31 values that property is impossible. It was replaced by the property the sampler guarantees.
  The r3.py docstring was deliberately left unchanged so that the frozen hash stays valid.
- **Status of the held-out set.** The held-out set H1–H4 with seeds 101–107 is now *used*. Any further R3 cycle must
  be confirmed on a new, previously unseen held-out set.

## R7: protocol v1.3.0 (R3 cycle 2)

- **Held-out declared first.** The cycle-2 held-out set (H5–H8, budgets 1500 and 3000, seeds 201–207) was declared and hashed
  (`docs/prereg/CYCLE2_HELDOUT_DECLARATION.*`) before any cycle-2 development run.
- **Diagnosis.** On the used cycle-1 cells, which are now development data: after about 900 evaluations every one-variable
  neighbour of the front had been evaluated. R3 then made zero new evaluations per iteration and
  degenerated into random re-seeding.
- **Fix.** Neighbourhood escalation (`escalate`): coupled two-variable moves first, then recombination of front designs,
  and random re-seeding only after both.
- **Refuted.** Focusing on infeasible designs (`infeasible_focus`) won 0 of 9 cells; it is retained in the code and logged.
- **Development.** 13 variants are in `docs/dev/R3_DEV_LOG_CYCLE2.jsonl`. The selection criterion (cells won, then total margin) was
  stated before the final variants ran. Variant 13 was chosen.
- **Held-out result: FAIL, 5 of 8.** H5/3000 was an exact tie, which counts against R3 under the unchanged rule.
- **Freezing earlier code.** `r3capsule/r3_v120.py` is a byte-identical copy of the cycle-1 R3, kept so that cycle 1 still re-executes under
  its hash guard. `heldout.py` maps each protocol version to its frozen module.

## R8: protocol v1.4.0 (R3 cycle 3)

- **Held-out declared first.** The cycle-3 held-out set (H9–H12, budgets 1200 and 2500, seeds 301–307) was declared and hashed before
  any cycle-3 development.
- **Diagnosis.** On H5–H8: escalation fired only when every neighbour had been evaluated, so long plateaus
  persisted.
- **Fix.** Escalation now also fires after any iteration with no gain (`escalate_trigger = no_gain`),
  with `pair_cap = 30`.
- **Development.** 7 variants on 17 development cells (`docs/dev/R3_DEV_LOG_CYCLE3.jsonl`). Variant 4 was chosen under the
  unchanged criterion, winning 14 of 17. `r3capsule/r3_v130.py` freezes the cycle-2 code.
- **Held-out result: PASS, 7 of 8.** H9/2500 was the only miss, an exact tie. The R3 median exceeded the NSGA-II maximum in 3 cells.
- **Multiplicity** (`results/PO4_multiplicity.json`, exact integers). Under an idealised null of independent
  fair-coin cells, the chance that at least one of three cycles reaches 7 of 8 is 1707993/16777216 ≈ 0.102.
  The PASS is valid under the frozen rule, but the evidence is moderate.
- **Design selected by v1.4.0.** The new R3 selects a different design: t_b = 0.46 m, TBR 1.2947, Δp 18.19 kPa,
  minimum nominal slack 5.19%. It is feasible and dominating at all 64 corners, but its worst-corner breeder-temperature
  slack is 0.0072%, which is thin. The v1.1.0 design (worst-corner slack 0.47%) is the more robust choice.
- **Audit.** The audit flagged the new `po4_multiplicity.py` (a `math` import and `**` with variable exponents).
  It was rewritten with integer-only helpers and no exemption; the output is byte-identical.
- **Interrupted build.** The background build was interrupted during the cycle-3 reproduction. The remaining steps
  were re-run, and a full fresh-unpack rebuild was then used for confirmation.

## R9: audit result depended on whether the audit had run before

The clean-unpack rebuild matched 94 of 95 result files. The mismatch was `zero_float_audit.json`. On a second
run in the same tree, the audit scanned its own previous report (90 output files instead of 89), so its output
depended on history. The audit now excludes its own report from the scan and checks that report after
writing it. Verified: two consecutive runs and a clean build give byte-identical reports (35 source files, 89 outputs,
0 violations). No other result changed. The manuscript's file count was corrected from 90 to 89.

## R10: evaluated nuclear data added and verified (not yet used by the model)

- **Data.** FENDL-3.2c MATXS libraries (NJOY2016, 211 neutron and 42 gamma groups, 293.6 K) for H-1, Li-6, Li-7,
  Be-9 and Pb-204/206/207/208, plus pointwise ENDF-6 evaluations for Li-6, Li-7 and Be-9 (FENDL-3.0) and
  Pb-204/206 (JEFF-3.1.1), are bundled in `data/nuclear/`. Every supplied file is hashed in `data/INVENTORY.json`.
- **Readers.** New integer-exact readers in `r3capsule/ndata/`. The MATXS transfer-matrix layout was not assumed: of
  six candidate layouts, only one makes the P0 elastic transfer out of each group equal that group's elastic cross
  section (H-1: 4 ppm; the others are off by 80% or more).
- **Verification** (`ndata_verify.py`, `results/ndata_verification.json`):
  - All word counts are exact.
  - Elastic balance closes within 0.1% below 20 MeV for every material.
  - Each processed group value lies within the weight-independent [min, max] bounds of the matching
    ENDF evaluation, after excluding resolved-resonance ranges and E ≤ 100 eV (Doppler: the libraries are at
    293.6 K, the ENDF files at 0 K).
  - These exclusions and the 0.1% tolerance were set after first inspection; unfiltered counts are always reported.
- **Known data features.**
  - Lead elastic rows above 20 MeV fall short by up to 2.7% (forward-peaked scattering at P6).
  - Li-7 at 20–21 MeV differs from the FENDL-3.0 file, a version difference across a 20 MeV splice.
  - Both lie above the 14.1 MeV D-T source.
- **Not usable yet.**
  - Fe, Cr and W were supplied as raw ENDF-6 evaluations, which need NJOY-type processing before transport.
  - O-16 has not been supplied.
  - Without steel and water, no blanket-faithful transport calculation is possible, so the
    surrogate model and all study results are unchanged.

## R11: full material set and an integer transport model (a check on the surrogate, not a replacement)

- **New data.** FENDL-3.2c MATXS for O-16, Cr-50/52/53/54, Fe-54/56/57/58 and W-182/183/184/186 was added and verified.
  - All 21 materials pass the word-count, elastic-balance and new total-closure checks (V4: total equals the sum of
    neutron-emitting plus pure-absorption reactions, within 10 ppm below 20 MeV).
  - Fe, Cr and W totals lie within their ENDF bounds above the resonance regions.
  - The fragile resonance-range finder in `endf.py` was replaced by a strict, conservative rule.
- **Conventions verified from the data.**
  - P_l matrices carry no (2l+1) factor: hydrogen's P1/P0 equals its mubar at about 2/(3A).
  - (n,2n) matrices include multiplicity 2.
  - The libraries have no thermal upscatter (free-gas hydrogen, no S(α,β)).
- **Solver.** `r3capsule/transport.py`: 1-D slab, 211 groups, S8 Gauss–Legendre (integer Newton roots),
  step characteristic, P3. P0 and P1 are solved implicitly per group and P2–P3 are iterated.
  - Verified: S8 integrates degree 14 to within 7×10⁻¹⁸; pure-absorber transmission equals the analytic value to
    10⁻¹⁸; the neutron balance closes to 10⁻¹⁰ or better in every run.
  - Convergence (reference, white boundary): 5 cm cells −1.4%, S4 −0.001%, P1 +0.14%. Mesh is the dominant
    numerical uncertainty.
- **Declared assumptions.** `spec/transport_model.json` gives the densities, EUROFER and PbLi compositions,
  isotopics, a Be multiplier, and the manifold and shield mixtures. The surrogate did not define these.
- **Boundary condition, changed after the first run (disclosed).** The declared vacuum plasma-side boundary gave
  0.45 for the reference, with 109% of the incident current leaving through the front face. In a torus those
  neutrons would re-enter the blanket, so a white boundary was added. The two are reported as bounds.
- **Pre-declared check** (`docs/prereg/TRANSPORT_CHECK.md`, written before any non-reference design was run; rules
  applied in integers by `transport_check.py`):
  - **Q1, direction: AGREE** for both selected designs (+17% white, +27% vacuum).
  - **Q2, magnitude: NO.** The surrogate's +12% gain is below the transport range, so the Be layer is undervalued.
  - **Q3, TBR ≥ 1.155: DEPENDS_ON_BOUNDARY.**
  - **Q4:** every surrogate TBR lies inside the transport bounds.
- **Unchanged.** All search studies and their verdicts still use the surrogate. Transport is a check on it.

## R12: integer cylindrical transport resolves the plasma-side boundary question

- **Solver.** `r3capsule/cylinder.py`: 1-D r-geometry discrete ordinates, entirely WAD-18.
  - Gauss–Legendre ξ levels × Chebyshev azimuths, with cosines from an integer Taylor series.
  - Step differencing in space and angle (positive, exactly conservative); P0 implicit, P1 iterated.
  - Upscatter is asserted absent.
- **Verification.**
  - Quadrature moments within 10⁻¹⁷.
  - Flat-flux test: an infinite medium gives φ = s/Σ flat to 12 digits with zero current, so the angular
    redistribution is consistent.
  - Conservation within 10⁻¹³ with a void cavity and anisotropic scattering.
- **Model.** The poloidal cross-section is an infinite cylinder: a plasma radius of 2.9 m with a uniform 14.1 MeV
  source, a first wall at 3.1 m, then the same layers and materials as the slab. Neutrons leaving the blanket front
  re-enter across the chamber, which replaces the slab's vacuum and white idealisations.
- **Pre-declared check** (`docs/prereg/CYLINDER_CHECK.md`, written before any cylindrical blanket run; rules
  applied by `cylinder_check.py`).
  - **U = 3.29%** (mesh coarsening dominates; azimuths and levels contribute below 0.02%).
  - **TBR including coverage:** REF 1.268, S110 1.485, S140 1.483.
  - **C1:** every value lies inside its slab bracket.
  - **C2, direction: AGREE** (+17.1% and +16.9%).
  - **C3, TBR ≥ 1.155: MET** for all three designs, beyond U.
  - **C4:** the surrogate underestimates TBR by 8.5–12.7%, and its gain is outside ±U of the cylinder gain.
  - **Sensitivity:** first-wall radius 2.5 m → 4.0 m changes the REF TBR by only ±0.1%.
- **Unchanged.** The search still uses the surrogate, which proves conservative on TBR. PO6 is still not
  established: there is no first wall in either model, 3-D effects are only in the coverage factor (0.82,
  assumed), data are at 293.6 K with free-gas hydrogen, and there is no benchmark or experimental comparison.

## R13: one-command final run; stale reports corrected

- **One command.** `./run_final.sh` runs the final protocol v1.4.0 (study, held-out PO4 test, reproduction
  check, report) and prints every verdict via `final_summary.py`.
- **Clearer default.** `run_capsule.py` with no arguments now states that it replays the original v1.0.1 protocol.
- **Defect found by testing the new command from a clean unpack.** The shipped `REPORT.md` and
  `CAPSULE_REPORT.json` of every study still quoted 49 passing tests, because they had not been regenerated
  after the test suite grew to 61. They were regenerated; no computed result changed.
- **Verified.** A clean unpack plus `./run_final.sh` now leaves all 232 manifest files byte-identical.

## Not done, deliberately

R3 was not tuned against the held-out results, and PO6 was not redefined. Changing the
algorithm until it wins on the same conditions, or relaxing an acceptance rule, would make
any eventual PASS uninformative. A credible PO4 test requires a
redesigned R3 frozen in advance and evaluated on held-out conditions, for example new seeds,
budgets, or problem instances.
