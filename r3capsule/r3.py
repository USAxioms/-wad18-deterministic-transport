"""Russell Recursive Refinement (R3 = I o V o F o A) applied to the blanket design grid.

A  Analyze : select focus designs (front extremes and the largest hypervolume gap,
             or v1.2.0 option: the largest exclusive-HV contributors),
             identify binding constraints, rank move directions by recorded success.
F  Refine  : propose coordinate moves at the current step, pattern extrapolation of
             each focus design's last successful move, and repair-combinations for
             promising designs that violate exactly one constraint.
V  Validate: grid/budget invariants, full constraint evaluation, archive admission
             only for feasible non-dominated designs, archive invariant check.
I  Iterate : keep step on hypervolume gain; otherwise halve steps; at unit steps with
             the whole front as focus and no gain, Phi(A) = A (fixed point) -> stop.
"""
from . import pareto
from .evaluator import Evaluator, BudgetExhausted
from .prng import SplitMix64
from . import wad18 as w


def _focus(front, all_points):
    if all_points or len(front) <= 3:
        return [k for k, _ in front]
    keys = {front[0][0], front[-1][0]}
    best_gap = -1
    best_pair = None
    for i in range(1, len(front)):
        (_, (t0, d0)), (_, (t1, d1)) = front[i - 1], front[i]
        gap = (t1 - t0) * (d1 - d0)
        if gap > best_gap:
            best_gap = gap
            best_pair = (front[i - 1][0], front[i][0])
    keys.update(best_pair)
    return sorted(keys)


def _focus_contrib(front, k, tbr_ref, dp_ref):
    """v1.2.0: extremes plus the k designs with the largest exclusive HV contribution."""
    if len(front) <= k + 2:
        return [key for key, _ in front]
    contrib = []
    n = len(front)
    for i, (key, (t, d)) in enumerate(front):
        t_prev = front[i - 1][1][0] if i > 0 else tbr_ref
        d_next = front[i + 1][1][1] if i < n - 1 else dp_ref
        contrib.append(((t - t_prev) * (d_next - d), key))
    keys = {front[0][0], front[-1][0]}
    for _, key in sorted(contrib, key=lambda c: (-c[0], c[1]))[:k]:
        keys.add(key)
    return sorted(keys)


