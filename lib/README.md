# dsp-gpy/lib

Utility modules used by the templates.

- `qfmt.py`: defines fixed-point formats and derives the widths they imply.
- `vexpr.py`: common Verilog expression generation utilities:
  literals, sign extension, zero padding, declarations, and expression trees.

Neither depends on genesispy itself.

## Q format

A format is the triple `(signed, width, frac)`. A stored code `c` denotes the value `c / 2**frac`,
read as two's complement when the format is signed and as a plain magnitude when it is not. The
format fixes the position of the binary point; nothing about it appears in the hardware, which sees
only `width` bits.

Integer bits are `width - frac`. That count may be zero or negative, and both cases are useful. A
signed format holds `[-2**(int_bits-1), 2**(int_bits-1))` and an unsigned one `[0, 2**int_bits)`:
the low bound is attained exactly, the high bound is one lsb above the largest value. So `Q0.8`
holds `[-1/2, 1/2)`, at the resolution its `frac` gives.

### Notation

`Qm.n` and `UQm.n` name a format in text. `n` is the number of fractional bits and `m + n` is
the width, so `m` is the integer-bit count. Complies with ARM Q convention, in which the sign
bit is part of `m`: a 16-bit signed integer is `Q16.0`. A leading `U` makes the format unsigned.

| Format  | Signed | Width | Integer bits | Fractional bits | lsb                | Range              |
|---------|--------|-------|--------------|-----------------|--------------------|--------------------|
| `Q16.0` | yes    | 16    | 16           | 0               | 1                  | -32768 .. 32767    |
| `UQ8.0` | no     | 8     | 8            | 0               | 1                  | 0 .. 255           |
| `Q4.4`  | yes    | 8     | 4            | 4               | 0.0625 (1/16)      | -8 .. 7.9375       |
| `Q0.8`  | yes    | 8     | 0            | 8               | 0.00390625 (1/256) | -0.5 .. 0.49609375 |
| `Q-1.5` | yes    | 4     | -1           | 5               | 0.03125 (1/32)     | -0.25 .. 0.21875   |

Every bound above is exact. The library computes in `Fraction`, never in floating point, so no
derived bound is off by a rounding error of its own.

### Negative integer bits

`m` may be negative: it counts integer bits, and a shift can drive that count below zero. Only the
width `m + n` is constrained, and only to be at least one bit.

`Q-1.5` is signed, `m + n = 4` bits wide, with `frac = 5`, so a code `c` denotes `c / 32`. Its
four bits weigh -1/4, 1/8, 1/16 and 1/32, the first being the sign bit, so no weight in the word
reaches 1/2. The codes -8 .. 7 denote -1/4 .. 7/32 in steps of 1/32.

`n` may be negative too, giving an lsb above one: `Q6.-2` is four bits stepping by 4. It is
supported by `parse` and `f_qcvt` although its practical use is questionable.

## qfmt

### `Fmt`

A frozen dataclass over the three fields, with everything else derived.

| Member                     | Gives                                                              |
|----------------------------|--------------------------------------------------------------------|
| `signed`, `width`, `frac`  | the fields                                                         |
| `int_bits`                 | `width - frac`                                                     |
| `lsb`                      | the value of a one-code step, as a `Fraction`                      |
| `min_code`, `max_code`     | the extreme codes                                                  |
| `min_val`, `max_val`       | the extreme values                                                 |
| `to_q()`                   | the `Qm.n` string; `str(f)` is the same                            |
| `decode(code)`             | the value a code denotes; raises if the code is out of range       |
| `encode(value)`            | the code for a value; raises unless it is exact and in range       |
| `contains(value)`          | whether `encode` would succeed                                     |
| `codes()`                  | a `range` over every code                                          |
| `with_frac(n)`             | the same range at `n` fractional bits                              |

`encode` is exact by design: a value that is not a multiple of the lsb is an error, not a rounded
code. `with_frac` widens the word to keep the range, so it refuses to lower `frac`; dropping bits is
`requant`'s job.

```python
Fmt(True, 8, 4).encode(Fraction(3, 2))   -> 24
Fmt(True, 8, 4).decode(24)               -> Fraction(3, 2)
Fmt(True, 8, 4).with_frac(6)             -> Q4.6
```

### Building a format

`parse(x)` accepts an `Fmt` unchanged, a `Qm.n` or `UQm.n` string, or a `(signed, width, frac)`
tuple. Every operation calls it on its arguments, so a caller may pass any of the three.

`from_range(lo, hi, frac, signed=None)` returns the narrowest format at `frac` fractional bits that
holds every value in `[lo, hi]`. Signedness follows `lo` unless given. The bounds must be exact
multiples of the lsb.

```python
from_range(Fraction(-1), Fraction(1), 4)   -> Q2.4
```

