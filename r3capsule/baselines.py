"""Conventional baselines under the same unique-evaluation budget:
NSGA-II (constrained domination, crowding distance) and uniform random search."""
from . import wad18 as w
from . import pareto
from .prng import SplitMix64
from .evaluator import Evaluator, BudgetExhausted

BIG = 1 << 300


def _better(a, b):
    """Deb's constrained domination: True if record a beats record b."""
    if a["feasible"] and not b["feasible"]:
        return True
    if b["feasible"] and not a["feasible"]:
        return False
    if not a["feasible"]:
        return a["violation"] < b["violation"]
    return pareto.dominates((a["tbr"], a["dp"]), (b["tbr"], b["dp"]))


def _sort(keys, cache):
    ranks = {}
    remaining = list(keys)
    r = 0
    while remaining:
        front = [k for k in remaining
                 if not any(_better(cache[o], cache[k]) for o in remaining if o != k)]
        for k in front:
            ranks[k] = r
        remaining = [k for k in remaining if k not in ranks]
        r += 1
    crowd = {k: 0 for k in keys}
    for r_ in set(ranks.values()):
        fr = [k for k in keys if ranks[k] == r_]
        for obj in ("tbr", "dp"):
            fr.sort(key=lambda k: (cache[k][obj], k))
            lo, hi = cache[fr[0]][obj], cache[fr[-1]][obj]
            crowd[fr[0]] = BIG
            crowd[fr[-1]] = BIG
            if hi > lo:
                for i in range(1, len(fr) - 1):
                    if crowd[fr[i]] < BIG:
                        crowd[fr[i]] += (cache[fr[i + 1]][obj] - cache[fr[i - 1]][obj]) * w.WAD // (hi - lo)
    return ranks, crowd


def _random_key(ctx, rng):
    return tuple(rng.below(n) for n in ctx.n)


def run_nsga2(ctx, seed, budget):
    p = ctx.nsga2
    rng = SplitMix64(seed)
    ev = Evaluator(ctx, budget, label="NSGA2-" + str(seed))
    pop = [ctx.reference_key]
    stop = None
    gens = 0
    try:
        ev.evaluate(ctx.reference_key)
        while len(pop) < p["population"]:
            k = _random_key(ctx, rng)
            ev.evaluate(k)
            if k not in pop:
                pop.append(k)
        stagnant = 0
        while True:
            gens += 1
            if gens > p["max_generations"]:
                stop = "MAX_GENERATIONS"
                break
            ranks, crowd = _sort(pop, ev.cache)

            def tour():
                a = pop[rng.below(len(pop))]
                b = pop[rng.below(len(pop))]
                if (ranks[a], -crowd[a], a) <= (ranks[b], -crowd[b], b):
                    return a
                return b
            kids = []
            used0 = ev.used
            while len(kids) < p["population"]:
                a, b = tour(), tour()
                child = []
                for i in range(len(ctx.n)):
                    g = a[i] if rng.bit() else b[i]
                    if rng.below(p["mutation_one_in"]) == 0:
                        d = rng.below(p["mutation_max_step"]) + 1
                        g = g + d if rng.bit() else g - d
                        g = max(0, min(ctx.n[i] - 1, g))
                    child.append(g)
                child = tuple(child)
                ev.evaluate(child)
                kids.append(child)
            stagnant = stagnant + 1 if ev.used == used0 else 0
            if stagnant >= p["stagnation_generations"]:
                stop = "STAGNATION"
                break
            union = sorted(set(pop) | set(kids))
            ranks, crowd = _sort(union, ev.cache)
            union.sort(key=lambda k: (ranks[k], -crowd[k], k))
            pop = union[: p["population"]]
    except BudgetExhausted:
        stop = "BUDGET"
    return {"evaluator": ev, "stop": stop, "generations": gens}


def run_random(ctx, seed, budget):
    rng = SplitMix64(seed)
    ev = Evaluator(ctx, budget, label="RANDOM-" + str(seed))
    draws = 0
    stop = None
    try:
        ev.evaluate(ctx.reference_key)
        while True:
            draws += 1
            if draws > budget * 1000:
                stop = "MAX_DRAWS"
                break
            ev.evaluate(_random_key(ctx, rng))
    except BudgetExhausted:
        stop = "BUDGET"
    return {"evaluator": ev, "stop": stop, "draws": draws}
