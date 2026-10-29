"""Print the combined proof-obligation verdicts of a study: python3 final_summary.py results/v1.4.0"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import jsonio  # noqa: E402


def main():
    rd = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results", "v1.4.0")
    rep = jsonio.load(os.path.join(rd, "CAPSULE_REPORT.json"))
    print("")
    print("Proof obligations (" + os.path.basename(rd) + "):")
    for k, v in sorted(rep["proof_obligations"].items()):
        print("  " + k.ljust(30) + v["status"])
    print("")
    print("PO6 needs comparison with experimental data; no run can pass it here.")
    print("Full report: " + os.path.join(os.path.relpath(rd, ROOT), "REPORT.md"))


if __name__ == "__main__":
    main()
