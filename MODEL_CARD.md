# Model card: reduced-order blanket surrogate

**Class:** REDUCED_ORDER_SURROGATE. These are 1-D parametric correlations, not Monte Carlo
neutron transport and not CFD. All constants are declared in `spec/research_spec.json`.
They are plausible orders of magnitude for a water-cooled, lithium-lead blanket slice
per m² of first wall, but they are **not** taken from qualified datasets. PO6 is therefore
NOT_ESTABLISHED by construction.

## Design vector d = (g, m, b, c, o)

| Var | Group | Range | Meaning |
|---|---|---|---|
| t_b | g | 0.30–0.60 m | breeding-zone thickness |
| e_li6 | b | 0.30–0.90 | Li-6 enrichment |
| t_mult | b | 0–0.08 m | optional multiplier layer |
| f_struct | m | 0.06–0.16 | stiffener fraction |
| f_cool | c | 0.010–0.050 | coolant flow-area fraction |
| d_h | g | 6–14 mm | tube inner diameter |

Operating conditions (o) are fixed: 15.5 MPa water at 295→328 °C and a 1 MW/m² neutron wall load.

## Correlations (all WAD-18)

- **Composition.** The tube-steel fraction is f_c·4t_w(D+t_w)/D². The breeder fraction is 1 − f_steel − f_c.
- **TBR.** TBR = T0·κ·M·(1−e^(−t_b/λ))·E(e)·P, where:
  - λ = λ0/f_breeder;
  - E(e) = e(1+K)/(e+K);
  - P = (1−β_s f_steel)(1−β_c f_c);
  - M = 1 + μ(1−e^(−t_m/λ_m)).
- **Shielding.** The attenuation exponent is t_b/0.25 + t_m/0.20 + t_shield/0.09, where t_shield is the remaining radial build.
- **Heat and flow.**
  - Heat: Q = W_n·ε·(1−e^(−(t_b+t_m)/λ_E)), with mass flow ṁ = Q/(c_p ΔT) and velocity v = ṁ/(ρ f_c t_b).
  - Pressure drop: Blasius friction f = 0.316·Re^(−1/4), giving Δp = f(L/D)ρv²/2 + K ρv²/2.
- **Temperatures.**
  - Heat transfer: Dittus–Boelter, Nu = 0.023 Re^(4/5) Pr^(2/5).
  - Wall temperature: T_wall = T_out + q_wall/h, with q_wall = q‴D/(4 f_c).
  - Conduction rise: ΔT = q‴ s²/(4k), with half-pitch s.
  - Peaking: q‴ = (2 + e)·Q/t_b.
- **Structure.** Hoop stress σ = pD/(2t_w). The stiffener minimum is 0.06 + 0.08·t_b, and the ligament is pitch − D − 2t_w.

## Known limitations (non-exhaustive)

- There is no spatial transport, no spectrum, and no nuclear-data library. TBR saturation lengths are assumed, not computed.
- The multiplier layer is generic, and its tritium inventory is a linear placeholder.
- Water moderation effects, Li-6 burn-up, and Pb(n,2n) multiplication are ignored.
- Uniform peaking is assumed, with no axial or poloidal power profile.
- There is no transient, LOCA, MHD, corrosion-rate, or irradiation-creep analysis.
- Low-temperature irradiation embrittlement of steel (relevant near 300 °C) is not represented.
- Tritium recovery appears only through the TBR ≥ 1.10 requirement. There is no permeation or inventory model.
- A plant-level net-electric claim is not supported; p_pump is reported only.

## Transport check (R11)

An integer 1-D multigroup S_N transport model (`r3capsule/transport.py`, `r3capsule/blanket_transport.py`),
using verified FENDL-3.2c data for all 21 nuclides, recomputes TBR for the same design vector. Its assumptions are
declared in `spec/transport_model.json`.

| Design | Surrogate | Slab, vacuum front | Slab, white front | **Cylinder (R12)** |
|---|---|---|---|---|
| Reference | 1.160 | 0.453 | 1.300 | **1.268** |
| v1.1.0 selected | 1.302 | 0.575 | 1.522 | **1.485** |
| v1.4.0 selected | 1.295 | 0.574 | 1.520 | **1.483** |

The cylindrical model (`r3capsule/cylinder.py`, integer-exact) puts the plasma chamber inside the blanket, so
front leakage re-enters physically. Its numerical uncertainty is 3.3%. All three designs meet TBR ≥ 1.155 by
more than that uncertainty, and the surrogate underestimates TBR by 8.5–12.7%.

What the check shows:
- Transport confirms the *direction* of the surrogate's design improvement.
- The surrogate *underestimates* both the absolute TBR and the size of the gain.
- The slab could not settle whether TBR ≥ 1.155 is met; the cylinder (R12) shows it is met for all three designs.

Transport-model limitations:
- 1-D geometry (slab, or infinite cylinder with toroidal curvature neglected); coverage is represented only by a
  factor (0.82, assumed).
- No first wall in either model.
- Free-gas thermal hydrogen; 293.6 K data.
- No gamma transport or heating.
- About 1.4% mesh uncertainty.

The surrogate remains the model used by the search. PO6 is still NOT_ESTABLISHED, since it needs 3-D Monte
Carlo and benchmark or experimental comparison.
