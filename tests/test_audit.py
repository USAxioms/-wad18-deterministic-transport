import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "audit"))
import zero_float_audit as zfa  # noqa: E402

BAD = {
    "F1": "x = 0" + ".5\n",
    "F2": "y = fl" + "oat(3)\n",
    "F3": "z = 7 " + "/" + " 2\n",
    "F4": "q = 2 *" + "* -1\n",
    "F5": "import ma" + "th\n",
    "F6": "import json\nd = json.loads('1')\n",
    "F7": "s = '{:.3" + "f}'\n",
    "F8": "r = ro" + "und(7)\n",
}


def test_audit_detects_each_violation_class():
    path = os.path.join(HERE, "_audit_probe.txt")
    try:
        for code, src in BAD.items():
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(src)
            got = [v["code"] for v in zfa.audit_source(path)]
            assert code in got, (code, got)
    finally:
        if os.path.exists(path):
            os.remove(path)


def test_audit_accepts_integer_code():
    path = os.path.join(HERE, "_audit_probe_ok.txt")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            fh.write("a = 10 ** 18\nb = 7 // 2\nc = divmod(9, 4)\nimport json\nd = json.loads('1', parse_float=None)\n")
        assert zfa.audit_source(path) == []
    finally:
        if os.path.exists(path):
            os.remove(path)
