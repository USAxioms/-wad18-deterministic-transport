# WAD-18 arithmetic specification (r3capsule/wad18.py)

- **Representation.** A WAD value is an int X representing X·10⁻¹⁸. Operands must be exact `int`, and `bool` is rejected.
- **Rounding.** Every inexact primitive floors toward −∞. Exact variants raise NON_EXACT instead of rounding.
- **Bounds.** Results must lie in [−2²⁵⁵, 2²⁵⁵−1]; otherwise the operation raises OVERFLOW. Intermediates inside a primitive are exact.
- **Errors.** The error codes are DIV_ZERO, OVERFLOW, NON_EXACT, DOMAIN, and PARSE.
- **Roots.** `iroot(n,k)` uses integer Newton iteration, and its postcondition r^k ≤ n < (r+1)^k is checked on every call.
- **Fractional powers.** `pow_frac(x,p,q)` = floor(x^(p/q)) with a single exact floor. For negative p it computes iroot(W^(|p|+q) // X^|p|, q).
- **Exponential.** `exp` uses range reduction by ln2 at 10⁻³⁶, a Taylor series with truncating terms, and exact scaling by 2^k, followed by a final floor. It matches e, e⁻¹, and e² to the last of 18 digits.
  - Arguments below −42 return 0.
  - Arguments above 130 raise OVERFLOW.
