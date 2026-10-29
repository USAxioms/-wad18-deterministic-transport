"""Minimal float-free test runner: python3 tests/run_tests.py [report.json]"""
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

MODULES = ["test_wad18", "test_prng_jsonio", "test_model", "test_pareto", "test_search", "test_audit", "test_v110", "test_v120", "test_v140", "test_ndata", "test_transport", "test_cylinder"]


def main():
    passed = 0
    failed = []
    per_module = {}
    for mname in MODULES:
        mod = __import__(mname)
        names = sorted(n for n in dir(mod) if n.startswith("test_"))
        mp = 0
        for n in names:
            try:
                getattr(mod, n)()
                passed += 1
                mp += 1
            except Exception:
                failed.append(mname + "." + n)
                traceback.print_exc()
        per_module[mname] = [mp, len(names)]
    for m, (p, t) in per_module.items():
        print(m + ": " + str(p) + "/" + str(t))
    print("passed " + str(passed) + "  failed " + str(len(failed)))
    for f in failed:
        print("  FAILED " + f)
    if len(sys.argv) > 1:
        from r3capsule import jsonio
        jsonio.dump({"passed": passed, "failed": len(failed), "failures": failed,
                     "per_module_passed_total": per_module}, sys.argv[1])
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
