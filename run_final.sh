#!/bin/sh
# One command for the final protocol (v1.4.0): run the study, the held-out PO4 test,
# the reproduction check (PO1), write the report, and print every proof-obligation verdict.
# Takes about 4 minutes. Set PYTHON=python if your interpreter is not called python3.
set -e
cd "$(dirname "$0")"
PY=${PYTHON:-python3}
echo "[1/4] running study v1.4.0 ..."
$PY run_capsule.py spec/research_spec_v1.4.0.json results/v1.4.0 > /dev/null
echo "[2/4] held-out PO4 test (about 3 minutes) ..."
$PY heldout.py spec/research_spec_v1.4.0.json results/v1.4.0_heldout > /dev/null
echo "[3/4] reproduction check (PO1) ..."
$PY reproduce.py spec/research_spec_v1.4.0.json results/v1.4.0 > /dev/null
echo "[4/4] writing report ..."
$PY make_report.py results/v1.4.0 > /dev/null
$PY final_summary.py results/v1.4.0
