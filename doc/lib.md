# dsp-gpy lib

[dsp-gpy](../README.md) | [functions](functions.md) | [modules](modules.md) | [verification](verif.md)

Utility modules used by the templates.

- `qfmt.py`: defines fixed-point formats and derives the widths they imply.
- `vexpr.py`: writes Verilog text: literals, sign extension, zero padding, declarations, and
  expression trees.
- `partition.py`: cuts a weighted sequence into contiguous groups of even weight.

None of the three depends on genesispy itself.

## Q format

A format is the triple `(signed, width, frac)`. A stored code `c` denotes the value `c / 2**frac`,
read as two's complement when the format is signed and as a plain magnitude when it is not. The
format fixes the position of the binary point; nothing about it appears in the hardware, which sees
only `width` bits.

Integer bits are `width - frac`. That count may be zero or negative. A
signed format holds `[-2**(int_bits-1), 2**(int_bits-1))` and an unsigned one `[0, 2**int_bits)`:
the low bound is attained exactly, the high bound is one lsb above the largest value. So `Q0.8`
holds `[-1/2, 1/2)`, at the resolution its `frac` gives.

### Notation

`Qm.n` and `UQm.n` name a format in text. `n` is the number of fractional bits and `m + n` is
the width, so `m` is the integer-bit count. This is the ARM convention: the sign bit is part of
`m`, so a 16-bit signed integer is `Q16.0`. A leading `U` makes the format unsigned.

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

Only the width `m + n` is constrained, and only to be at least one bit.

`Q-1.5` is signed, `m + n = 4` bits wide, with `frac = 5`, so a code `c` denotes `c / 32`. Its
four bits weigh -1/4, 1/8, 1/16 and 1/32, the first being the sign bit, so no weight in the word
reaches 1/2. The codes -8 .. 7 denote -1/4 .. 7/32 in steps of 1/32.

`n` may be negative too, giving an lsb above one: `Q6.-2` is four bits stepping by 4. `parse` and
`f_qcvt` accept it.

## qfmt

### Fmt

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

| Call                      | Returns                                                             |
|---------------------------|---------------------------------------------------------------------|
| `mult(a, b, sym, bsym)`   | the product format; `sym` and `bsym` exclude an operand's minimum   |
| `add(fmts)`               | the sum format; the terms must share `frac`, or it raises           |
| `align(fmts)`             | the terms at a common `frac`, and the left shift each one needs     |
| `envelope(fmts)`          | the format covering every input's range and resolution              |
| `bmult(a, b)`             | the product `Bounds` of two `Bounds`                                |
| `badd(bs)`                | the sum `Bounds`; the terms must share `frac`, or it raises         |

```python
mult("Q4.4", "Q4.4")                  -> Q8.8
mult("Q4.4", "Q4.4", sym=True)        -> Q7.8
add(["Q4.4"] * 4)                     -> Q6.4
align(["Q1.6", "Q-1.5", "Q5.2"])      -> ["Q1.6", "Q-1.6", "Q5.6"], [0, 1, 4]
envelope(["Q1.6", "Q5.2"])            -> Q5.6
```

`clog2(n)` returns `ceil(log2(n))`, the bits needed to count `n` distinct values.

`add` raises rather than aligning: terms at different binary points give a wrong sum that the
widths do not show.

`mult(a, b, sym=True)` excludes the products in which `a` takes its most negative code. The saving
is zero or more bits, depending on whether the dropped corner crosses a power-of-two boundary:

```python
mult("Q3.0", "UQ3.0", sym=True)       -> Q6.0, the same width as sym=False
mult("Q2.0", "UQ2.0", sym=True)       -> Q3.0, one bit narrower
mult("Q1.0", "UQ2.0", sym=True)       -> Q1.0, two bits narrower
```

`bsym` says the same of `b`. Each flag constrains the operand it names and nobody else, and the
call raises if that operand is unsigned, since an unsigned format has no most negative code to
exclude. The two are not redundant: excluding both minima can cross a further power-of-two boundary
that excluding either alone does not, which is worth a bit or two on narrow operands.

```python
mult("Q2.0", "Q2.0")                       -> Q4.0
mult("Q2.0", "Q2.0", sym=True)             -> Q3.0
mult("Q2.0", "Q2.0", bsym=True)            -> Q3.0
mult("Q2.0", "Q2.0", sym=True, bsym=True)  -> Q2.0
```

Nothing in `qfmt` checks either precondition at run time -- `functions/f_sym.svpy` enforces it in
the RTL, and a generator that uses `sym` or `bsym` without it is wrong.

### Bounds

A format is the power-of-two container of a range. `Bounds(lo, hi, frac, signed=True)` is the range
itself: the codes `lo .. hi` a net can reach, at `frac` fractional bits. `mult` and `add` are
`bmult` and `badd` over `Bounds.of` with the result converted by `fmt()`, and a one-step
derivation loses nothing by using them. A derivation with more than one step should carry `Bounds`
and call `fmt()` only where it declares a net, because the next step can widen a container where
it would not widen the range:

```python
Bounds.of("Q1.6")                          -> Bounds(lo=-64, hi=63, frac=6, signed=True)
Bounds.of("Q1.6", sym=True)                -> Bounds(lo=-63, hi=63, frac=6, signed=True)
badd([Bounds(-31, 32, 6)] * 3)             -> Bounds(lo=-93, hi=96, frac=6, signed=True)
badd([Bounds(-31, 32, 6)] * 3).fmt()       -> Q2.6
add([Bounds(-31, 32, 6).fmt()] * 3)        -> Q3.6
```

| Member                 | Gives                                                           |
|------------------------|-----------------------------------------------------------------|
| `lo`, `hi`, `frac`     | the fields; `signed` says how `fmt()` reads them                |
| `Bounds.of(fmt, sym)`  | every code of a format, or every code but the most negative one |
| `lo_val`, `hi_val`     | the ends as values                                              |
| `fmt()`                | `from_range` over the ends: the narrowest format holding them   |

`bmult` takes the four corner products of the ends, at `a.frac + b.frac`. `badd` sums the ends.
`requant` with a frac as its target derives the format from the ends, and `Requant.image` carries
a `Bounds` through a conversion; see below. A `Bounds` with `lo > hi`, or
an unsigned one with `lo < 0`, is rejected.

### Requantization

`requant(src, dst, mode="trunc", osym=False, saturate=True)` describes the conversion from one
format to another as the integer operations the RTL performs. It returns a `Requant`. `src` may be
a `Bounds` instead of a format; the source format is then its container, and `sat_reachable` and
the `saturate=False` check judge the clamp over the codes the `Bounds` names rather than over the
whole format. `dst` may be an `int`, the target frac: `src` must then be a `Bounds`, and the target
format is the container of its image at that frac, so the clamp is unreachable by construction;
`osym` is rejected there. That is how a derivation names a product format it has no other reason
to choose.

| Field                  | Means                                                                 |
|------------------------|-----------------------------------------------------------------------|
| `shift`                | `src.frac - dst.frac`: bits to drop, or zeros to append when negative |
| `mode`                 | the rounding mode; an emitter builds the carry from it and `shift`    |
| `min_code`, `max_code` | the clamp bounds, in dst codes                                        |
| `src_bounds`           | the source codes judged: all of `src`, or the `Bounds` given          |
| `lossless`             | no bit is ever dropped and no value is ever clamped                   |
| `sat_lo`, `sat_hi`     | the lowest or highest code in `src_bounds` lands outside the clamp    |
| `sat_reachable`        | either of the two                                                     |

`apply(code, clamp=True)` runs the conversion on one code exactly as the emitted RTL computes it,
so a testbench or a check can compare against it directly. `image(b=None)` returns the `Bounds` the
conversion produces from `b`, or from `src_bounds` when `b` is omitted, clamped into `dst`: every
rounding mode is non-decreasing in its input code, so the two ends are enough.

```python
p  = bmult(Bounds.of("Q1.5", sym=True), Bounds.of("Q1.6", sym=True))
                                           -> Bounds(lo=-1953, hi=1953, frac=11, signed=True)
requant(p, "Q1.6", "half_up").image()      -> Bounds(lo=-61, hi=61, frac=6, signed=True)
requant(p, 6, "half_up").dst               -> Q1.6, the container of that image
requant(p.fmt(), "Q1.6", "half_up").sat_reachable  -> True: the container Q1.11 reaches 64
```

The five `ROUND_MODES` are `trunc`, `half_up`, `half_even`, `half_away` and `to_zero`. `trunc`
rounds toward minus infinity, which is what an arithmetic right shift already does and so costs
nothing; `half_up` adds half an lsb first; `half_even` adds half an lsb and then steps an exact tie
down to the even neighbour; `half_away` rounds a tie to the larger magnitude; `to_zero` drops the
fraction toward zero. Each is one carry into the kept bits, so all five cost an incrementer and
differ only in what drives its carry-in. Below, `Q4.12 -> Q2.6`, where one dst lsb is 64 src
codes:

| src code | value  | `trunc` | `half_up` | `half_even` | `half_away` | `to_zero` |
|----------|--------|---------|-----------|-------------|-------------|-----------|
| 32       | 1/128  | 0       | 1         | 0           | 1           | 0         |
| 96       | 3/128  | 1       | 2         | 2           | 2           | 1         |
| 160      | 5/128  | 2       | 3         | 2           | 3           | 2         |
| -32      | -1/128 | -1      | 0         | 0           | -1          | 0         |
| -96      | -3/128 | -2      | -1        | -2          | -2          | -1        |
| -160     | -5/128 | -3      | -2        | -2          | -3          | -2        |

`osym` clamps a signed output's low end at `-max_code` instead of `min_code`, giving a range
symmetric about zero. `saturate=False` turns a conversion whose clamp can trigger into an error,
so a generator that means to lose no range says so and finds out.

### Errors

Everything the library rejects raises `QError`, a subclass of `ValueError`, with the offending
value in the message. A template catches it and reports it as a generation error.