def _lhs(ctx, n, seed):
    """v1.2.0: deterministic Latin-hypercube sample of n grid designs."""
    rng = SplitMix64(seed)
    cols = []
    for i, size in enumerate(ctx.n):
        perm = list(range(n))
        for j in range(n - 1, 0, -1):
            r = rng.below(j + 1)
            perm[j], perm[r] = perm[r], perm[j]
        cols.append([(p * size + rng.below(size)) // n for p in perm])
    return [tuple(cols[i][j] for i in range(len(ctx.n))) for j in range(n)]


def run(ctx, budget):
    ev = Evaluator(ctx, budget, label="R3")
    arc = pareto.Archive()
    nvar = len(ctx.order)
    margin = ctx.selection_margin
    step = [max(1, (n - 1) // ctx.r3["initial_step_divisor"]) for n in ctx.n]
    succ = {(i, s): 0 for i in range(nvar) for s in (1, -1)}
    tries = {(i, s): 0 for i in range(nvar) for s in (1, -1)}
    last_vec = {}
    iterations = []
    stop = None

    ref = ev.evaluate(ctx.reference_key)
    if ref["feasible"]:
        arc.add(ref["key"], (ref["tbr"], ref["dp"]))
    hv = pareto.hypervolume(list(arc.items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)

    restart = bool(ctx.r3.get("restart_on_fixed_point", False))
    focus_mode = ctx.r3.get("focus_mode", "extremes_gap")
    focus_k = ctx.r3.get("focus_k", 0)
    halve_below = w.parse(ctx.r3.get("halve_when_relative_gain_below", "0"))
    n_init = ctx.r3.get("init_lhs_points", 0)
    escalate = bool(ctx.r3.get("escalate", False))
    pair_cap = ctx.r3.get("pair_cap", 60)
    recombine_n = ctx.r3.get("recombine_n", 20)
    erng = SplitMix64(ctx.r3.get("init_lhs_seed", 0) * 1000003 + 999331)
    iterations_escalated = []
    inf_focus = ctx.r3.get("infeasible_focus", 0)
    inf_seen = set()
    esc_on_no_gain = ctx.r3.get("escalate_trigger", "exhausted") == "no_gain"
    prev_no_gain = False
    init_step = list(step)
    cycle_gain = False
    cycles = 1
    it = 0
    try:
        # v1.2.0 option: deterministic Latin-hypercube seeding (inside budget accounting)
        for key in (_lhs(ctx, n_init, ctx.r3.get("init_lhs_seed", 0)) if n_init else []):
            rec = ev.evaluate(key)
            if rec["feasible"]:
                arc.add(key, (rec["tbr"], rec["dp"]))
        hv = pareto.hypervolume(list(arc.items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)
        while True:
            it += 1
            if it > ctx.r3["max_iterations"]:
                stop = "MAX_ITERATIONS"
                break
            used0 = ev.used
            # ---------------- A: analyze
            unit = all(s == 1 for s in step)
            front = arc.sorted()
            if front and focus_mode == "contrib" and not unit:
                focus = _focus_contrib(front, focus_k, ctx.hv_ref_tbr, ctx.hv_ref_dp)
            elif front:
                focus = _focus(front, unit)
            else:
                # v1.1.0 rule (b): no feasible design yet -> least-violation design
                focus = [min(ev.cache, key=lambda k: (ev.cache[k]["violation"], k))]
            if inf_focus and not unit:
                # v1.3.0 option: also focus the least-violation infeasible designs not yet
                # focused, so several near-feasible basins are refined (each design once)
                cand = sorted((ev.cache[k]["violation"], k) for k in ev.cache
                              if ev.cache[k]["status"] == "OK" and not ev.cache[k]["feasible"]
                              and k not in inf_seen)
                extra = [k for _, k in cand[:inf_focus]]
                inf_seen.update(extra)
                focus = list(focus) + extra
            binding = {}
            for k in focus:
                cons = ev.cache[k]["constraints"] or []
                binding[str(list(k))] = [c["name"] for c in cons if c["slack"] < margin]
            dirs = sorted(succ, key=lambda m: (-succ[m], tries[m], m[0], -m[1]))

            # ---------------- F: refine
            proposals = []
            for k in focus:
                for (i, s) in dirs:
                    child = ctx.move(k, i, s * step[i])
                    if child != k:
                        proposals.append((k, child, (i, s)))
                vec = last_vec.get(k)
                if vec is not None:
                    child = tuple(max(0, min(ctx.n[j] - 1, k[j] + vec[j])) for j in range(nvar))
                    if child != k:
                        proposals.append((k, child, None))

            # v1.3.0 option: neighbourhood escalation. When every single-coordinate
            # proposal is already evaluated, escalate to coupled two-coordinate moves,
            # then to recombination of front designs (before any random re-seed).
            if escalate:
                fresh = sum(1 for _, c, _ in proposals if c not in ev.cache)
                if fresh == 0 or (esc_on_no_gain and prev_no_gain):
                    pairs = []
                    for k in focus:
                        for a in range(len(dirs)):
                            for b in range(a + 1, len(dirs)):
                                (i, s), (j, t) = dirs[a], dirs[b]
                                if i == j:
                                    continue
                                c = ctx.move(ctx.move(k, i, s * step[i]), j, t * step[j])
                                if c != k and c not in ev.cache:
                                    pairs.append((k, c, None))
                    pairs = pairs[:pair_cap]
                    proposals.extend(pairs)
                    if not pairs and len(front) >= 2:
                        keys = [kk for kk, _ in front]
                        for _ in range(recombine_n):
                            a = keys[erng.below(len(keys))]
                            b = keys[erng.below(len(keys))]
                            c = list(a[q] if erng.below(2) == 0 else b[q] for q in range(nvar))
                            q = erng.below(nvar)
                            c[q] = max(0, min(ctx.n[q] - 1, c[q] + erng.below(3) - 1))
                            c = tuple(c)
                            if c not in ev.cache:
                                proposals.append((a, c, None))
                    iterations_escalated.append(it)

            # ---------------- V: validate
            accepted = 0
            promising = []
            for parent, child, mv in proposals:
                if child in ev.cache:
                    continue
                rec = ev.evaluate(child)
                ok = rec["feasible"] and arc.add(child, (rec["tbr"], rec["dp"]))
                if mv is not None:
                    tries[mv] += 1
                    if ok:
                        succ[mv] += 1
                if ok:
                    accepted += 1
                    last_vec[child] = tuple(child[j] - parent[j] for j in range(nvar))
                elif rec["status"] == "OK" and rec["n_violated"] == 1:
                    p = ev.cache[parent]
                    if p["status"] == "OK" and pareto.dominates((rec["tbr"], rec["dp"]), (p["tbr"], p["dp"])):
                        promising.append((child, mv))
            repairs = 0
            for child, mv in promising[: ctx.r3["repair_limit_per_iteration"]]:
                moved = mv[0] if mv is not None else -1
                for j in range(nvar):
                    if j == moved:
                        continue
                    for s in (1, -1):
                        c2 = ctx.move(child, j, s)
                        if c2 == child or c2 in ev.cache:
                            continue
                        rec = ev.evaluate(c2)
                        repairs += 1
                        if rec["feasible"] and arc.add(c2, (rec["tbr"], rec["dp"])):
                            accepted += 1
                            last_vec[c2] = tuple(c2[q] - child[q] for q in range(nvar))
            arc.check_invariants(ev.cache)
            new_hv = pareto.hypervolume(list(arc.items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)
            if new_hv < hv:
                raise AssertionError("hypervolume decreased: archive invariant violated")

            # ---------------- I: iterate
            gained = new_hv > hv
            iterations.append({
                "iteration": it, "step": list(step), "unit_step": unit,
                "focus": [list(k) for k in focus], "binding_constraints": binding,
                "proposals": len(proposals), "evaluations": ev.used - used0,
                "repair_evaluations": repairs, "accepted": accepted,
                "archive_size": len(arc.items), "hv": new_hv, "hv_gain": new_hv - hv,
                "evaluations_total": ev.used,
            })
            hv = new_hv
            prev_no_gain = not gained
            if gained:
                cycle_gain = True
                # v1.2.0: diminishing returns at this scale -> refine sooner
                if (halve_below and not unit and
                        iterations[-1]["hv_gain"] * w.WAD < halve_below * new_hv):
                    step = [max(1, s // 2) for s in step]
                    iterations[-1]["refined_on_small_gain"] = True
                continue
            if unit:
                if restart and cycle_gain:
                    # v1.1.0 rule (a): new coarse-to-fine cycle
                    step = list(init_step)
                    cycle_gain = False
                    cycles += 1
                    iterations[-1]["restart_cycle"] = cycles
                    continue
                reseed = ctx.r3.get("reseed_on_fixed_point", 0)
                if reseed:
                    # v1.2.0 option: a local fixed point is not global -> new LHS batch,
                    # reset scales, continue until the budget is exhausted
                    cycles += 1
                    batch = _lhs(ctx, reseed, ctx.r3.get("init_lhs_seed", 0) * 1000003 + cycles)
                    iterations[-1]["reseed_cycle"] = cycles
                    for key in batch:
                        rec = ev.evaluate(key)
                        if rec["feasible"]:
                            arc.add(key, (rec["tbr"], rec["dp"]))
                    hv = pareto.hypervolume(list(arc.items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)
                    step = list(init_step)
                    cycle_gain = False
                    continue
                stop = "FIXED_POINT"
                break
            step = [max(1, s // 2) for s in step]
    except BudgetExhausted:
        arc.check_invariants(ev.cache)
        hv = pareto.hypervolume(list(arc.items.values()), ctx.hv_ref_tbr, ctx.hv_ref_dp)
        iterations.append({"iteration": it, "stopped": "BUDGET", "archive_size": len(arc.items),
                           "hv": hv, "evaluations_total": ev.used})
        stop = "BUDGET"
    return {"evaluator": ev, "archive": arc, "iterations": iterations, "stop": stop,
            "escalated_iterations": iterations_escalated,
            "direction_success": {str(k[0]) + ("+" if k[1] > 0 else "-"): [succ[k], tries[k]]
                                  for k in sorted(succ)}}
