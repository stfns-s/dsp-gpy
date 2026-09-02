"""Contiguous k-way partition of a weighted sequence, minimising the widest group.

dotp uses it to cut the live taps into NG groups by product width. Pure Python,
no genesispy and no qfmt, so it runs under pytest on its own.
"""

from __future__ import annotations

from collections.abc import Sequence


class PartitionError(ValueError):
    """A request the partition cannot satisfy."""


def _min_groups(ws: Sequence[int], cap: int) -> int:
    """Fewest contiguous groups with every group sum at most cap, filled greedily."""
    groups, acc = 1, 0
    for w in ws:
        if acc + w > cap:
            groups, acc = groups + 1, w
        else:
            acc += w
    return groups


def _feasible(ws: Sequence[int], groups: int, cap: int) -> bool:
    return len(ws) >= groups and _min_groups(ws, cap) <= groups


def cut(weights: Sequence[int], k: int) -> list[int]:
    """Group index per element for the k-way contiguous cut of weights whose widest group,
    measured as summed weight, is narrowest. Among ties, the cut whose cut positions come
    earliest: the lexicographically smallest list of cut positions.

    Raises PartitionError for an empty sequence, k outside 1 .. len(weights), a negative
    weight, or a weight that is not an int.
    """
    ws = list(weights)
    if not ws:
        raise PartitionError("cut: no weights")
    if any(type(w) is not int for w in ws):
        raise PartitionError(f"cut: non-integer weight in {ws}")
    if any(w < 0 for w in ws):
        raise PartitionError(f"cut: negative weight in {ws}")
    if not 1 <= k <= len(ws):
        raise PartitionError(f"cut: k={k} must be in 1 .. {len(ws)}")
    # Smallest cap with at most k greedy groups. The greedy count is the minimum for that
    # cap, and a group can always be split without raising the widest, so k >= count is
    # exactly feasibility.
    lo, hi = max(ws), sum(ws)
    while lo < hi:
        mid = (lo + hi) // 2
        if _min_groups(ws, mid) <= k:
            hi = mid
        else:
            lo = mid + 1
    cap = lo
    # Earliest cuts: end each group at the first position that leaves the rest feasible.
    # Group sums grow with the end, and some optimal cut exists, so that first position
    # also keeps this group within cap.
    out: list[int] = []
    start = 0
    for g in range(k - 1):
        end = start + 1
        while not _feasible(ws[end:], k - g - 1, cap):
            end += 1
        out.extend([g] * (end - start))
        start = end
    out.extend([k - 1] * (len(ws) - start))
    return out
