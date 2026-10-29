"""
wad18.py -- WAD-18 integer-exact fixed-point arithmetic.

A WAD value is a Python int X that represents the real number X * 10^-18.

Rules (normative for this capsule):
  * Operands must be exact Python ints (bool and every non-int type are rejected).
  * Every inexact primitive rounds toward negative infinity (floor).
  * Every *result* must lie in the signed 256-bit range; otherwise OVERFLOW.
    Intermediates inside a primitive are exact unbounded integers.
  * Exact variants (mul_exact, div_exact, parse) raise NON_EXACT instead of rounding.
  * Division by zero raises DIV_ZERO. Out-of-domain inputs raise DOMAIN.
  * No floating-point value is created, consumed, or returned anywhere.
"""

WAD = 10 ** 18
DECIMALS = 18
INT256_MAX = (1 << 255) - 1
INT256_MIN = -(1 << 255)


class WadError(ArithmeticError):
    code = "WAD_ERROR"


class WadOverflow(WadError):
    code = "OVERFLOW"


class WadDivZero(WadError):
    code = "DIV_ZERO"


class WadNonExact(WadError):
    code = "NON_EXACT"


class WadDomain(WadError):
    code = "DOMAIN"


class WadParse(WadError):
    code = "PARSE"


def _req_int(*xs):
    for x in xs:
        if type(x) is not int:
            raise TypeError("WAD-18 operands must be exact int, got " + type(x).__name__)


def _bound(x):
    if x > INT256_MAX or x < INT256_MIN:
        raise WadOverflow("result outside signed 256-bit range")
    return x


def ipow(base, exponent):
    """Exact integer power for a non-negative integer exponent."""
    _req_int(base, exponent)
    if exponent < 0:
        raise WadDomain("negative integer exponent")
    result = 1
    b = base
    e = exponent
    while e:
        if e & 1:
            result *= b
        b *= b
        e >>= 1
    return result


def _floordiv(a, b):
    if b == 0:
        raise WadDivZero("division by zero")
    return a // b


# ---------------------------------------------------------------- conversion

def from_int(n):
    _req_int(n)
    return _bound(n * WAD)


def parse(text):
    """Parse a plain decimal string such as '-12.034' into an exact WAD int."""
    if type(text) is not str:
        raise WadParse("decimal literal must be a str")
    s = text.strip()
    if not s:
        raise WadParse("empty literal")
    neg = False
    if s[0] in "+-":
        neg = s[0] == "-"
        s = s[1:]
    if s.count(".") > 1:
        raise WadParse("malformed literal: " + text)
    if "." in s:
        ip, fp = s.split(".")
    else:
        ip, fp = s, ""
    if ip == "" and fp == "":
        raise WadParse("malformed literal: " + text)
    for ch in ip + fp:
        if ch not in "0123456789":
            raise WadParse("non-digit in literal: " + text)
    fp_stripped = fp.rstrip("0")
    if len(fp_stripped) > DECIMALS:
        raise WadNonExact("literal has more than 18 fractional digits: " + text)
    ival = int(ip) if ip else 0
    fval = int(fp_stripped.ljust(DECIMALS, "0")) if fp_stripped else 0
    x = ival * WAD + fval
    return _bound(-x if neg else x)


def fmt(x, places=DECIMALS):
    """Exact decimal rendering. places < 18 truncates toward zero (display only)."""
    _req_int(x, places)
    if places < 0 or places > DECIMALS:
        raise WadDomain("places must be in 0..18")
    neg = x < 0
    a = -x if neg else x
    ip = a // WAD
    fp = str(a % WAD).rjust(DECIMALS, "0")[:places]
    body = str(ip) + ("." + fp if places else "")
    if neg and (ip != 0 or fp.strip("0")):
        body = "-" + body
    return body


# ---------------------------------------------------------------- arithmetic

def add(a, b):
    _req_int(a, b)
    return _bound(a + b)


def sub(a, b):
    _req_int(a, b)
    return _bound(a - b)


