# Fusion breeding-blanket R3 reproducibility capsule

Executable implementation of the manuscript *Advancing Nuclear Fusion Through
Invariant-Driven Recursive Refinement* (M. A. Russell, 28 Oct 2026).

**Arithmetic:** WAD-18 only. Every real quantity is an exact Python `int` scaled by
10^18, with floor rounding and signed 256-bit result bounds. There are no floating-point
literals, no true division, no `math`, `random`, `time`, `decimal`, or `fractions`, and no float
JSON tokens. This is enforced by `audit/zero_float_audit.py` over all source and outputs.

**Dependencies:** Python 3.10+ standard library only. No network and no compiled code.

## Run

```sh
./run_final.sh       # final protocol v1.4.0 only: PO1-PO5 verdicts in about 4 minutes
./build_capsule.sh   # 5 studies, 3 held-out cycles, nuclear data, slab and cylinder transport, 61 tests, audit (~45 min)
```

Individual steps:

```sh
python3 run_capsule.py spec/research_spec_v1.1.0.json results/v1.1.0
python3 tests/run_tests.py
python3 reproduce.py spec/research_spec_v1.1.0.json results/v1.1.0
python3 audit/zero_float_audit.py
python3 manifest.py verify
```

## Five protocol versions, three confirmatory cycles

Each protocol version was frozen before its first execution (`docs/prereg/`). All of them are
re-executed and byte-compared on every build.

| Obligation | v1.0.1 | v1.1.0 | v1.2.0 | v1.3.0 | v1.4.0 |
|---|---|---|---|---|---|
| PO1 reproducible execution | PASS | PASS | PASS | PASS | PASS |
| PO2 constraint satisfaction | FAIL | PASS | PASS | PASS | PASS |
| PO3 engineering improvement | FAIL | PASS | PASS | PASS | PASS |
| PO4 R3 vs NSGA-II (held-out) | FAIL | FAIL | FAIL 2/8 | FAIL 5/8 | **PASS 7/8** |
| PO5 robustness (64 corners) | FAIL | PASS | PASS | PASS | PASS |
| PO6 physical relevance | not est. | not est. | not est. | not est. | not est. |

**PO4 caveat.** PO4 passed on the third confirmatory cycle. Under an idealised null, the chance that
at least one of three cycles would reach 7 of 8 is about 0.10 (`results/PO4_multiplicity.json`).
The pass is valid under the frozen rule, but the evidence is moderate.

**Robustness caveat.** The v1.4.0 design holds at all 64 corners with only 0.0072% worst-corner slack.
The v1.1.0 design is more robust.

**Nuclear data.** Evaluated FENDL-3.2c multigroup data for H, Li-6, Li-7, Be-9 and Pb are bundled
in `data/nuclear/`, read by integer-exact readers (`r3capsule/ndata/`) and verified against the raw
ENDF evaluations (`python3 ndata_verify.py`). The surrogate model does not use them yet.

**Transport check.** An integer 1-D multigroup S_N model (all 21 nuclides, FENDL-3.2c) recomputes TBR.
- It confirms that the selected designs breed more than the reference (+17% to +27%).
- It shows the surrogate underestimates that gain.
- The slab brackets the reference TBR between 0.45 (vacuum plasma side) and 1.30 (white).
- An integer 1-D **cylindrical** model resolves the bracket: reference 1.268, selected designs 1.485 and 1.483,
  with 3.3% numerical uncertainty. All meet TBR ≥ 1.155, and the surrogate is conservative by 8.5–12.7%.

Run `python3 transport_check.py run all && python3 transport_check.py summarize`, and likewise
`cylinder_check.py`. Results are in `results/transport/` and `results/cylinder/`, and the pre-declared rules in
`docs/prereg/TRANSPORT_CHECK.md` and `docs/prereg/CYLINDER_CHECK.md`.

**PO6** cannot pass here: it needs 3-D Monte Carlo transport, thermal-hydraulics, and benchmark or
experimental data. The model lives in one module (`r3capsule/model.py`), so it can be replaced on a capable machine.

## What this capsule is and is not

It is a complete, deterministic, auditable execution of the manuscript's protocol.

It is **not** evidence about a real blanket. The physics is a reduced-order surrogate with
declared, unvalidated constants (`docs/MODEL_CARD.md`), so PO6 cannot pass here.
To make an engineering claim, the model must be replaced by benchmarked neutronics
(e.g. OpenMC) and thermal-hydraulics. The swap touches only `r3capsule/model.py`.

## Layout

```
spec/research_spec.json          v1.0.1 frozen inputs (exact decimal strings)
spec/research_spec_v1.1.0.json   v1.1.0 frozen inputs
spec/research_spec_v1.2.0.json   v1.2.0 frozen inputs + cycle-1 held-out design
spec/research_spec_v1.3.0.json   v1.3.0 + cycle-2 held-out
spec/research_spec_v1.4.0.json   v1.4.0 + cycle-3 held-out
r3capsule/r3_v120.py, r3_v130.py frozen R3 of cycles 1 and 2 (hash-guarded)
po4_multiplicity.py              exact multiplicity analysis across cycles
run_final.sh, final_summary.py   one command for the final protocol and its verdicts
r3capsule/ndata/                 integer-exact MATXS and ENDF-6 readers
ndata_verify.py                  nuclear-data verification (structure, layout, closure, ENDF bounds)
r3capsule/transport.py           integer 1-D multigroup S_N solver
r3capsule/blanket_transport.py   design vector -> transport TBR (spec/transport_model.json)
transport_check.py               pre-declared slab transport check of the surrogate
r3capsule/cylinder.py            integer 1-D cylindrical S_N solver
cylinder_check.py                pre-declared cylindrical check
data/nuclear/, data/INVENTORY.json  bundled evaluated data; hashes of every supplied file
heldout.py, heldout_repro.py     confirmatory PO4 tests and their reproduction
dev/r3_dev*.py                   development harnesses (log every variant, per cycle)
r3capsule/wad18.py               WAD-18 arithmetic (exp, roots, fractional powers)
r3capsule/model.py               surrogate multiphysics model + constraints
r3capsule/r3.py                  R3 = I o V o F o A search
r3capsule/baselines.py           NSGA-II and random search
r3capsule/uq.py                  64 theta corners, one-at-a-time sensitivity
r3capsule/pipeline.py            manuscript execution sequence, proof obligations
tests/                           float-free runner, 61 tests
audit/zero_float_audit.py        AST and output audit
results/v1.0.1 ... v1.4.0        evidence per study (00..15, REPORT.md, CAPSULE_REPORT.json)
results/v1.x.0_heldout           held-out runs, summary, reproduction check (cycles 1-3)
results/PO4_multiplicity.json    exact multiplicity analysis
results/                         test_results.json, zero_float_audit.json
docs/                            model card, protocol, WAD-18 spec, revision log, freeze records,
                                 dev log, revised manuscript (docs/paper/)
MANIFEST.json                    SHA-256 of every file
```
