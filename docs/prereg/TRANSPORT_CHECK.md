# Pre-declared transport check of the surrogate's design claims

**Written before** computing transport for any design other than the reference. Already seen:
- the reference design: 1-D TBR 0.5526 (vacuum) and 1.5852 (white); with coverage, 0.4531 and 1.2998;
- the reference convergence study: mesh −1.4% at 5 cm, S4 −0.001%, P1 +0.14%.

**Change made after the first run (disclosed).** `spec/transport_model.json` declared a vacuum plasma-side boundary.
The first result showed 109% of the incident current leaving through the front face. That is consistent with
Pb(n,2n) multiplication plus slow moderation in lead, and in a torus those neutrons would re-enter the blanket.
The white (isotropic re-entry) boundary was therefore added. Vacuum and white are reported together as lower and
upper idealisations; neither is the 3-D answer.

## Designs (fixed)

| Label | Design |
|---|---|
| REF | the reference design |
| S110 | the v1.1.0 selected design (t_b 0.47, e 0.90, t_mult 0.05, f_struct 0.105, f_cool 0.030, d_h 11 mm) |
| S140 | the v1.4.0 selected design (as S110 but t_b 0.46) |

## Questions and decision rules (fixed)

**Q1, direction.** Does transport agree that the selected designs breed more than REF?
- AGREE iff TBR(S) > TBR(REF) under BOTH boundary conditions, for S110 and S140 separately.
- DISAGREE iff TBR(S) < TBR(REF) under both.
- Otherwise INDETERMINATE.

**Q2, magnitude.** Is the surrogate's relative TBR gain over REF within the range spanned by the two transport
boundary conditions? Report YES or NO.

**Q3, requirement.** Does each selected design meet TBR ≥ 1.10 with the 5% search margin (≥ 1.155)?
- MET iff white AND vacuum both meet it.
- NOT_MET iff neither does.
- Otherwise DEPENDS_ON_BOUNDARY.

**Q4, surrogate calibration.** Does each surrogate TBR (REF, S110, S140) lie within [vacuum, white]? Report.

Numerics are fixed to the spec (S8, P3, cells ≤ 2.5 cm). Mesh uncertainty of about 1.4% is attached to every
transport value. Gaps smaller than 1.4% are reported as within numerical uncertainty and are not used to decide Q1.
