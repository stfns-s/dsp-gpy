# dsp-gpy functions

[dsp-gpy](../README.md) | [modules](modules.md) | [verification](verif.md) | [lib](lib.md)

`functions/` holds one arithmetic function per file, pulled into a module with `include()`. A
function is a SystemVerilog `function`, not a module: it has no ports and no state, and the
including module decides what drives it.

The options below are the lowercase keys of `self.include_params`, set by the module that includes
the file:

```systemverilog
//; self.include_params = {'func_name': 'f_scale', 'iwidth': 12, 'owidth': 8}
//; include('f_sat.svpy')
```

They are not the uppercase names that appear in a test configuration. `IW=8:OW=6` names parameters
of the testbench, which passes them down as `iwidth` and `owidth`; see [verification](verif.md).

Each function is emitted under the name given by `func_name`, defaulting to the file's own name.
Every function also accepts `lifetime` (`static` or `automatic`). Most take their operand width as
`iwidth`; the two multipliers take `awidth` and `bwidth` instead, and `f_qcvt` takes Q-format
strings.

| File              | Does                                                    | Also accepts              |
|-------------------|---------------------------------------------------------|---------------------------|
| `f_abs.svpy`      | absolute value, saturating at the most negative input   | `approx`, `isym`          |
| `f_negate.svpy`   | two's complement negate                                 | `approx`, `isym`          |
| `f_sym.svpy`      | map the most negative value to one above it             | --                        |
| `f_sat.svpy`      | narrow the width, saturating on overflow                | `owidth`, `osym`          |
| `f_trunc.svpy`    | narrow the width by dropping low bits                   | `owidth`, `osym`          |
| `f_round.svpy`    | narrow the width, rounding half up and saturating       | `owidth`, `osym`          |
| `f_sx.svpy`       | sign extend to a wider word; errors if not wider        | `owidth`                  |
| `f_sh.svpy`       | shift either way by a signed count, saturating          | `cwidth`                  |
| `f_shleft.svpy`   | shift left, saturating                                  | `cwidth`, `osym`          |
| `f_shright.svpy`  | shift right, saturating                                 | `cwidth`, `osym`          |
| `f_s2sm.svpy`     | two's complement to sign magnitude                      | `owidth`, `sm_plus`       |
| `f_sm2s.svpy`     | sign magnitude to two's complement                      | `owidth`, `sm_plus`       |
| `f_umod.svpy`     | unsigned remainder, by shift and subtract               | --                        |
| `f_log2.svpy`     | integer log2, as `{ sign, log2(abs x) }`                | `isym`, `approx`, `lfrac` |
| `f_logmult.svpy`  | multiply by adding logs                                 | see below                 |
| `f_slogmult.svpy` | multiply by shifting, `a * b =~ a << log2(b)`           | see below                 |
| `f_qcvt.svpy`     | convert between Q formats, rounding and saturating      | the seven Q options below |

| Option              | Default       | Meaning                                                         |
|---------------------|---------------|-----------------------------------------------------------------|
| `iwidth`            | `8`           | input width in bits                                             |
| `owidth`            | `6`/`16`/`8`  | output width: narrowing functions / `f_sx` / `f_s2sm`, `f_sm2s` |
| `cwidth`            | `4`           | shift count width in bits                                       |
| `lifetime`          | `static`      | SystemVerilog function lifetime                                 |
| `approx`            | `0`/`1`       | negate as `~x` instead of `~x + 1`: one adder for one LSB       |
| `isym` / `osym`     | `0`           | input / output already symmetric, so no clamp is needed         |
| `sm_plus`           | `1`           | in sign magnitude, a set MSB means positive                     |
| `awidth`/`bwidth`   | `8`           | multiplier operand widths, in place of `iwidth`                 |
| `lfrac`             | `0`           | fractional bits in the log returned by `f_log2`                 |
| `iapprox`/`oapprox` | `1`/`0`       | approximate the input / output negate of a multiplier           |
| `q_in`/`q_out`      | `Q4.4`/`Q2.2` | `f_qcvt` source and target format, `Qm.n` or `UQm.n`            |
| `round_mode`        | `trunc`       | `f_qcvt` rounding: one of the five modes listed below           |
| `src_lo`/`src_hi`   | the format's  | `f_qcvt` source code range; only a clamp it reaches is emitted  |
| `saturate`          | `1`           | `f_qcvt`: `0` rejects a configuration whose clamp is reachable  |

