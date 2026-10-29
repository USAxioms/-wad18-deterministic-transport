from r3capsule import wad18 as w
from r3capsule.prng import SplitMix64

W = w.WAD


def _raises(exc, fn, *a):
    try:
        fn(*a)
    except exc:
        return True
    raise AssertionError("expected " + exc.__name__)


def _close(got, want_str, ulps=1):
    want = w.parse(want_str)
    assert abs(got - want) <= ulps, (w.fmt(got), want_str)


def test_parse_format_roundtrip():
    for s in ["0", "1", "-1", "0.000000000000000001", "-0.5", "123456789.123456789123456789",
              "15500000", "0.000086"]:
        x = w.parse(s)
        assert w.parse(w.fmt(x)) == x
    assert w.parse("1.50") == 3 * W // 2
    assert w.fmt(w.parse("-0.25")) == "-0.250000000000000000"


def test_parse_rejects():
    _raises(w.WadNonExact, w.parse, "0.0000000000000000001")
    _raises(w.WadParse, w.parse, "1e5")
    _raises(w.WadParse, w.parse, "abc")
    _raises(w.WadParse, w.parse, "1.2.3")


def test_type_guard_rejects_non_int():
    _raises(TypeError, w.mul, W, True)
    _raises(TypeError, w.add, W, "1")


def test_mul_div_floor_semantics():
    assert w.mul(3 * W, W // 3) == W - 1
    assert w.mul(-W, 1) == -1
    assert w.div(W, 3 * W) == 333333333333333333
    assert w.div(-W, 3 * W) == -333333333333333334
    assert w.muldiv(7, 3, 2) == 10


def test_exact_variants():
    assert w.mul_exact(2 * W, 3 * W) == 6 * W
    _raises(w.WadNonExact, w.mul_exact, 1, 1)
    assert w.div_exact(W, 4 * W) == W // 4
    _raises(w.WadNonExact, w.div_exact, W, 3 * W)


def test_div_zero_and_overflow():
    _raises(w.WadDivZero, w.div, W, 0)
    _raises(w.WadDivZero, w.div_int, W, 0)
    _raises(w.WadOverflow, w.add, w.INT256_MAX, 1)
    _raises(w.WadOverflow, w.mul, w.INT256_MAX, 2 * W)
    _raises(w.WadOverflow, w.exp, 131 * W)


def test_iroot_floor_property_randomized():
    rng = SplitMix64(12345)
    for _ in range(400):
        n = rng.next_u64() * rng.next_u64() * (rng.below(1000) + 1)
        for k in (2, 3, 4, 5):
            r = w.iroot(n, k)
            assert w.ipow(r, k) <= n < w.ipow(r + 1, k)


def test_pow_frac_floor_property():
    rng = SplitMix64(777)
    for _ in range(300):
        x = rng.below(10 ** 24) + 1
        for p, q in ((4, 5), (2, 5), (1, 2), (3, 2)):
            r = w.pow_frac(x, p, q)
            lhs = w.ipow(x, p) * w.ipow(W, q)
            assert w.ipow(r, q) * w.ipow(W, p) <= lhs < w.ipow(r + 1, q) * w.ipow(W, p)
        r = w.pow_frac(x, -1, 4)
        assert w.ipow(r, 4) * x <= w.ipow(W, 5) < w.ipow(r + 1, 4) * x


def test_known_constants():
    _close(w.exp(W), "2.718281828459045235")
    _close(w.exp(-W), "0.367879441171442321")
    _close(w.exp(2 * W), "7.389056098930650227")
    _close(w.exp(0), "1")
    _close(w.sqrt(2 * W), "1.414213562373095048", 0)
    _close(w.pow_frac(2 * W, 1, 4), "1.189207115002721066", 0)
    _close(w.pow_frac(16 * W, -1, 4), "0.5", 0)
    assert w.PI == w.parse("3.141592653589793238")


def test_exp_identities():
    rng = SplitMix64(99)
    for _ in range(200):
        a = rng.below(20 * W)
        ea = w.exp(a)
        prod = w.mul(ea, w.exp(-a))
        # exp(-a) carries <= 1 ulp floor error (+ <= 1 ulp series/scaling), which the
        # product scales by e^a; mul adds <= 1 ulp. Derived bound: e^a*2/W + 2 ulps.
        bound = 2 * ea // W + 2
        assert W - bound <= prod <= W + 1, (w.fmt(prod), bound)
    prev = -1
    for i in range(-40, 41):
        v = w.exp(i * W // 4)
        assert v > prev
        prev = v
    assert w.exp(-43 * W) == 0
