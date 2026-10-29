# Freeze record: protocol v1.4.0 (R3 cycle 3)

Written before any execution on the cycle-3 held-out conditions.

- spec/research_spec_v1.4.0.json SHA-256: `67c94308ffaed368a7b7a3866009dc02cc0d34cde3b439b8c9637c372edd4297`
- r3capsule/r3.py SHA-256 at freeze: `db14c3dcc173c98d0c5462a8a0823392eb17bf682b5680fb10a764bc383756cf`
- docs/dev/R3_DEV_LOG_CYCLE3.jsonl SHA-256 at freeze: `8be444ca553a8c9cb58b7c86394b2c613518409b092cabe7223597b73a466afd` (7 variants)
- docs/prereg/CYCLE3_HELDOUT_DECLARATION.json SHA-256: `4bb3a68e52bc8f2b4e45c9b5160b0745b4780e77501e0eadcff75f65b9a9f360`

## Cycle-3 development (disclosed in full)

The cycle-2 low-budget losses (H6/1500, H8/1500) were diagnosed on what had become development data.
Escalation fired only when every neighbour had been evaluated, so R3 sat on long plateaus where
neighbours remained but none helped.

- **Fix:** also escalate after any iteration that brings no gain (`escalate_trigger = no_gain`).
- **Pair phase:** a cheaper two-variable phase (`pair_cap = 30`) performed best.
- **Selection criterion:** unchanged and stated in advance. Most of the 17 development cells won, with ties
  broken by total margin.
- **Chosen design:** variant 4, which won 14 of 17 development cells.
- **Bias:** this result was selected from 7 variants, and 16 of its development cells were seen in earlier
  cycles. It is therefore biased upward.

## Held-out rule (unchanged)

PO4 is PASS iff the R3 median HV exceeds the NSGA-II median HV in at least 6 of 8 cells.
Ties count against R3. This is the third confirmatory cycle: cycle 1 scored 2 of 8 and cycle 2 scored 5 of 8.
