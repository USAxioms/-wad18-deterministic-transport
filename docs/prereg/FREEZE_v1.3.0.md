# Freeze record: protocol v1.3.0 (R3 cycle 2)

Written before any execution on the cycle-2 held-out conditions.

- spec/research_spec_v1.3.0.json SHA-256: `04925a7c6fe306bc65f1721749a78a668d40f7a7288a4be6f1fbe102185f0eac`
- r3capsule/r3.py SHA-256 at freeze: `0fb2bde69f261ea697aab01753b67ac4e26031b2cfc582d9475e90de3f09d5f1`
- docs/dev/R3_DEV_LOG_CYCLE2.jsonl SHA-256 at freeze: `b8e577c86ff62a73e2a21724e5933ac82bfc811b0fd43924da74847ad61cda27` (13 variants)
- docs/prereg/CYCLE2_HELDOUT_DECLARATION.json SHA-256: `64e04b29bd102bbbac23d4f0562a77801d9c0a2299eab602894bf5bfceb2e83b`
  (declared before cycle-2 development; its instances and seeds are copied unchanged into the spec)

## Cycle-2 development (disclosed in full)

The cycle-1 held-out failure was diagnosed on what had become development data. After about 900
evaluations, every one-variable neighbour of the front had been evaluated. R3 then made zero
new evaluations per iteration and fell back on random re-seeding, which is why it stagnated.

- **Fix:** neighbourhood escalation. Coupled two-variable moves are tried first, then recombination of
  front designs, and only then random re-seeding.
- **Refuted:** focusing on infeasible designs (variants 6–7, 0/9 cells).
- **Selection criterion:** stated before the final variants ran. Most development cells won, with ties broken by
  total margin.
- **Chosen design:** variant 13 (40 Latin-hypercube points, starting step divisor 6, escalation, 20-point
  re-seed). It won 6 of 9 development cells with a total margin of +0.0040.
- **Bias:** this result was selected from 13 variants, and four of its development cells were seen in
  cycle 1. It is therefore biased upward.

## Held-out rule (unchanged from v1.2.0)

PO4 is PASS iff the R3 median HV exceeds the NSGA-II median HV in at least 6 of 8 cells.
This is the second confirmatory cycle: cycle 1 failed with 2 of 8 cells.
