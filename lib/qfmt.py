"""Fixed-point format algebra for generation-time width derivation.

A format is (signed, width, frac). A stored code c denotes c / 2**frac, read as two's
complement when signed. Integer bits are width - frac and may be zero or negative, so
Q-1.5 (a four-bit signed word with five fractional bits) is a valid format.

The Qm.n strings follow the ARM convention: m + n is the width and m includes the sign
bit, so a 16-bit signed integer is Q16.0 (Texas Instruments would write Q15.0).

Every range is exact: values are Fractions, never floats. Nothing here emits Verilog or
imports genesispy, so the module runs under pytest on its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence, Union

_Q_RE = re.compile(r"(U?)Q(-?\d+)\.(-?\d+)")

ROUND_MODES = ("trunc", "half_up", "half_even")


class QError(ValueError):
    """A format, conversion or combination that the algebra rejects."""


def clog2(n: int) -> int:
    """Bits needed to count n distinct values: ceil(log2(n)), exact in integers."""
    if n < 1:
        raise QError(f"clog2: need n >= 1, got {n}")
    return (n - 1).bit_length()


@dataclass(frozen=True)
class Fmt:
    signed: bool
    width: int
    frac: int

    def __post_init__(self) -> None:
        if self.width < 1:
            raise QError(f"{self.to_q()}: a format needs at least one bit")

    # ----------------------------------------------------------------- shape
    @property
    def int_bits(self) -> int:
        return self.width - self.frac

    @property
    def lsb(self) -> Fraction:
        return Fraction(1, 1 << self.frac) if self.frac >= 0 else Fraction(1 << -self.frac)

    @property
    def min_code(self) -> int:
        return -(1 << (self.width - 1)) if self.signed else 0

    @property
    def max_code(self) -> int:
        return (1 << (self.width - 1)) - 1 if self.signed else (1 << self.width) - 1

    @property
    def min_val(self) -> Fraction:
        return self.min_code * self.lsb

    @property
    def max_val(self) -> Fraction:
        return self.max_code * self.lsb

    # ------------------------------------------------------------- notation
    def to_q(self) -> str:
        return f"{'' if self.signed else 'U'}Q{self.width - self.frac}.{self.frac}"

    def __str__(self) -> str:
        return self.to_q()

    # ----------------------------------------------------------- code/value
    def decode(self, code: int) -> Fraction:
        if not self.min_code <= code <= self.max_code:
            raise QError(f"{self}: code {code} out of range")
        return code * self.lsb

    def encode(self, value: Union[Fraction, int]) -> int:
        """Exact code for value; raises unless value is representable and in range."""
        q = Fraction(value) / self.lsb
        if q.denominator != 1:
            raise QError(f"{self}: {value} is not a multiple of the lsb")
        code = int(q)
        if not self.min_code <= code <= self.max_code:
            raise QError(f"{self}: {value} out of range")
        return code

    def contains(self, value: Union[Fraction, int]) -> bool:
        q = Fraction(value) / self.lsb
        return q.denominator == 1 and self.min_code <= q <= self.max_code

    def codes(self) -> range:
        return range(self.min_code, self.max_code + 1)

    def with_frac(self, frac: int) -> Fmt:
        """Same range at more fractional bits: a value-preserving left shift."""
        if frac < self.frac:
            raise QError(f"{self}: with_frac({frac}) would drop bits; use requant")
        return Fmt(self.signed, self.width + frac - self.frac, frac)


FmtLike = Union[Fmt, str, Sequence[object]]


def parse(x: FmtLike) -> Fmt:
    """Fmt from a Fmt, a Qm.n / UQm.n string, or a (signed, width, frac) tuple."""
    if isinstance(x, Fmt):
        return x
    if isinstance(x, str):
        m = _Q_RE.fullmatch(x.strip())
        if not m:
            raise QError(f"bad Q format {x!r} (want Qm.n or UQm.n)")
        m_bits, n_bits = int(m.group(2)), int(m.group(3))
        return Fmt(m.group(1) == "", m_bits + n_bits, n_bits)
    if isinstance(x, Sequence) and len(x) == 3:
        signed, width, frac = x
        return Fmt(bool(signed), int(width), int(frac))  # type: ignore[call-overload]
    raise QError(f"bad format {x!r} (want Fmt, Q string or (signed, width, frac))")


def from_range(lo: Fraction, hi: Fraction, frac: int, signed: Union[bool, None] = None) -> Fmt:
    """Narrowest format at frac holding every value in [lo, hi]."""
    if lo > hi:
        raise QError(f"from_range: empty range [{lo}, {hi}]")
    if signed is None:
        signed = lo < 0
    if not signed and lo < 0:
        raise QError(f"from_range: unsigned format cannot hold {lo}")
    probe = Fmt(signed, 1, frac)
    lo_code, hi_code = Fraction(lo) / probe.lsb, Fraction(hi) / probe.lsb
    if lo_code.denominator != 1 or hi_code.denominator != 1:
        raise QError(f"from_range: bounds are not multiples of 2**-{frac}")
    width = 1
    while True:
        f = Fmt(signed, width, frac)
        if f.min_code <= lo_code and hi_code <= f.max_code:
            return f
        width += 1


# ------------------------------------------------------------------ operations
def mult(a: FmtLike, b: FmtLike, sym: bool = False) -> Fmt:
    """Product format, signed if either operand is.

    With sym=True the result holds every product except those where a takes its most
    negative code; a must be signed, and the caller owns the precondition (f_sym enforces
    it in RTL). How much that saves depends on whether dropping a's minimum corner moves
    the required range across a power-of-two boundary, which from_range decides case by
    case: mult("Q3.0", "UQ3.0", sym=True) saves nothing, mult("Q2.0", "UQ2.0", sym=True)
    saves one bit, mult("Q1.0", "UQ2.0", sym=True) saves two. It is never wider.
    """
    fa, fb = parse(a), parse(b)
    a_min = fa.min_val
    if sym:
        if not fa.signed:
            raise QError(f"mult: sym needs a signed first operand, got {fa}")
        a_min = -fa.max_val
    corners = [x * y for x in (a_min, fa.max_val) for y in (fb.min_val, fb.max_val)]
    return from_range(min(corners), max(corners), fa.frac + fb.frac, fa.signed or fb.signed)


def _aligned(fmts: Iterable[FmtLike], what: str) -> list[Fmt]:
    fs = [parse(f) for f in fmts]
    if not fs:
        raise QError(f"{what}: no terms")
    fracs = {f.frac for f in fs}
    if len(fracs) > 1:
        raise QError(f"{what}: terms have different fractional bits {sorted(fracs)}; align first")
    return fs


def add(fmts: Iterable[FmtLike]) -> Fmt:
    """Format holding every reachable sum of the terms. Terms must share a frac."""
    fs = _aligned(fmts, "add")
    lo = sum((f.min_val for f in fs), Fraction(0))
    hi = sum((f.max_val for f in fs), Fraction(0))
    return from_range(lo, hi, fs[0].frac, any(f.signed for f in fs))


def align(fmts: Iterable[FmtLike]) -> tuple[list[Fmt], list[int]]:
    """Bring terms to a common frac (the maximum). Returns the aligned formats and the
    left shift each term needs, in that order."""
    fs = [parse(f) for f in fmts]
    if not fs:
        raise QError("align: no terms")
    frac = max(f.frac for f in fs)
    shifts = [frac - f.frac for f in fs]
    return [f.with_frac(frac) for f in fs], shifts


def envelope(fmts: Iterable[FmtLike]) -> Fmt:
    """Narrowest format whose range and resolution cover every input."""
    fs, _ = align(fmts)
    lo = min(f.min_val for f in fs)
    hi = max(f.max_val for f in fs)
    return from_range(lo, hi, fs[0].frac, any(f.signed for f in fs))


# -------------------------------------------------------------------- requant
@dataclass(frozen=True)
class Requant:
    """What a src -> dst conversion does, in integer terms the RTL can use directly.

    shift > 0 drops that many lsbs (with rounding), shift < 0 appends zeros. add_c is the
    rounding constant in src codes; tie_mask/tie_val pick out an exact half for
    half_even. min_code/max_code are the dst clamp bounds.
    """

    src: Fmt
    dst: Fmt
    mode: str
    osym: bool
    shift: int
    add_c: int
    tie_mask: int
    tie_val: int
    min_code: int
    max_code: int

    @property
    def lossless(self) -> bool:
        """No bit is ever dropped and no value is ever clamped."""
        return self.shift <= 0 and not self.sat_reachable

    @property
    def sat_reachable(self) -> bool:
        """Some src code lands outside the dst range after rounding."""
        lo, hi = self.apply(self.src.min_code, clamp=False), self.apply(
            self.src.max_code, clamp=False
        )
        return lo < self.min_code or hi > self.max_code

    def apply(self, code: int, clamp: bool = True) -> int:
        """The conversion on one src code, as the emitted RTL computes it."""
        if self.shift > 0:
            acc = (code + self.add_c) >> self.shift
            if self.mode == "half_even" and (code & self.tie_mask) == self.tie_val and acc & 1:
                acc -= 1
        else:
            acc = code << -self.shift
        if clamp:
            acc = max(self.min_code, min(self.max_code, acc))
        return acc


def requant(
    src: FmtLike, dst: FmtLike, mode: str = "trunc", osym: bool = False, saturate: bool = True
) -> Requant:
    """Describe the conversion from src to dst. With saturate=False, a conversion whose
    clamp can trigger is an error rather than a silent range loss."""
    fs, fd = parse(src), parse(dst)
    if mode not in ROUND_MODES:
        raise QError(f"bad round mode {mode!r} (want {', '.join(ROUND_MODES)})")
    shift = fs.frac - fd.frac
    rounding = shift > 0 and mode != "trunc"
    min_code = -fd.max_code if (fd.signed and osym) else fd.min_code
    rq = Requant(
        src=fs,
        dst=fd,
        mode=mode,
        osym=bool(osym),
        shift=shift,
        add_c=(1 << (shift - 1)) if rounding else 0,
        tie_mask=(1 << shift) - 1 if shift > 0 else 0,
        tie_val=(1 << (shift - 1)) if shift > 0 else 0,
        min_code=min_code,
        max_code=fd.max_code,
    )
    if not saturate and rq.sat_reachable:
        raise QError(f"requant {fs} -> {fd}: range does not fit and saturation is off")
    return rq
