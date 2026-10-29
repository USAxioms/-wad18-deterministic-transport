"""Load and validate the research specification; grid <-> design conversion."""
from . import wad18 as w
from . import jsonio


class SpecError(ValueError):
    pass


class Context:
    """Parsed, validated specification. All numbers are WAD ints or plain ints."""

    def __init__(self, raw):
        self.raw = raw
        ds = raw["design_space"]
        self.order = tuple(ds["order"])
        self.lo = []
        self.step = []
        self.n = []
        for name in self.order:
            v = ds["variables"][name]
            self.lo.append(w.parse(v["lo"]))
            self.step.append(w.parse(v["step"]))
            self.n.append(v["n"])
        self.const = {k: w.parse(v["value"]) for k, v in raw["constants"].items()}
        self.theta_nominal = {}
        self.theta_rel = {}
        for k, v in raw["theta"].items():
            if k.startswith("_"):
                continue
            self.theta_nominal[k] = w.parse(v["nominal"])
            self.theta_rel[k] = w.parse(v["rel"])
        self.constraints = []
        for c in raw["constraints"]:
            self.constraints.append({"name": c["name"], "output": c["output"],
                                     "sense": c["sense"], "limit": w.parse(c["limit"])})
        ep = raw["evaluation_protocol"]
        self.budget = ep["budget_unique_evaluations"]
        self.hv_ref_tbr = w.parse(ep["hypervolume_reference"]["tbr"])
        self.hv_ref_dp = w.parse(ep["hypervolume_reference"]["dp"])
        self.seeds = list(ep["baseline_seeds"])
        self.nsga2 = dict(ep["nsga2"])
        self.r3 = dict(ep["r3"])
        self.selection_margin = w.parse(ep["selection_margin"])
        # v1.1.0: feasibility margin applied during search (0 reproduces v1.0.x)
        self.search_margin = w.parse(ep.get("search_constraint_margin", "0"))
        self.spec_version = raw["metadata"]["spec_version"]
        self.reference_key = self.key_from_values(
            {k: w.parse(s) for k, s in raw["reference_design"].items()})

    # ---------------------------------------------------------------- grid
    def values(self, key):
        return {name: self.lo[i] + key[i] * self.step[i] for i, name in enumerate(self.order)}

    def in_grid(self, key):
        if len(key) != len(self.order):
            return False
        for i, k in enumerate(key):
            if type(k) is not int or k < 0 or k >= self.n[i]:
                return False
        return True

    def key_from_values(self, vals):
        key = []
        for i, name in enumerate(self.order):
            q, r = divmod(vals[name] - self.lo[i], self.step[i])
            if r != 0 or q < 0 or q >= self.n[i]:
                raise SpecError("value of " + name + " is not on the declared grid")
            key.append(q)
        return tuple(key)

    def move(self, key, i, delta):
        k = list(key)
        k[i] = max(0, min(self.n[i] - 1, k[i] + delta))
        return tuple(k)

    def theta_corner(self, mask):
        """mask bit j set -> parameter j at +rel, else -rel (parameters in sorted order)."""
        th = {}
        for j, name in enumerate(sorted(self.theta_nominal)):
            nom = self.theta_nominal[name]
            d = w.mul(nom, self.theta_rel[name])
            th[name] = nom + d if (mask >> j) & 1 else nom - d
        return th


def load(path):
    return Context(jsonio.load(path))


def validate(ctx):
    """Method-level checks: completeness, consistency, declared stopping/acceptance rules.

    Returns a list of check records; raises SpecError on any failed mandatory check.
    """
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": detail})
        if not ok:
            raise SpecError(name + ": " + detail)

    raw = ctx.raw
    chk("design_order_matches_variables",
        sorted(ctx.order) == sorted(raw["design_space"]["variables"]))
    for i, name in enumerate(ctx.order):
        chk("grid_positive_step_" + name, ctx.step[i] > 0)
        chk("grid_size_" + name, ctx.n[i] >= 2)
    chk("reference_on_grid", ctx.in_grid(ctx.reference_key), str(ctx.reference_key))
    names = [c["name"] for c in ctx.constraints]
    chk("constraint_names_unique", len(names) == len(set(names)))
    chk("constraint_senses_valid", all(c["sense"] in ("ge", "le") for c in ctx.constraints))
    chk("theta_rel_in_open_unit_interval",
        all(0 < r < w.WAD for r in ctx.theta_rel.values()))
    chk("theta_corner_count_is_64", len(ctx.theta_nominal) == 6)
    chk("budget_positive", ctx.budget > 0)
    chk("baseline_seeds_present", len(ctx.seeds) >= 3)
    chk("hv_reference_consistent_with_constraints",
        ctx.hv_ref_tbr == next(c["limit"] for c in ctx.constraints if c["output"] == "tbr") and
        ctx.hv_ref_dp == next(c["limit"] for c in ctx.constraints if c["output"] == "dp"))
    acc = raw["evaluation_protocol"]["acceptance"]
    for po in ("PO1_reproducible_execution", "PO2_constraint_satisfaction",
               "PO3_engineering_improvement", "PO4_contribution_of_R3",
               "PO5_robustness", "PO6_physical_relevance"):
        chk("acceptance_rule_declared_" + po, po in acc)
    chk("stopping_rules_declared",
        "max_iterations" in ctx.r3 and "max_generations" in ctx.nsga2)
    return checks
