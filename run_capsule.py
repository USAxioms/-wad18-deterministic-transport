"""Execute one study: python3 run_capsule.py [spec_path] [output_dir]
Defaults: spec/research_spec.json -> results/v<spec_version>/"""
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from r3capsule import pipeline, spec  # noqa: E402


def main():
    sp = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "spec", "research_spec.json")
    ver = spec.load(sp).spec_version
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "results", "v" + ver)
    res = pipeline.run(ROOT, out, sp)
    print("study v" + ver + " executed; results in " + os.path.relpath(out, ROOT))
    for k, v in sorted(res["po"].items()):
        print("  " + k + ": " + v["status"])


if __name__ == "__main__":
    main()
