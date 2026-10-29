"""Zero-floating-point audit.

Source scope: every .py file in the capsule. A violation is any of:
  F1 float or complex literal
  F2 reference to the names float / complex
  F3 true division operator '/' or '/=' (Python true division always yields float)
  F4 '**' whose exponent is not a non-negative integer literal (int ** negative int -> float)
  F5 import of a float-producing or approximate-numeric module
     (math, cmath, decimal, fractions, statistics, random, numpy, time)
  F6 json.load/json.loads without a parse_float hook
  F7 float-style format specification in a string (fixed, exponent, general or percent
     presentation types in str.format or printf-style specs)
  F8 call to round()

Output scope: every .json/.jsonl file under results/ (recursively), except this audit's own report
(which is checked after it is written, so the result never depends on a prior run), is parsed with a hook that
raises on any floating-point token, NaN, or Infinity.

Out of scope (stated, not hidden): the CPython interpreter and its standard
library internals; this capsule contains no compiled binaries.

Usage: python3 audit/zero_float_audit.py [results_dir]
"""
import ast
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANNED_MODULES = {"math", "cmath", "decimal", "fractions", "statistics", "random", "numpy", "time"}
FMT_RE = re.compile(r"(\{[^{}]*:[^{}]*[eEfFgG%]\}|%[-+ 0#]*\d*(\.\d+)?[eEfFgG])")


def audit_source(path):
    with open(path, "r", encoding="utf-8") as fh:
        src = fh.read()
    tree = ast.parse(src, filename=path)
    v = []

    def add(node, code, msg):
        v.append({"file": os.path.relpath(path, ROOT), "line": getattr(node, "lineno", 0),
                  "code": code, "detail": msg})

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant):
            if type(node.value).__name__ in ("float", "complex"):
                add(node, "F1", "float/complex literal")
            elif type(node.value) is str and FMT_RE.search(node.value):
                add(node, "F7", "float-style format spec in string")
        elif isinstance(node, ast.Name) and node.id in ("float", "complex"):
            add(node, "F2", "reference to " + node.id)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            add(node, "F3", "true division '/'")
        elif isinstance(node, ast.AugAssign) and isinstance(node.op, ast.Div):
            add(node, "F3", "true division '/='")
        elif isinstance(node, (ast.BinOp, ast.AugAssign)) and isinstance(node.op, ast.Pow):
            r = node.right if isinstance(node, ast.BinOp) else node.value
            if not (isinstance(r, ast.Constant) and type(r.value) is int and r.value >= 0):
                add(node, "F4", "'**' with non-literal or negative exponent")
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in BANNED_MODULES:
                    add(node, "F5", "import " + a.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and node.module.split(".")[0] in BANNED_MODULES:
                add(node, "F5", "from " + node.module + " import")
        elif isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name) and f.id == "round":
                add(node, "F8", "round()")
            if (isinstance(f, ast.Attribute) and f.attr in ("load", "loads")
                    and isinstance(f.value, ast.Name) and f.value.id == "json"):
                if not any(k.arg == "parse_float" for k in node.keywords):
                    add(node, "F6", "json." + f.attr + " without parse_float hook")
    return v


class _FloatToken(ValueError):
    pass


def _reject(tok):
    raise _FloatToken(tok)


def audit_output(path):
    v = []
    with open(path, "r", encoding="utf-8") as fh:
        text = fh.read()
    docs = text.splitlines() if path.endswith(".jsonl") else [text]
    for i, d in enumerate(docs):
        if not d.strip():
            continue
        try:
            json.loads(d, parse_float=_reject, parse_constant=_reject)
        except _FloatToken as exc:
            v.append({"file": os.path.relpath(path, ROOT), "line": i + 1, "code": "O1",
                      "detail": "floating-point token " + str(exc)})
    return v


SELF_OUTPUT = "zero_float_audit.json"


def run(results_dir):
    src_files = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = sorted(d for d in dns if not d.startswith(".") and d != "__pycache__")
        for fn in sorted(fns):
            if fn.endswith(".py"):
                src_files.append(os.path.join(dp, fn))
    out_files = []
    for dp, dns, fns in os.walk(results_dir):
        dns.sort()
        for fn in sorted(fns):
            if fn == SELF_OUTPUT and dp == results_dir:
                continue    # own report: excluded so the result does not depend on a prior run
            if fn.endswith(".json") or fn.endswith(".jsonl"):
                out_files.append(os.path.join(dp, fn))
    violations = []
    for f in src_files:
        violations += audit_source(f)
    for f in out_files:
        violations += audit_output(f)
    return {
        "python_files_inspected": len(src_files),
        "output_files_inspected": len(out_files),
        "compiled_binaries_in_capsule": 0,
        "violations": violations,
        "violation_count": len(violations),
        "certified_zero_float": len(violations) == 0,
        "scope_note": "Capsule source and generated outputs, excluding this report itself (it is checked after writing). CPython interpreter and stdlib internals are outside scope.",
        "files": [os.path.relpath(f, ROOT) for f in src_files + out_files],
    }


def main():
    rd = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "results")
    rep = run(rd)
    sys.path.insert(0, ROOT)
    from r3capsule import jsonio
    jsonio.dump(rep, os.path.join(rd, SELF_OUTPUT))
    self_violations = audit_output(os.path.join(rd, SELF_OUTPUT))
    if self_violations:
        print("audit report itself failed its own output check")
        sys.exit(1)
    print("python files: " + str(rep["python_files_inspected"]) +
          "  output files: " + str(rep["output_files_inspected"]) +
          "  violations: " + str(rep["violation_count"]) +
          "  certified_zero_float: " + str(rep["certified_zero_float"]).lower())
    for x in rep["violations"]:
        print("  " + x["file"] + ":" + str(x["line"]) + " " + x["code"] + " " + x["detail"])
    return 0 if rep["certified_zero_float"] else 1


if __name__ == "__main__":
    sys.exit(main())