### Operations

Each returns the narrowest format holding every reachable value, derived from the exact ranges of
the operands rather than from a bound on their widths.

| Call                    | Returns                                                            |
|-------------------------|--------------------------------------------------------------------|
| `mult(a, b, sym=False)` | the product format; `sym` narrows it while `a` avoids its minimum |
| `add(fmts)`             | the sum format; the terms must share `frac`, or it raises          |
| `align(fmts)`           | the terms at a common `frac`, and the left shift each one needs    |
| `envelope(fmts)`        | the format covering every input's range and resolution             |

```python
mult("Q4.4", "Q4.4")                  -> Q8.8
mult("Q4.4", "Q4.4", sym=True)        -> Q7.8
add(["Q4.4"] * 4)                     -> Q6.4
align(["Q1.6", "Q-1.5", "Q5.2"])      -> ["Q1.6", "Q-1.6", "Q5.6"], [0, 1, 4]
envelope(["Q1.6", "Q5.2"])            -> Q5.6
```

`clog2(n)` is included in this library, though it is not format algebra: generates `ceil(log2(n))`,
i.e.  the bits needed to count `n` distinct values.

`add` produces an error for terms whose fractional bits disagree instead of aligning them
itself. Silently aligning would hide the defect that a missing `align` represents: terms added
at different binary points give a wrong sum, and the wrongness is invisible in the widths.

`mult(a, b, sym=True)` excludes the products in which `a` takes its most negative code. How much
that narrows the result depends on whether dropping that corner moves the required range across a
power-of-two boundary, which `from_range` decides case by case, so the saving is zero or more bits
rather than always one:

```python
mult("Q3.0", "UQ3.0", sym=True)       -> Q6.0, the same width as sym=False
mult("Q2.0", "UQ2.0", sym=True)       -> Q3.0, one bit narrower
mult("Q1.0", "UQ2.0", sym=True)       -> Q1.0, two bits narrower
```

The precondition constrains `a` and nobody else, so the caller puts the operand it can guarantee
first; the call raises if that operand is unsigned, since an unsigned format has no most negative
code to exclude. Nothing in `qfmt` checks the precondition at run time -- `funcs/f_sym.svpy`
enforces it in the RTL, and a generator that uses `sym` without it is wrong.

### Requantization

`requant(src, dst, mode="trunc", osym=False, saturate=True)` describes the conversion from one
format to another as the integer operations the RTL performs. It returns a `Requant`.

| Field                  | Means                                                                 |
|------------------------|-----------------------------------------------------------------------|
| `shift`                | `src.frac - dst.frac`: bits to drop, or zeros to append when negative |
| `add_c`                | the rounding constant, added in src codes before the shift            |
| `tie_mask`, `tie_val`  | pick out an exact half, for the `half_even` correction                |
| `min_code`, `max_code` | the clamp bounds, in dst codes                                        |
| `lossless`             | no bit is ever dropped and no value is ever clamped                   |
| `sat_reachable`        | some src code lands outside the dst range after rounding              |

`apply(code, clamp=True)` runs the conversion on one code exactly as the emitted RTL computes it,
so a testbench or a check can compare against it directly.

The three `ROUND_MODES` are `trunc`, `half_up` and `half_even`. `trunc` rounds toward minus
infinity, which is what an arithmetic right shift already does and so costs nothing; `half_up` adds
half an lsb first; `half_even` adds half an lsb and then steps an exact tie down to the even
neighbour. Below, `Q4.12 -> Q2.6`, where one dst lsb is 64 src codes:

| src code | value | `trunc` | `half_up` | `half_even` |
|----------|-------|---------|-----------|-------------|
| 32       | 1/128 | 0       | 1         | 0           |
| 96       | 3/128 | 1       | 2         | 2           |
| 160      | 5/128 | 2       | 3         | 2           |

`osym` clamps a signed output's low end at `-max_code` instead of `min_code`, giving a range
symmetric about zero. `saturate=False` turns a conversion whose clamp can trigger into an error,
so a generator that means to lose no range says so and finds out.

### Errors

Everything the library rejects raises `QError`, a subclass of `ValueError`, with the offending
value in the message. A template catches it and reports it as a generation error.

```text
bad Q format 'Q1' (want Qm.n or UQm.n)
add: terms have different fractional bits [4, 5]; align first
mult: sym needs a signed first operand, got UQ4.4
requant Q4.4 -> Q2.4: range does not fit and saturation is off
```

Rejected: a width below one bit; a string that is not `Qm.n` or `UQm.n`; `add` over terms whose
`frac` disagree; `mult(..., sym=True)` on an unsigned first operand; `with_frac` to fewer fractional
bits; `decode` of a code outside the range; `encode` of a value the format cannot hold exactly;
`requant` with `saturate=False` to a format that cannot hold the source range; `clog2(0)`.

