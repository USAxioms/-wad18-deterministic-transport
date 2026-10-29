"""Reduced-order multiphysics surrogate of a water-cooled liquid-breeder blanket slice.

Every operation is WAD-18 integer arithmetic. The correlations are declared
engineering approximations (see docs/MODEL_CARD.md); they are NOT validated
transport or CFD models.
"""
from . import wad18 as w

W = w.WAD


def evaluate_physics(x, c, th):
    t_b = x["t_b"]
    e = x["e_li6"]
    t_m = x["t_mult"]
    f_s = x["f_struct"]
    f_c = x["f_cool"]
    D = x["d_h"]
    tw = c["tube_wall"]

    # ---- composition
    f_tube = w.mul(f_c, w.div(w.mul_int(w.mul(tw, D + tw), 4), w.mul(D, D)))
    f_steel = f_s + f_tube
    f_breed = W - f_steel - f_c
    if f_breed <= 0:
        raise w.WadDomain("non-positive breeder fraction")

    # ---- neutronics (1-D saturation surrogate)
    lam = w.div(th["lambda0"], f_breed)
    capture = W - w.exp(-w.div(t_b, lam))
    enrich_eff = w.div(w.mul(e, W + c["k_enrich"]), e + c["k_enrich"])
    parasitic = w.mul(W - w.mul(c["beta_steel"], f_steel), W - w.mul(c["beta_cool"], f_c))
    mult = W + w.mul(th["mult_gain"], W - w.exp(-w.div(t_m, c["lambda_mult"])))
    tbr = w.mul(w.mul(w.mul(w.mul(w.mul(th["t0"], c["coverage"]), mult), capture),
                      enrich_eff), parasitic)

    # ---- shielding
    t_sh = c["radial_build"] - c["t_manifold"] - t_b - t_m
    expo = (w.div(t_b, c["lsh_breeder"]) + w.div(t_m, c["lsh_mult"]) +
            w.div(t_sh, c["lsh_shield"]))
    atten = w.exp(-expo)

    # ---- heat deposition and coolant flow
    eps = c["eps0"] + w.mul(c["eps_mult"], mult - W)
    cap_e = W - w.exp(-w.div(t_b + t_m, c["lambda_energy"]))
    q_total = w.mul(w.mul(w.mul(c["wall_load"], c["fw_area"]), eps), cap_e)
    mdot = w.div(q_total, w.mul(c["cp"], c["dT_cool"]))
    a_flow = w.mul(w.mul(f_c, t_b), c["module_width"])
    vel = w.div(mdot, w.mul(c["rho"], a_flow))
    re = w.div(w.mul(w.mul(c["rho"], vel), D), c["mu"])

    # ---- pressure drop (Blasius friction + form losses)
    fric = w.mul(th["fric_coeff"], w.pow_frac(re, -1, 4))
    dyn = w.div_int(w.mul(c["rho"], w.mul(vel, vel)), 2)
    dp = w.mul(fric, w.mul(w.div(c["channel_length"], D), dyn)) + w.mul(c["k_form"], dyn)

    # ---- heat transfer (Dittus-Boelter) and conduction
    pr = w.div(w.mul(c["mu"], c["cp"]), c["k_water"])
    nu = w.mul(w.mul(th["nu_coeff"], w.pow_frac(re, 4, 5)), w.pow_frac(pr, 2, 5))
    h = w.div(w.mul(nu, c["k_water"]), D)
    peak = c["peak0"] + w.mul(c["peak_enrich"], e)
    qv = w.div(w.mul(peak, q_total), w.mul(t_b, c["fw_area"]))
    q_wall = w.div(w.mul(qv, D), w.mul_int(f_c, 4))
    t_wall = c["T_out"] + w.div(q_wall, h)
    pitch = w.mul(D, w.sqrt(w.div(w.PI, w.mul_int(f_c, 4))))
    half = w.div_int(pitch, 2)
    dt_cond = w.div(w.mul(qv, w.mul(half, half)), w.mul_int(th["k_breeder"], 4))
    t_peak = t_wall + dt_cond

    # ---- structure, manufacturing, inventory
    sigma = w.div(w.mul(c["p_cool"], D), w.mul_int(tw, 2))
    ligament = pitch - D - w.mul_int(tw, 2)
    fs_min = c["fs_min0"] + w.mul(c["fs_min_slope"], t_b)
    inv_mult = w.mul(c["be_inventory_rate"], t_m)
    p_pump = w.div(w.mul(mdot, dp), w.mul(c["rho"], c["pump_eff"]))

    return {
        "tbr": tbr, "dp": dp,
        "f_tube": f_tube, "f_steel": f_steel, "f_breeder": f_breed,
        "lambda_breed": lam, "capture": capture, "enrich_eff": enrich_eff,
        "parasitic": parasitic, "mult_factor": mult,
        "t_shield": t_sh, "atten_exponent": expo, "attenuation": atten,
        "energy_mult": eps, "energy_capture": cap_e, "q_total": q_total,
        "mdot": mdot, "velocity": vel, "reynolds": re, "friction": fric,
        "prandtl": pr, "nusselt": nu, "h_conv": h, "peaking": peak,
        "q_vol_peak": qv, "q_wall": q_wall, "T_wall": t_wall, "pitch": pitch,
        "dT_cond": dt_cond, "T_peak": t_peak, "sigma_hoop": sigma,
        "ligament": ligament, "f_struct_min": fs_min,
        "f_struct_margin": f_s - fs_min, "f_struct_ratio": w.div(f_s, fs_min), "inv_mult": inv_mult, "p_pump": p_pump,
    }


def check_constraints(out, constraints, margin=0):
    """Returns (records, feasible, total_violation). Slack is normalised by |limit|
    (or used raw when the limit is zero); slack >= 0 means the declared limit is met.
    Feasibility requires slack >= margin for every constraint (margin 0 = declared limits);
    violation is the summed shortfall below the margin."""
    recs = []
    feasible = True
    violation = 0
    for c in constraints:
        val = out[c["output"]]
        lim = c["limit"]
        raw = val - lim if c["sense"] == "ge" else lim - val
        slack = w.div(raw, abs(lim)) if lim != 0 else raw
        ok = slack >= 0
        if slack < margin:
            feasible = False
            violation += margin - slack
        recs.append({"name": c["name"], "value": val, "limit": lim,
                     "sense": c["sense"], "slack": slack, "ok": ok})
    return recs, feasible, violation
