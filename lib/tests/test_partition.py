"""partition.cut against brute force over every small weight sequence."""

from itertools import combinations, product

import pytest

from partition import PartitionError, cut


def brute(weights, k):
    """First cut list, in lexicographic order, whose widest group is narrowest."""
    n = len(weights)
    best = None
    for cuts in combinations(range(1, n), k - 1):
        edges = (0, *cuts, n)
        widest = max(sum(weights[a:b]) for a, b in zip(edges, edges[1:]))
        if best is None or widest < best[0]:
            best = (widest, cuts)
    return best[1]


def to_cuts(groups):
    return tuple(i for i in range(1, len(groups)) if groups[i] != groups[i - 1])


# Every sequence to six elements over weights 1..3; seven and eight over 1..2.
CASES = [ws for n in range(1, 7) for ws in product(range(1, 4), repeat=n)]
CASES += [ws for n in (7, 8) for ws in product(range(1, 3), repeat=n)]


@pytest.mark.parametrize("ws", CASES, ids=lambda ws: "".join(map(str, ws)))
def test_matches_brute_force(ws):
    n = len(ws)
    for k in range(1, n + 1):
        got = cut(ws, k)
        assert sorted(set(got)) == list(range(k)), (ws, k, got)
        assert all(a <= b for a, b in zip(got, got[1:])), (ws, k, got)
        assert to_cuts(got) == brute(ws, k), (ws, k, got)


@pytest.mark.parametrize(
    "ws, k, expect",
    [
        ([3, 1, 1, 1], 2, [0, 1, 1, 1]),
        ([1, 1, 1, 1], 2, [0, 0, 1, 1]),
        ([1, 1, 1, 1, 1, 1], 2, [0, 0, 0, 1, 1, 1]),
        ([5], 1, [0]),
        ([8, 10, 10, 8], 3, [0, 1, 2, 2]),
        ([0, 0, 4], 2, [0, 1, 1]),
        ([7, 7, 7, 7], 4, [0, 1, 2, 3]),
    ],
)
def test_examples(ws, k, expect):
    assert cut(ws, k) == expect


@pytest.mark.parametrize(
    "ws, k", [([], 1), ([1, 2], 0), ([1, 2], 3), ([1, -1], 1), ([1.5, 2], 1), ([True, 1], 1)]
)
def test_rejects(ws, k):
    with pytest.raises(PartitionError):
        cut(ws, k)
