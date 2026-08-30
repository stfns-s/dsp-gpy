"""Verilog expression text, built from generation-time values.

Nothing here computes a width or a format; that is qfmt's job. These helpers turn
a Python value into the Verilog that denotes it, so a template does not spell the
notation out by hand.
"""

from __future__ import annotations


class VExprError(ValueError):
    """A value that cannot be written in the requested Verilog form."""


def lit(value: int, width: int, signed: bool = True) -> str:
    """A sized Verilog decimal literal.

        lit(5, 8)               -> "8'sd5"
        lit(-5, 8)              -> "-8'sd5"
        lit(5, 8, signed=False) -> "8'd5"

    Verilog has no sign inside a sized literal, so a negative value is emitted as
    a unary negation of its magnitude. The most negative value of a width is the
    one case where that magnitude does not itself fit: -8'sd128 truncates to the
    bit pattern for -128 and negating it wraps back. That result is correct only in
    a self-determined context of the same width -- a comparison against an 8-bit
    operand, or an assignment to an 8-bit target. In a wider context the literal
    sign-extends to -128 first and the negation then yields +128. lit() cannot see
    the context it lands in, so the caller owns that.

    The base is decimal because every caller states a numeric bound. Raises if the
    value does not fit the width, which is the check the notation cannot make.
    """
    if width < 1:
        raise VExprError(f"lit: width must be at least one bit, got {width}")
    lo = -(1 << (width - 1)) if signed else 0
    hi = (1 << (width - 1)) - 1 if signed else (1 << width) - 1
    if not lo <= value <= hi:
        kind = "signed" if signed else "unsigned"
        raise VExprError(f"lit: {value} does not fit {width} {kind} bits [{lo}, {hi}]")
    if not signed:
        return f"{width}'d{value}"
    return f"{width}'sd{value}" if value >= 0 else f"-{width}'sd{-value}"


def sext(term: str, from_w: int, to_w: int, msb: int | None = None, signed: bool = True) -> str:
    """Widen a term by replicating its sign bit, or by zeros when unsigned.

        sext("in", 8, 11)                  -> "{ { 3 {in[7]} }, in }"
        sext("x", 8, 11, signed=False)     -> "{ { 3 {1'b0} }, x }"
        sext("x", 7, 10, msb=0)            -> "{ { 3 {x[0]} }, x }"

    msb is the index of the term's sign bit, defaulting to from_w - 1. It is a
    separate argument because a net declared with the binary point in its range,
    [int_bits-1:-frac], has its sign bit at int_bits-1 rather than at width-1.
    """
    if to_w <= from_w:
        raise VExprError(f"sext: to_w ({to_w}) must exceed from_w ({from_w})")
    if from_w < 1:
        raise VExprError(f"sext: from_w must be at least one bit, got {from_w}")
    fill = f"{term}[{from_w - 1 if msb is None else msb}]" if signed else "1'b0"
    return f"{{ {{ {to_w - from_w} {{{fill}}} }}, {term} }}"


def pad_low(term: str, n: int) -> str:
    """Append n zero bits below a term's lsb, moving its binary point down.

    pad_low("x", 3) -> "{ x, { 3 {1'b0} } }"
    pad_low("x", 0) -> "x"
    """
    if n < 0:
        raise VExprError(f"pad_low: n must not be negative, got {n}")
    return term if n == 0 else f"{{ {term}, {{ {n} {{1'b0}} }} }}"


def decl(what: object, signed: bool | None = None, pad: bool = True) -> str:
    """The type part of a declaration: the signedness keyword and the bit range.

        decl(8, signed=True)          -> "signed [7:0]"
        decl(8, signed=False)         -> "       [7:0]"
        decl(8, signed=False, pad=0)  -> "[7:0]"
        decl(qfmt.parse("Q4.6"))      -> "signed [3:-6]"

    Only the type is returned, never a whole declaration, because what precedes it
    differs at every call: a net says "logic", a function says "function static",
    a port says "input". Callers keep their own prefix.

    With pad set, the unsigned form is blanked to the width of "signed" so the
    ranges line up in a column of declarations. That is bookkeeping every caller
    currently does by hand, in five mutually incompatible spellings.

    `what` is a width in bits, or any object exposing int_bits/frac/signed -- a
    qfmt.Fmt -- whose range carries the binary point.
    """
    if hasattr(what, "int_bits"):
        hi, lo = what.int_bits - 1, -what.frac  # type: ignore[attr-defined]
        if signed is None:
            signed = what.signed  # type: ignore[attr-defined]
    else:
        width = int(what)  # type: ignore[call-overload]
        if width < 1:
            raise VExprError(f"decl: width must be at least one bit, got {width}")
        hi, lo = width - 1, 0
    if signed is None:
        raise VExprError("decl: signed must be given for a plain width")
    if signed:
        return f"signed [{hi}:{lo}]"
    return f"       [{hi}:{lo}]" if pad else f"[{hi}:{lo}]"


def parenthesize(terms: list[str], op: str = " + ", leaf: int = 2) -> str:
    """One expression from many terms, parenthesised into a balanced tree.

        parenthesize(["a", "b", "c", "d"])  ->  "(a + b) + (c + d)"

    Verilog parses a + b + c + d left-associatively, which hands synthesis a
    ripple chain. Bisecting the term list until a group holds `leaf` terms or
    fewer gives it a balanced tree instead.

    This cannot change the value. Every term is already at the width of the net
    being assigned, and two's complement addition is associative modulo that
    width, so the grouping is a hint about structure and nothing more.
    """
    if leaf < 1:
        raise VExprError(f"parenthesize: leaf must be at least 1, got {leaf}")
    if not terms:
        raise VExprError("parenthesize: no terms")
    if len(terms) <= leaf:
        return op.join(terms)
    mid = (len(terms) + 1) // 2
    return (
        f"({parenthesize(terms[:mid], op, leaf)})"
        f"{op}"
        f"({parenthesize(terms[mid:], op, leaf)})"
    )
