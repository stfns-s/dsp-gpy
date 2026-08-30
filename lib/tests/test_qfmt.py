"""Exhaustive cross-validation of qfmt against Fraction arithmetic over small formats."""

from fractions import Fraction
from itertools import combinations, product
from math import floor

import pytest

import qfmt
from qfmt import Fmt, QError

WIDTHS = range(1, 7)
FRACS = range(-2, 7)
FMTS = [Fmt(s, w, f) for s in (True, False) for w in WIDTHS for f in FRACS]

# Enumerating every code pair is only affordable on narrow words. The wider ones are
# checked at their corners, which is where products and sums take their extremes.
SMALL = [f for f in FMTS if f.width <= 4 and f.frac in (-1, 0, 3)]


def narrower(f: Fmt) -> Fmt | None:
    return Fmt(f.signed, f.width - 1, f.frac) if f.width > 1 else None


# -------------------------------------------------------------------- notation
@pytest.mark.parametrize("f", FMTS, ids=str)
def test_q_string_round_trips(f):
    assert qfmt.parse(f.to_q()) == f
    assert qfmt.parse((f.signed, f.width, f.frac)) == f
    assert qfmt.parse(f) is f


@pytest.mark.parametrize(
    "text, expect",
    [
        ("Q1.6", Fmt(True, 7, 6)),
        ("UQ8.8", Fmt(False, 16, 8)),
        ("Q-1.5", Fmt(True, 4, 5)),
        ("UQ-1.3", Fmt(False, 2, 3)),
        ("Q4.-1", Fmt(True, 3, -1)),
        (" Q0.1 ", Fmt(True, 1, 1)),
    ],
)
def test_parse_examples(text, expect):
    assert qfmt.parse(text) == expect


@pytest.mark.parametrize("text", ["X4.4", "Q1", "Q1.6junk", "", "Q0.0", "Q-1.1", "UQ-2.1", "q1.6"])
def test_parse_rejects(text):
    with pytest.raises(QError):
        qfmt.parse(text)


def test_width_below_one_rejected():
    with pytest.raises(QError):
        Fmt(True, 0, 0)


@pytest.mark.parametrize("n, expect", [(1, 0), (2, 1), (3, 2), (4, 2), (5, 3), (8, 3), (9, 4)])
def test_clog2(n, expect):
    assert qfmt.clog2(n) == expect


def test_clog2_rejects_zero():
    with pytest.raises(QError):
        qfmt.clog2(0)


# ------------------------------------------------------------------ code/value
@pytest.mark.parametrize("f", FMTS, ids=str)
def test_encode_decode_every_code(f):
    for c in f.codes():
        v = f.decode(c)
        assert f.encode(v) == c
        assert f.contains(v)
    assert not f.contains(f.max_val + f.lsb)
    assert not f.contains(f.min_val - f.lsb)
    assert not f.contains(f.max_val + f.lsb / 2)


def test_with_frac_preserves_range():
    f = qfmt.parse("Q2.3")
    g = f.with_frac(5)
    assert g == Fmt(True, 7, 5)
    assert g.min_val == f.min_val
    assert all(g.contains(f.decode(c)) for c in f.codes())
    with pytest.raises(QError):
        f.with_frac(2)


# ------------------------------------------------------------------------ mult
@pytest.mark.parametrize("a", SMALL, ids=str)
def test_mult_holds_every_product(a):
    for b in SMALL:
        p = qfmt.mult(a, b)
        assert p.frac == a.frac + b.frac
        for ca, cb in product(a.codes(), b.codes()):
            assert p.contains(a.decode(ca) * b.decode(cb))


@pytest.mark.parametrize("a", FMTS, ids=str)
def test_mult_is_narrowest_at_corners(a):
    for b in FMTS:
        p = qfmt.mult(a, b)
        corners = [x * y for x in (a.min_val, a.max_val) for y in (b.min_val, b.max_val)]
        assert all(p.contains(c) for c in corners)
        n = narrower(p)
        assert n is None or not all(n.contains(c) for c in corners)
        assert p.signed == (a.signed or b.signed)


