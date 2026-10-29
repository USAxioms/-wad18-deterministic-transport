"""Build or verify MANIFEST.json (SHA-256 of every capsule file).

python3 manifest.py build | verify
"""
import hashlib
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
from r3capsule import jsonio, CAPSULE_NAME, CAPSULE_VERSION  # noqa: E402

SKIP_DIRS = {"__pycache__", "_repro_scratch"}


def files():
    out = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if d not in SKIP_DIRS and not d.startswith("."))
        for fn in sorted(fns):
            rel = os.path.relpath(os.path.join(dp, fn), ROOT).replace(os.sep, "/")
            if rel != "MANIFEST.json" and not fn.endswith(".pyc"):
                out.append(rel)
    return out


def sha(rel):
    with open(os.path.join(ROOT, rel), "rb") as fh:
        data = fh.read()
    return hashlib.sha256(data).hexdigest(), len(data)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "verify"
    path = os.path.join(ROOT, "MANIFEST.json")
    if mode == "build":
        ent = []
        for rel in files():
            h, n = sha(rel)
            ent.append({"path": rel, "sha256": h, "bytes": n})
        jsonio.dump({"capsule": CAPSULE_NAME, "version": CAPSULE_VERSION,
                     "file_count": len(ent), "files": ent}, path)
        print("manifest: " + str(len(ent)) + " files")
        return 0
    man = jsonio.load(path)
    bad = []
    listed = set()
    for e in man["files"]:
        listed.add(e["path"])
        if not os.path.exists(os.path.join(ROOT, e["path"])):
            bad.append("missing " + e["path"])
        elif sha(e["path"])[0] != e["sha256"]:
            bad.append("hash mismatch " + e["path"])
    for rel in files():
        if rel not in listed:
            bad.append("unlisted " + rel)
    print("manifest verify: " + str(len(man["files"])) + " files, " + str(len(bad)) + " problems")
    for b in bad:
        print("  " + b)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
