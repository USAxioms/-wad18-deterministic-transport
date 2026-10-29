#!/bin/sh
# Full capsule build: five protocol versions, three held-out cycles, tests, reproduction,
# multiplicity analysis, nuclear-data verification, reports, zero-float audit, manifest. (~16 min, stdlib only)
set -e
cd "$(dirname "$0")"
rm -rf results && mkdir results
for v in 1.0.1 1.1.0 1.2.0 1.3.0 1.4.0; do
  s=spec/research_spec_v$v.json; [ "$v" = "1.0.1" ] && s=spec/research_spec.json
  python3 run_capsule.py $s results/v$v
done
for v in 1.2.0 1.3.0 1.4.0; do
  python3 heldout.py spec/research_spec_v$v.json results/v${v}_heldout
done
python3 ndata_verify.py
python3 transport_check.py run all
python3 transport_check.py summarize
python3 cylinder_check.py run all
python3 cylinder_check.py summarize
python3 tests/run_tests.py results/test_results.json
for v in 1.0.1 1.1.0 1.2.0 1.3.0 1.4.0; do
  s=spec/research_spec_v$v.json; [ "$v" = "1.0.1" ] && s=spec/research_spec.json
  python3 reproduce.py $s results/v$v
done
for v in 1.2.0 1.3.0 1.4.0; do
  python3 heldout_repro.py spec/research_spec_v$v.json results/v${v}_heldout
done
python3 po4_multiplicity.py
for v in 1.0.1 1.1.0 1.2.0 1.3.0 1.4.0; do python3 make_report.py results/v$v; done
python3 audit/zero_float_audit.py
find . -name __pycache__ -type d -prune -exec rm -rf {} +
python3 manifest.py build
python3 manifest.py verify
find . -name __pycache__ -type d -prune -exec rm -rf {} +