@pytest.mark.parametrize("a", FMTS, ids=str)
def test_mult_width_is_sum_of_widths(a):
    for b in FMTS:
        w = qfmt.mult(a, b).width
        if a.signed and b.signed:
            assert w == a.width + b.width
        elif not a.signed and not b.signed:
            # a one-bit unsigned factor is an AND gate and adds no width
            assert w == (max(a.width, b.width) if min(a.width, b.width) == 1 else a.width + b.width)


@pytest.mark.parametrize("a", [f for f in SMALL if f.signed], ids=str)
def test_mult_sym_holds_all_but_the_excluded_corner(a):
    for b in SMALL:
        p = qfmt.mult(a, b, sym=True)
        assert p.width <= qfmt.mult(a, b).width
        for ca, cb in product(a.codes(), b.codes()):
            if ca != a.min_code:
                assert p.contains(a.decode(ca) * b.decode(cb))
        if p.width < qfmt.mult(a, b).width:
            assert any(not p.contains(a.decode(a.min_code) * b.decode(cb)) for cb in b.codes())


def test_mult_sym_saves_one_bit_for_signed_operands():
    for a, b in product(FMTS, FMTS):
        if a.signed and b.signed and a.width >= 2:
            assert qfmt.mult(a, b, sym=True).width == a.width + b.width - 1


def test_mult_sym_needs_signed_first_operand():
    with pytest.raises(QError):
        qfmt.mult("UQ4.4", "Q4.4", sym=True)
    assert qfmt.mult("UQ4.4", "Q4.4") == qfmt.mult("Q4.4", "UQ4.4")


# ------------------------------------------------------------------- sum/align
@pytest.mark.parametrize("a", SMALL, ids=str)
def test_add_holds_every_pair_sum(a):
    for b in SMALL:
        if b.frac != a.frac:
            continue
        s = qfmt.add([a, b])
        for ca, cb in product(a.codes(), b.codes()):
            assert s.contains(a.decode(ca) + b.decode(cb))


def _check_add(fs):
    s = qfmt.add(fs)
    lo = sum(f.min_val for f in fs)
    hi = sum(f.max_val for f in fs)
    assert s.contains(lo) and s.contains(hi)
    n = narrower(s)
    assert n is None or not (n.contains(lo) and n.contains(hi))
    assert s.signed == any(f.signed for f in fs)


def test_add_is_narrowest_for_pairs():
    for a, b in product(FMTS, FMTS):
        if a.frac == b.frac:
            _check_add([a, b])


def test_add_is_narrowest_for_three_and_four_terms():
    pool = [Fmt(s, w, 0) for s in (True, False) for w in WIDTHS]
    for k in (3, 4):
        for fs in combinations(pool, k):
            _check_add(list(fs))


def test_add_rejects_misaligned_terms():
    with pytest.raises(QError):
        qfmt.add(["Q4.4", "Q4.5"])
    with pytest.raises(QError):
        qfmt.add([])


def test_align_preserves_ranges_and_reports_shifts():
    fs = [qfmt.parse(q) for q in ("Q1.6", "Q-1.5", "Q5.2")]
    aligned, shifts = qfmt.align(fs)
    assert shifts == [0, 1, 4]
    assert {f.frac for f in aligned} == {6}
    for f, g in zip(fs, aligned):
        assert g.min_val == f.min_val
        assert all(g.contains(f.decode(c)) for c in f.codes())
    assert qfmt.add(aligned).width == 12


def test_envelope_covers_every_input():
    for a, b in product(FMTS, FMTS):
        h = qfmt.envelope([a, b])
        for f in (a, b):
            assert h.contains(f.min_val) and h.contains(f.max_val)
            assert h.contains(f.min_val + f.lsb) or f.width == 1
        n = narrower(h)
        vals = [a.min_val, a.max_val, b.min_val, b.max_val]
        assert n is None or not all(n.contains(v) for v in vals)


