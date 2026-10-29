"""Budgeted, cached, logged design evaluation shared by every search procedure."""
from . import model
from . import wad18 as w


class BudgetExhausted(Exception):
    pass


class Evaluator:
    def __init__(self, ctx, budget, theta=None, label=""):
        self.ctx = ctx
        self.budget = budget
        self.theta = theta if theta is not None else ctx.theta_nominal
        self.label = label
        self.cache = {}
        self.order = []          # keys in evaluation order
        self.domain_errors = 0

    @property
    def used(self):
        return len(self.order)

    def evaluate(self, key):
        if key in self.cache:
            return self.cache[key]
        if not self.ctx.in_grid(key):
            raise ValueError("design outside grid: " + str(key))
        if self.used >= self.budget:
            raise BudgetExhausted()
        rec = evaluate_once(self.ctx, key, self.theta)
        if rec["status"] != "OK":
            self.domain_errors += 1
        self.cache[key] = rec
        self.order.append(key)
        return rec


def evaluate_once(ctx, key, theta, margin=None):
    """margin None -> the spec's search margin; pass 0 for the declared limits."""
    if margin is None:
        margin = ctx.search_margin
    x = ctx.values(key)
    try:
        out = model.evaluate_physics(x, ctx.const, theta)
    except w.WadError as exc:
        return {"key": key, "status": exc.code, "feasible": False,
                "violation": w.WAD * 1000, "tbr": 0, "dp": 0, "outputs": None,
                "constraints": None, "n_violated": len(ctx.constraints)}
    cons, feas, viol = model.check_constraints(out, ctx.constraints, margin)
    return {"key": key, "status": "OK", "feasible": feas, "violation": viol,
            "tbr": out["tbr"], "dp": out["dp"], "outputs": out, "constraints": cons,
            "n_violated": sum(1 for c in cons if c["slack"] < margin)}
