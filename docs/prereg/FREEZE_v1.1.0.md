# Freeze record: protocol v1.1.0

Written **before** the code that implements v1.1.0 existed and before any v1.1.0 execution.

- spec/research_spec_v1.1.0.json SHA-256: `0d89796a2d4f6441b6c16e08f24c6b6156387328df4b70ce597db52acb5836d1`
- parent spec/research_spec.json (v1.0.1) SHA-256: `29b701f225f07fb9e6c70d9232b4e945ab9694e20e3185acb61b5fdb8319586d`

Changes relative to v1.0.1, motivated only by defects the v1.0.1 study exposed:

1. **Margin-aware search.** The 5% margin moves from a post-hoc selection filter into the
   feasibility test used during search, and it applies to *all* methods equally. In v1.0.1,
   every dominating front design sat on a constraint, so the selection rule found none.
2. **R3 multiscale fixed point.** In v1.0.1, R3 stopped at a unit-step fixed point with 126 of
   1000 evaluations unused. A fixed point now means that a complete coarse-to-fine cycle gains
   nothing.
3. **Empty-archive focus.** The reference is infeasible under the tightened constraints
   (its C08 slack is exactly 0), so R3 needs a defined focus when it has no feasible design yet.

Unchanged: the model, every constant and theta, the grid, the budget (1000), the seeds, the
hypervolume reference, the selection rule and its 0.05 margin, and every acceptance rule.
The outcome will be reported whatever it is. The v1.0.1 study and its results stay unchanged in
the capsule.

Limitation: this freeze is self-attested within one working session. No external
timestamp authority was used.
