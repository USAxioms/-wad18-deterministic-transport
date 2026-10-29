# Freeze record: protocol v1.2.0

Written before the held-out runner existed and before any held-out execution.

- spec/research_spec_v1.2.0.json SHA-256: `956710ebac93d5a1d8294af1261e24b5fe581467adc45676bfab83534939ee54`
- r3capsule/r3.py SHA-256 at freeze: `c683b62564467f12c80aca569f44440fad9f3b4df4d7d60b973c93f8d19684f1`
- docs/dev/R3_DEV_LOG.jsonl SHA-256 at freeze: `0b11f8ba5117578bcc5d6e76c0f8fa82ff7c4210020a46e27b2f14a1d3c79788` (21 variants)

## Development (disclosed in full)

All 21 variants are in the dev log, including the losers.

- Variants 1–13 were scored on single runs.
- Variants 12–13 showed that single-run "wins" were seed luck.
- The harness was changed to compare R3's seed distribution (seeds 0–4) with NSGA-II.
- Variants 14–21 used that distribution comparison.

**Chosen design:**
- 20 Latin-hypercube initial points.
- A 20-point re-seed at each local fixed point, instead of stopping.
- The v1.1.0 rules otherwise unchanged.

**Development evidence:** R3 median 0.210398 versus NSGA-II median 0.208245, beating 3 of 5 seeds.
The edge is small and was selected after 21 variants, so it is selection-biased.

## Held-out test (decides PO4)

There are 4 instances never used in development: wall load ±20%, radial build +5 cm, and
breeder conductivity −20%. These are crossed with budgets of 1000 and 2000, giving 8 cells.
Each method runs on 7 new seeds (101–107).

PO4 is PASS iff the R3 median HV exceeds the NSGA-II median HV in at least 6 of 8 cells.
The result will be reported whatever it is. If it fails, a further cycle needs a NEW held-out
set; this one cannot be reused.

Self-attested within one session; no external timestamp.
