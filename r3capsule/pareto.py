"""Pareto dominance, archive, and exact 2-D hypervolume (maximise TBR, minimise dp)."""


def dominates(a, b):
    """a, b are (tbr, dp) integer pairs."""
    return a[0] >= b[0] and a[1] <= b[1] and (a[0] > b[0] or a[1] < b[1])


class Archive:
    """Mutually non-dominated set of feasible designs. Equal objective vectors:
    the first-inserted design is kept (deterministic)."""

    def __init__(self):
        self.items = {}

    def add(self, key, obj):
        for k, o in self.items.items():
            if dominates(o, obj) or o == obj:
                return False
        for k in [k for k, o in self.items.items() if dominates(obj, o)]:
            del self.items[k]
        self.items[key] = obj
        return True

    def sorted(self):
        return sorted(self.items.items(), key=lambda kv: (kv[1][1], kv[1][0], kv[0]))

    def check_invariants(self, cache):
        objs = list(self.items.items())
        for k, o in objs:
            rec = cache[k]
            if not rec["feasible"]:
                raise AssertionError("archive contains infeasible design")
            if (rec["tbr"], rec["dp"]) != o:
                raise AssertionError("archive objective mismatch")
        for i in range(len(objs)):
            for j in range(len(objs)):
                if i != j and dominates(objs[i][1], objs[j][1]):
                    raise AssertionError("archive not mutually non-dominated")
        return True


def front_from_records(records):
    arc = Archive()
    for rec in records:
        if rec["feasible"]:
            arc.add(rec["key"], (rec["tbr"], rec["dp"]))
    return arc


def hypervolume(points, tbr_ref, dp_ref):
    """Exact dimensionless HV in WAD: area dominated in (TBR - tbr_ref) x (dp_ref - dp)/dp_ref.

    Single final floor: HV = floor( sum_i dTBR_i * (dp_ref - dp_i) / dp_ref ).
    """
    pts = [p for p in points if p[0] > tbr_ref and p[1] < dp_ref]
    arc = Archive()
    for i, p in enumerate(pts):
        arc.add(i, p)
    nd = sorted(arc.items.values(), key=lambda p: (p[1], p[0]))
    num = 0
    prev = tbr_ref
    for tbr, dp in nd:
        if tbr > prev:
            num += (tbr - prev) * (dp_ref - dp)
            prev = tbr
    return num // dp_ref