`approx` defaults to `0` in `f_negate` and `f_abs`, which are exact unless asked otherwise, and to
`1` in `f_log2` and in the multipliers' `iapprox`, where the cheap negate costs one LSB of a value
that is already an approximation. The `owidth` default differs per function so that each one is
usable with no options at all.

An `owidth` of `iwidth` or more does not narrow. `f_sat` and `f_round` then output `iwidth-1` bits,
except that `f_sat` rejects `owidth == iwidth`; `f_trunc` widens its input port to `owidth` and
drops nothing.

`f_sh` and `f_shright` take an extra 2-bit `frac` port giving a finer step than a power of two: the
result is scaled by `1 + frac * 0.25`. Both scale before they shift, so the result is truncated once
rather than once per term. At `sh` of 0 the scaling can push the result past the output range, so
both saturate.

## Log multipliers

`f_log2` returns `{ sign, log2(abs x) }`. The log is the position of the leading one plus one, so a
power of two reports one more than its exponent, and with `lfrac` set the value carries that many
fractional bits: `floor(2**lfrac * log2(2 * m))`, `m` being the magnitude truncated to its top
`lfrac+1` significant bits.

`f_logmult` adds the two logs and shifts back, `f_slogmult` shifts `a` by the log of `b` alone. Both
are approximate. Because the log of a power of two is one high, a product can come out at twice its
true value: `f_log2` returns `floor(log2|x|) + 1`, and `f_logmult` removes only one of the two
offsets, so on a power-of-two pair the product comes out at exactly `2*a*b`. The testbenches check
every case bit-exact against their reference; they carry no relative-error bound, because a bound
loose enough to admit the 2x gain is also satisfied by an output stuck at zero.

The two functions do not take the same options.

| Option              | Default | Taken by    | Meaning                                                          |
|---------------------|---------|-------------|------------------------------------------------------------------|
| `awidth` / `bwidth` | `8`     | both        | operand widths                                                   |
| `isym`              | `0`     | both        | operands already use a symmetric range                           |
| `iapprox`           | `1`     | both        | approximate the negate that takes the input magnitude            |
| `oapprox`           | `0`     | both        | approximate the negate that signs the result                     |
| `zdet`              | `0`/`1` | both        | force zero when an operand is zero (`1` in `f_slogmult`)         |
| `alfrac` / `blfrac` | `0`     | `f_logmult` | fractional bits in each log                                      |
| `antilog`           | `1`     | `f_logmult` | shift back to a product; `0` leaves the result in the log domain |
| `osm`               | `0`     | `f_logmult` | leave the output in sign magnitude rather than two's complement  |
| `sign_only`         | `0`     | `f_logmult` | return only the sign of the product, as `+1`, `-1` or `0`        |

With `antilog` set, `f_logmult` forces `alfrac` and `blfrac` to zero with a warning: the antilog of
a fractional log is a root, not a shift. With `antilog` clear and no fractional bits, it also emits
`<func_name>_antilog`, which turns a log-domain result into the product later. With `sign_only`
clear, it also emits `<func_name>_core`, which takes the logs already taken, so one log function
can feed several cores. `sign_only=1` emits neither the log functions nor the core: it reads the
two sign bits directly.

`f_slogmult` always emits `<func_name>_core` and never emits an antilog function.

## Q-format conversion

`f_qcvt` converts between two Q formats; [lib](lib.md#q-format) defines the notation.

The function shifts to align the binary points, rounds by `round_mode`, and saturates into the
output range; `osym` clamps the low end one above the most negative value. The five modes are
`trunc`, `half_up`, `half_even`, `half_away` and `to_zero`: `trunc` rounds toward minus infinity,
which is what an arithmetic right shift does; `half_up` rounds a tie up, `half_even` rounds a tie to
the even neighbour, `half_away` rounds a tie to the larger magnitude, and `to_zero` drops the
fraction toward zero. [lib](lib.md#requantization) tabulates the five against each other.

`src_lo` and `src_hi` name the source codes that can actually arrive; given them, the function emits
a clamp comparison only at an end some code reaches, and with `saturate=0` it rejects a
configuration where one does. Without them every code of `q_in` is assumed and both clamps are
emitted.

```systemverilog
//; self.include_params = {'func_name': 'f_scale', 'q_in': 'Q4.12', 'q_out': 'Q2.6',
//;                        'round_mode': 'half_even'}
//; include('f_qcvt.svpy')
```

`f_qcvt` gets its shift, rounding mode and clamp bounds from `qfmt.requant` and builds the rounding
carry itself; its testbench keeps its own arithmetic, so the two stay independent.
[lib](lib.md#using-the-library-from-a-template) walks through its prologue.