# --------------------------------------------------------------------- requant
def ref_requant(v: Fraction, dst: Fmt, mode: str, osym: bool) -> int:
    q = v / dst.lsb
    if mode == "trunc":
        c = floor(q)
    elif mode == "half_up":
        c = floor(q + Fraction(1, 2))
    else:
        c = round(q)  # Fraction.__round__ is half-to-even
    lo = -dst.max_code if (dst.signed and osym) else dst.min_code
    return max(lo, min(dst.max_code, c))


REQ_SRC = [f for f in FMTS if f.width <= 5]
REQ_DST = [f for f in FMTS if f.frac in (-2, 0, 3, 6)]


@pytest.mark.parametrize("osym", [False, True])
@pytest.mark.parametrize("mode", qfmt.ROUND_MODES)
def test_requant_matches_fraction_reference(mode, osym):
    for src, dst in product(REQ_SRC, REQ_DST):
        rq = qfmt.requant(src, dst, mode, osym)
        for c in src.codes():
            assert rq.apply(c) == ref_requant(src.decode(c), dst, mode, osym), (src, dst, c)


def test_requant_reports_loss():
    assert qfmt.requant("Q4.4", "Q6.6").lossless
    assert not qfmt.requant("Q4.4", "Q4.2").lossless
    assert not qfmt.requant("Q4.4", "Q4.2").sat_reachable
    assert qfmt.requant("Q4.4", "Q4.2", "half_up").sat_reachable
    assert qfmt.requant("Q4.4", "Q2.4").sat_reachable
    assert qfmt.requant("Q4.4", "Q4.4", osym=True).sat_reachable


def test_requant_can_refuse_saturation():
    with pytest.raises(QError):
        qfmt.requant("Q4.4", "Q2.4", saturate=False)
    assert qfmt.requant("Q4.4", "Q4.2", saturate=False).shift == 2


def test_requant_rejects_bad_mode():
    with pytest.raises(QError):
        qfmt.requant("Q4.4", "Q2.2", "nearest")


def test_requant_constants_match_f_qcvt():
    rq = qfmt.requant("Q4.12", "Q2.6", "half_even")
    assert (rq.shift, rq.add_c, rq.tie_mask, rq.tie_val) == (6, 32, 63, 32)
    assert (rq.min_code, rq.max_code) == (-128, 127)
    rq = qfmt.requant("Q4.4", "Q4.4", osym=True)
    assert (rq.min_code, rq.max_code) == (-127, 127)
    rq = qfmt.requant("Q3.5", "Q3.9")
    assert (rq.shift, rq.add_c) == (-4, 0)


# -------------------------------------------------------- reference design check
def test_ffe_slice_widths_from_ff_txt():
    """The partial-sum widths derived in ff.txt section 3, from formats alone."""
    sample = qfmt.parse("Q1.6")
    coef_w = [4, 6, 7, 8, 9, 10, 9, 9, 8, 8, 6, 6, 5, 5, 5, 5, 5, 5, 5, 5] + [5] * 40
    groups = [
        [4, 5, 6],
        [0, 1, 2, 3] + list(range(7, 20)),
        list(range(20, 40)),
        list(range(40, 60)),
    ]
    coefs = [Fmt(True, w, 5) for w in coef_w]
    assert [c.to_q() for c in coefs[:6]] == ["Q-1.5", "Q1.5", "Q2.5", "Q3.5", "Q4.5", "Q5.5"]
    pp = [qfmt.requant(qfmt.mult(c, sample, sym=True), Fmt(True, c.width + 4, 9)) for c in coefs]
    assert all(r.shift == 2 for r in pp)
    ps = [qfmt.add([pp[i].dst for i in g]) for g in groups]
    assert [p.width for p in ps] == [15, 15, 14, 14]
    out = qfmt.add(ps)
    assert (out.width, out.to_q()) == (17, "Q8.9")
