from r3capsule.prng import SplitMix64
from r3capsule import jsonio


def test_splitmix64_reference_vector():
    assert SplitMix64(0).next_u64() == 0xE220A8397B1DCDAF


def test_prng_deterministic_and_bounded():
    a, b = SplitMix64(42), SplitMix64(42)
    for _ in range(1000):
        x = a.below(17)
        assert x == b.below(17) and 0 <= x < 17


def test_json_rejects_floats():
    for bad in ('{"a": 1.5}', '[1e3]', '{"x": NaN}', '[Infinity]'):
        try:
            jsonio.loads(bad)
        except jsonio.FloatInJson:
            continue
        raise AssertionError("accepted " + bad)
    assert jsonio.loads('{"a": 15, "b": "1.5"}') == {"a": 15, "b": "1.5"}


def test_json_dump_refuses_non_int_numeric_objects():
    class Fake:
        pass
    try:
        jsonio.dumps({"a": Fake()})
    except jsonio.FloatInJson:
        return
    raise AssertionError("dumped a disallowed object")


def test_below_supports_bounds_above_2_64():
    # regression: rejection window was empty for n > 2^64 (infinite loop)
    r = SplitMix64(5)
    for n in (10 ** 24, (1 << 64) + 1, 1 << 200):
        for _ in range(50):
            assert 0 <= r.below(n) < n


def test_below_unchanged_for_small_bounds():
    # single-word path must equal plain rejection on one 64-bit draw
    a, b = SplitMix64(9), SplitMix64(9)
    for _ in range(200):
        x = a.below(31)
        span = 1 << 64
        limit = span - span % 31
        while True:
            y = b.next_u64()
            if y < limit:
                break
        assert x == y % 31
