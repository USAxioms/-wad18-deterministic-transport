# Pre-declared cylindrical transport check

**Written before** any cylindrical blanket calculation. The solver had been verified only on analytic and
one-group problems: quadrature moments, the flat-flux test, and conservation.

**Model.** `spec/transport_model.json`, section `cylinder`: plasma radius 2.9 m, first wall at 3.1 m,
GL order 8 (4 ξ levels) × 8 azimuths, P1, cells ≤ 2.5 cm, step differencing. The designs are REF, S110 and
S140, defined exactly as in `TRANSPORT_CHECK.md`. TBR includes coverage 0.82.

**Numerical uncertainty U** (REF only, computed first): the largest relative TBR change among three runs,
each varying one setting: cells 5 cm, 16 azimuths, and GL order 4. U is attached to every value.

**Questions and rules (fixed).**
- **C1, bracket.** Does the cylinder TBR lie within the slab [vacuum, white] bounds for each design? Report YES or NO.
- **C2, direction.** AGREE iff TBR(S) − TBR(REF) > U·TBR(REF) for S110 and S140 separately; DISAGREE iff
  TBR(S) − TBR(REF) < −U·TBR(REF); otherwise INDETERMINATE.
- **C3, requirement** (TBR ≥ 1.155):
  - MET iff TBR > 1.155·(1+U);
  - NOT_MET iff TBR < 1.155·(1−U);
  - otherwise WITHIN_UNCERTAINTY.
- **C4, surrogate error.** Report (surrogate − cylinder)/cylinder for each design, and whether the surrogate's
  relative gain over REF lies within ±U of the cylinder's gain (YES or NO).

**Sensitivity** (REF only, reported but not used for C1–C4): first-wall radius 2.5 m and 4.0 m, each with
the plasma 0.2 m inside it.