```text
bad Q format 'Q1' (want Qm.n or UQm.n)
badd: terms have different fractional bits [4, 5]; align first
mult: sym needs a signed first operand, got UQ4.4
requant Q4.4 -> Q2.4: range does not fit and saturation is off
```

Rejected: a width below one bit; a string that is not `Qm.n` or `UQm.n`; `add` or `badd` over
terms whose `frac` disagree; `mult(..., sym=True)` or `Bounds.of(..., sym=True)` on an unsigned
format; `with_frac` to fewer fractional bits; `decode` of a code outside the range; `encode` of a
value the format cannot hold exactly; `requant` with a mode outside `ROUND_MODES`; `requant` with
`saturate=False` to a format that cannot hold the source range; `requant` to a frac from a format
rather than a `Bounds`, or with `osym`; `image` of a `Bounds` at another `frac` than `src`; a
`Bounds` with `lo > hi`; `clog2(0)`.

## vexpr

Text helpers. Each turns a generation-time Python value into the Verilog that denotes it, so no
template spells the notation out by hand. A bad value raises `VExprError`, also a subclass of
`ValueError`.

| Call                                              | Writes                                              |
|---------------------------------------------------|-----------------------------------------------------|
| `lit(value, width, signed=True)`                  | a sized decimal literal: `8'sd5`, `-8'sd5`, `8'd5`  |
| `sext(term, from_w, to_w, msb=None, signed=True)` | `{ { 3 {in[7]} }, in }`; `signed=False` fills zeros |
| `pad_low(term, n)`                                | `{ x, { 3 {1'b0} } }`, appending zero bits below    |
| `decl(what, signed=None, pad=True)`               | `signed [3:-6]`, blanked to the same width when not |
| `parenthesize(terms, op, leaf)`                   | one expression, grouped into a balanced tree        |
| `idx(base, i, n, min_width=1)`                    | `coef03`: member `i` of `n`, padded to one width    |

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
parenthesize(list("abcd"))      -> "(a + b) + (c + d)"
idx("coef", 3, 4)               -> "coef3"
idx("coef", 3, 12)              -> "coef03"
idx("coef", 3, 4, 2)            -> "coef03"
```

## partition

`cut(weights, k)` cuts a sequence into `k` contiguous groups whose widest group, measured as summed
weight, is as narrow as it can be. It returns one group index per element: non-decreasing, starting
at 0, using every index up to `k-1`. Among the cuts that reach the same widest group, it returns the
one whose cuts come earliest.

```python
cut([8, 10, 10, 8], 3)      -> [0, 1, 2, 2]
cut([1, 1, 1, 1, 1, 1], 2)  -> [0, 0, 0, 1, 1, 1]
cut([0, 0, 4], 2)           -> [0, 1, 1]
```

`dotp` calls it with the requantized product width of each live tap, so the group sums it builds are
as even in width as a contiguous cut allows. Nothing else in the repository uses it.

`PartitionError`, a subclass of `ValueError`, is raised for an empty sequence, a negative weight, or
a `k` outside `1 .. len(weights)`.

## Using the library from a template

Import in the Python prologue, then call in a backtick expression. `functions/f_qcvt.svpy` derives
its whole datapath from one `requant` call over a `Bounds` of the source codes that arrive. The
returned `rq` carries what the RTL needs -- `rq.shift`, `rq.mode`, `rq.min_code`, `rq.max_code`,
`rq.src_bounds`, `rq.sat_lo` and `rq.sat_hi` -- and the body emits a shift in whichever direction
`shift` calls for (a left shift, a right shift with a carry into the kept bits, or neither when
`shift` is zero) and a clamp at each end a source code reaches. The carry is built from the mode:
`rq.src_bounds` says whether a negative code can arrive, which is what lets `half_away` collapse to
`half_up` and `to_zero` to `trunc`.

`acc_w` is `max(iwidth + abs(shift) + 2, owidth + (0 if f_out.signed else 1))`. The accumulator
has to hold the shifted input before the clamp, hence
`iwidth + abs(shift) + 2`; and it has to hold the clamp bounds themselves as signed literals, hence
`owidth` for a signed output and `owidth + 1` for an unsigned one, whose largest code needs a bit
above the sign.

`q_or_error` wraps each library call: a `QError` carries a message naming the bad format, and the
wrapper turns it into a generation error that names the function too, instead of a Python
traceback.

## Tests

```sh
make pytest                  # or: python3 -m pytest lib/tests
```

`lib/tests/conftest.py` puts `lib/` on `sys.path`; nothing else is needed. No simulator and no
generator is involved.

`lib/tests/test_qfmt.py` cross-checks the algebra against `Fraction` arithmetic over every code
of every format up to six bits wide, so a claim that a result format holds every reachable value
is checked by enumerating them, and a claim that a `Bounds` is attained at both ends is checked the
same way. It also pins `requant`'s constants to what `f_qcvt` emits.
`lib/tests/test_vexpr.py` pins each helper to the hand-written text it replaced, so the helpers
cannot drift from the templates that used to spell the notation out.
`lib/tests/test_partition.py` compares `cut` against a brute-force search over every short sequence,
so the claim that the cut is optimal is checked by trying all of them.