def mul(a, b):
    """floor(a*b / 10^18)"""
    _req_int(a, b)
    return _bound((a * b) // WAD)


def mul_exact(a, b):
    _req_int(a, b)
    q, r = divmod(a * b, WAD)
    if r:
        raise WadNonExact("mul result not representable at 18 decimals")
    return _bound(q)


def div(a, b):
    """floor(a * 10^18 / b)"""
    _req_int(a, b)
    return _bound(_floordiv(a * WAD, b))


def div_exact(a, b):
    _req_int(a, b)
    if b == 0:
        raise WadDivZero("division by zero")
    q, r = divmod(a * WAD, b)
    if r:
        raise WadNonExact("div result not representable at 18 decimals")
    return _bound(q)


def muldiv(a, b, c):
    """floor(a*b / c), scale-free."""
    _req_int(a, b, c)
    return _bound(_floordiv(a * b, c))


def mul_int(a, n):
    _req_int(a, n)
    return _bound(a * n)


def div_int(a, n):
    """floor(a / n) for an integer n."""
    _req_int(a, n)
    return _bound(_floordiv(a, n))


# ---------------------------------------------------------------- roots and powers

def iroot(n, k):
    """floor(n^(1/k)) for integers n >= 0, k >= 1 (exact, verified)."""
    _req_int(n, k)
    if n < 0:
        raise WadDomain("root of negative number")
    if k < 1:
        raise WadDomain("root order must be >= 1")
    if n < 2 or k == 1:
        return n
    x = 1 << ((n.bit_length() + k - 1) // k)  # x >= true root
    while True:
        y = ((k - 1) * x + n // ipow(x, k - 1)) // k
        if y >= x:
            break
        x = y
    # postcondition: x^k <= n < (x+1)^k
    if ipow(x, k) > n or ipow(x + 1, k) <= n:
        raise WadDomain("iroot postcondition failed")
    return x


def sqrt(x):
    """floor(sqrt(x)) in WAD."""
    _req_int(x)
    return _bound(iroot(x * WAD, 2))


def root(x, k):
    _req_int(x, k)
    return _bound(iroot(x * ipow(WAD, k - 1), k))


def pow_frac(x, p, q):
    """floor(x^(p/q)) in WAD for integer p, integer q >= 1, x >= 0.

    The single final floor is exact: floor(floor(r)^(1/q)) == floor(r^(1/q)).
    """
    _req_int(x, p, q)
    if q < 1:
        raise WadDomain("q must be >= 1")
    if x < 0:
        raise WadDomain("pow_frac requires x >= 0")
    if p == 0:
        return WAD
    if p > 0:
        if p >= q:
            radicand = _floordiv(ipow(x, p), ipow(WAD, p - q))
        else:
            radicand = ipow(x, p) * ipow(WAD, q - p)
    else:
        a = -p
        if x == 0:
            raise WadDivZero("zero to a negative power")
        radicand = _floordiv(ipow(WAD, a + q), ipow(x, a))
    return _bound(iroot(radicand, q))


def pow_int(x, n):
    """floor(x^n) in WAD for integer n >= 0 (single exact floor)."""
    _req_int(x, n)
    if n < 0:
        raise WadDomain("negative exponent: use pow_frac")
    if n == 0:
        return WAD
    return _bound(_floordiv(ipow(x, n), ipow(WAD, n - 1)))


# ---------------------------------------------------------------- exponential

_S = 10 ** 36                                             # internal guard scale
_LN2_36 = 693147180559945309417232121458176568            # floor(ln 2 * 10^36)
EXP_MAX = 130 * WAD                                       # e^130 * 10^18 < 2^255
EXP_ZERO_BELOW = -42 * WAD                                # e^-42 < 10^-18


def _tdiv(a, b):
    """Truncating integer division (toward zero), used only for series terms."""
    q = abs(a) // b
    return -q if a < 0 else q


def exp(x):
    """WAD exponential, floored at 18 decimals.

    Range reduction x = k*ln2 + r with |r| <= ln2/2, Taylor series at 10^-36
    guard precision, exact scaling by 2^k, final floor to 18 decimals.
    Verified against published constants in tests/test_wad18.py.
    """
    _req_int(x)
    if x > EXP_MAX:
        raise WadOverflow("exp argument too large")
    if x < EXP_ZERO_BELOW:
        return 0
    x36 = x * WAD
    k = (x36 + _LN2_36 // 2) // _LN2_36
    r = x36 - k * _LN2_36
    total = _S
    term = _S
    n = 1
    while term != 0:
        term = _tdiv(term * r, _S * n)
        total += term
        n += 1
    if k >= 0:
        total = total * ipow(2, k)
    else:
        total = total // ipow(2, -k)
    return _bound(total // WAD)


# ---------------------------------------------------------------- constants

PI = 3141592653589793238          # floor(pi * 10^18)
LN2 = 693147180559945309          # floor(ln 2 * 10^18)