## vexpr

Text helpers. Each turns a generation-time Python value into the Verilog that denotes it, so no
template spells the notation out by hand. A bad value raises `VExprError`, also a subclass of
`ValueError`.

| Call                                 | Writes                                              |
|--------------------------------------|-----------------------------------------------------|
| `lit(value, width, signed=True)`     | a sized decimal literal: `8'sd5`, `-8'sd5`, `8'd5`  |
| `sext(term, from_w, to_w, msb=None)` | `{ { 3 {in[7]} }, in }`; `signed=False` fills zeros |
| `pad_low(term, n)`                   | `{ x, { 3 {1'b0} } }`, appending zero bits below    |
| `decl(what, signed=None, pad=True)`  | `signed [3:-6]`, blanked to the same width when not |
| `parenthesize(terms, op, leaf)`      | one expression, grouped into a balanced tree        |

```python
lit(5, 8)                       -> "8'sd5"
lit(-5, 8)                      -> "-8'sd5"
lit(5, 8, signed=False)         -> "8'd5"
sext("in", 8, 11)               -> "{ { 3 {in[7]} }, in }"
sext("x", 8, 11, signed=False)  -> "{ { 3 {1'b0} }, x }"
sext("x", 7, 10, msb=0)         -> "{ { 3 {x[0]} }, x }"
pad_low("x", 3)                 -> "{ x, { 3 {1'b0} } }"
pad_low("x", 0)                 -> "x"
decl(8, signed=True)            -> "signed [7:0]"
decl(8, signed=False)           -> "       [7:0]"
decl(8, signed=False, pad=0)    -> "[7:0]"
decl(qfmt.parse("Q4.6"))        -> "signed [3:-6]"
parenthesize(["a", "b", "c", "d"]) -> "(a + b) + (c + d)"
```

## Using the library from a template

Import in the Python prologue, then call in a backtick expression. `funcs/f_qcvt.svpy` derives its
whole datapath from one `requant` call. This is its prologue, verbatim:

```systemverilog
//; from vexpr import decl, lit, sext
//; import qfmt
//; h          = self.include_params
//; func_name  = h.get('func_name', 'f_qcvt')
//; q_in       = h.get('q_in',  'Q4.4')
//; q_out      = h.get('q_out', 'Q2.2')
//; round_mode = h.get('round_mode', 'trunc')
//; osym       = h.get('osym', 0)
//; lifetime   = h.get('lifetime', 'static')
//; def q_or_error(fn, *args):
//;     try:
//;         return fn(*args)
//;     except qfmt.QError as e:
//;         error(f"{func_name}: {e}")
//; # enddef
//; f_in     = q_or_error(qfmt.parse, q_in)
//; f_out    = q_or_error(qfmt.parse, q_out)
//; rq       = q_or_error(qfmt.requant, f_in, f_out, round_mode, bool(osym))
//; iwidth   = f_in.width
//; owidth   = f_out.width
//; shift    = rq.shift
//; acc_w    = max(iwidth + abs(shift) + 2, owidth + (0 if f_out.signed else 1))
```

`rq` then carries every constant the RTL needs -- `rq.shift`, `rq.add_c`, `rq.tie_mask`,
`rq.tie_val`, `rq.min_code`, `rq.max_code` -- and the body below it emits a shift in whichever
direction `shift` calls for (a left shift, a right shift with the rounding constant added, or
neither when `shift` is zero), the `half_even` tie correction where the mode asks for it, and the
clamp. Read the file for the body; it is short, and copying it here is how this section came to
describe something the file never did.

`acc_w` is the one derived width worth explaining. The accumulator has to hold the shifted input
before the clamp, hence `iwidth + abs(shift) + 2`; and it has to hold the clamp bounds themselves as
signed literals, hence `owidth` for a signed output and `owidth + 1` for an unsigned one, whose
largest code needs a bit above the sign.

`q_or_error` is the idiom worth copying: a `QError` carries a message naming the bad format, and
wrapping the call turns it into a generation error that names the function too, instead of a Python
traceback.

## Tests

```sh
make pytest                  # or: python3 -m pytest lib/tests
```

`lib/tests/conftest.py` is the whole of the wiring: it puts `lib/` on `sys.path`. No simulator and
no generator is involved.

`lib/tests/test_qfmt.py` cross-checks the algebra against `Fraction` arithmetic over every code
of every format up to six bits wide, so a claim that a result format holds every reachable value
is checked by enumerating them. It also pins `requant`'s constants to what `f_qcvt` emits.
`lib/tests/test_vexpr.py` pins each helper to the hand-written text it replaced, so the helpers
cannot drift from the templates that used to spell the notation out.
