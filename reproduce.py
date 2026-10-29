"""PO1 check: re-execute one study into a scratch directory and compare every
pipeline result file byte-for-byte (SHA-256) with the recorded results.

python3 reproduce.py <spec_path> <results_dir>
"""
import hashlib
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import pipeline, jsonio  # noqa: E402

PIPELINE_FILES = ["00_environment.json", "01_spec_validation.json", "02_frozen_protocol.json",
                  "03_reference_evaluation.json", "04_r3_evaluations.jsonl", "05_r3_iterations.json",
                  "06_baseline_evaluations.jsonl", "07_comparison.json", "08_selected_candidate.json",
                  "11_output_checks.json", "12_proof_obligations.json", "13_front_diagnostics.json"]
OPTIONAL = ["09_uq_corners.json", "10_sensitivity.json"]


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    sp = sys.argv[1]
    res = sys.argv[2]
    scratch = os.path.join(ROOT, "_repro_scratch")
    if os.path.exists(scratch):
        shutil.rmtree(scratch)
    pipeline.run(ROOT, scratch, sp)
    rows = []
    names = PIPELINE_FILES + [f for f in OPTIONAL if os.path.exists(os.path.join(res, f))
                              or os.path.exists(os.path.join(scratch, f))]
    for n in names:
        a = os.path.join(res, n)
        b = os.path.join(scratch, n)
        ha = sha(a) if os.path.exists(a) else None
        hb = sha(b) if os.path.exists(b) else None
        rows.append({"file": n, "recorded_sha256": ha, "rerun_sha256": hb,
                     "identical": ha is not None and ha == hb})
    shutil.rmtree(scratch)
    ok = all(r["identical"] for r in rows)
    rep = {"files_compared": len(rows), "identical": sum(1 for r in rows if r["identical"]),
           "byte_identical_rerun": ok,
           "PO1_status": "PASS" if ok else "FAIL",
           "scope": "Same-machine re-execution by the capsule itself. Independent third-party reproduction is a separate step not performed here.",
           "rows": rows}
    jsonio.dump(rep, os.path.join(res, "15_reproduction_check.json"))
    print(os.path.relpath(res, ROOT) + " reproduction: " + str(rep["identical"]) + "/" + str(len(rows)) +
          " files byte-identical -> PO1 " + rep["PO1_status"])
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
