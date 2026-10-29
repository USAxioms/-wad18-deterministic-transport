"""Re-run a held-out test into a scratch directory and byte-compare with the record.
python3 heldout_repro.py [spec_path] [recorded_dir]"""
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import jsonio  # noqa: E402


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def main():
    sp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec", "research_spec_v1.2.0.json")
    rec = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "results", "v1.2.0_heldout")
    scratch = os.path.join(ROOT, "_repro_scratch_heldout")
    if os.path.exists(scratch):
        shutil.rmtree(scratch)
    subprocess.check_call([sys.executable, os.path.join(ROOT, "heldout.py"),
                           sp, scratch])
    rows = []
    for n in ("heldout_runs.jsonl", "heldout_summary.json"):
        a, b = sha(os.path.join(rec, n)), sha(os.path.join(scratch, n))
        rows.append({"file": n, "recorded_sha256": a, "rerun_sha256": b, "identical": a == b})
    shutil.rmtree(scratch)
    ok = all(r["identical"] for r in rows)
    jsonio.dump({"rows": rows, "byte_identical_rerun": ok}, os.path.join(rec, "heldout_reproduction.json"))
    print(os.path.basename(rec) + " reproduction: " + ("identical" if ok else "DIFFERENT"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
