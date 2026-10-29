from r3capsule import pareto
from r3capsule import wad18 as w

W = w.WAD


def test_dominance():
    assert pareto.dominates((2, 1), (1, 1))
    assert pareto.dominates((1, 0), (1, 1))
    assert not pareto.dominates((1, 1), (1, 1))
    assert not pareto.dominates((2, 2), (1, 1))


def test_hypervolume_hand_example():
    # ref (1, 10); points (2, 8), (3, 9): (2-1)*(10-8) + (3-2)*(10-9) = 3, /10 -> 0.3
    pts = [(2 * W, 8 * W), (3 * W, 9 * W)]
    assert pareto.hypervolume(pts, W, 10 * W) == w.parse("0.3")
    pts2 = pts + [(2 * W, 9 * W), (W, 1), (5 * W, 11 * W)]
    assert pareto.hypervolume(pts2, W, 10 * W) == w.parse("0.3")


def test_archive_keeps_nondominated():
    a = pareto.Archive()
    assert a.add("a", (1, 5))
    assert a.add("b", (2, 6))
    assert a.add("c", (2, 5))
    assert set(a.items) == {"c"}
    assert not a.add("d", (2, 5))
