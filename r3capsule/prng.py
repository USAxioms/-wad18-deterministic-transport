"""SplitMix64 pseudo-random generator: integer-only, deterministic, seedable."""

MASK64 = (1 << 64) - 1


class SplitMix64:
    def __init__(self, seed):
        if type(seed) is not int:
            raise TypeError("seed must be int")
        self.state = seed & MASK64

    def next_u64(self):
        self.state = (self.state + 0x9E3779B97F4A7C15) & MASK64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & MASK64
        return z ^ (z >> 31)

    def below(self, n):
        """Unbiased integer in [0, n) by rejection sampling; any positive int n."""
        if type(n) is not int or n <= 0:
            raise ValueError("n must be a positive int")
        words = 1
        while (1 << (64 * words)) < n:
            words += 1
        span = 1 << (64 * words)
        limit = span - (span % n)
        while True:
            r = 0
            for _ in range(words):
                r = (r << 64) | self.next_u64()
            if r < limit:
                return r % n

    def bit(self):
        return self.next_u64() >> 63
