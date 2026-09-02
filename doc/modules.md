# dsp-gpy modules

[dsp-gpy](../README.md) | [functions](functions.md) | [verification](verif.md) | [lib](lib.md)

`modules/` holds one synthesizable module per file, each its own genesispy top. A module is
generated per configuration: it derives its internal widths from the generation-time options.
`dotp` emits no Verilog parameter. `iir` and `intg` emit their widths as Verilog parameters as
well; leave them at the generated defaults, since the functions `intg` includes are sized at
generation time and an override does not reach them.

`iir` and `intg` use an active-high `reset` with no `_b` suffix, against the style file; the
testbenches, references and generated code all assume it. `dotp` has no reset. Everything else
follows the style file.

## `iir.svpy` -- single-pole IIR filter

`H(z) = f / (1 + (f - 1) * z^-1)`, where `f = 2^-mu`, refined by the 2-bit `mf` input to
`f = 2^-mu * (1 + mf * 0.25)`. Both `mu` and `mf` are runtime inputs, so the corner frequency can be
changed without regenerating. `mu` must be at least 1: at `mu=0` a nonzero `mf` makes `f` exceed 1
and the accumulator wraps. The file header lists the 3 dB corner for each `mu`.

Ports: `out`, `in`, `mu`, `mf`, `en`, `clk`, `reset`.

| Parameter | Default | Meaning                                   |
|-----------|---------|-------------------------------------------|
| `IW`      | 8       | input width                               |
| `OW`      | 8       | output width                              |
| `MW`      | 4       | width of `mu`                             |
| `ARST`    | 1       | asynchronous (1) or synchronous (0) reset |

`IW`, `OW` and `MW` also appear as Verilog parameters on the emitted module; `ARST` does not, since
it picks which always block is written.

Generation rejects `IW` below 2, `MW` below 1, and an `OW` outside `1..IW+2**MW`, which would slice
below the accumulator's least significant bit.

## `intg.svpy` -- integrator

Accumulates `in`, scaled by `2^-mu`, into a wide accumulator and returns its top `OW` bits. With
`lk_en` set, a fraction `2^-lk_mu` of the current output is subtracted each cycle. When `lim` is
nonzero, the output is held within `+/-lim`; `lim` is signed but must not be negative. The
accumulator clamps rather than wrapping on overflow. `ld` loads `ld_val`, with or without `en`;
`neg` negates the input; `en` gates accumulation.

| Parameter    | Default      | Meaning                                                      |
|--------------|--------------|--------------------------------------------------------------|
| `OW`         | 8            | output width                                                 |
| `IW`         | 4            | input width                                                  |
| `MW`         | 4            | width of `mu` and `lk_mu`                                    |
| `AW`         | `IW+(1<<MW)` | accumulator width                                            |
| `LW`         | `OW>>1`      | how many top bits the leak feedback is taken from            |
| `NEG_APPROX` | 0            | use the cheap negate (`approx` in [functions](functions.md)) |
| `ISYM`       | 0            | input is already symmetric, skip the `f_sym` clamp           |
| `DEBUG`      | 0            | reserved; no debug logic at present, and nothing is emitted  |

The emitted module also carries a Verilog parameter `RSTV`, `OW` bits wide, defaulting to zero: it
is loaded into the top `OW` bits of the accumulator on reset, so it is the value the output takes
out of reset. Unlike the options above it is a plain parameter and can be overridden on an
instance.

`AW` must be at least `OW`, `IW` and `LW`; `OW` must be at least 2; and `LW` must be
at least 2, since the leak negates a signed `LW`-bit word and a one-bit one negates to zero either
way. `LW` defaults to `OW>>1`, so `OW=2` and `OW=3` need an explicit `LW`. Each is checked at
generation time; a violation reports the offending value and writes no file.

## `dotp.svpy` -- dot product

`result = requant(sum(coef[i] * trim(sample[i])))` over `N_TAPS` taps. Each sample is trimmed to a
per-tap format, multiplied by that tap's coefficient, the product requantized to one common binary
point, the products summed in groups, and the total requantized into the output format.

Every width is derived from exact reachable ranges with `qfmt.Bounds`, so no width is a parameter.
The per-step conversions are `f_qcvt` with source bounds, which emits a clamp only where a code can
reach it, and `f_sx` where a term is only sign extended. See [lib](lib.md).

### Parameters

A parameter marked *per tap* takes either one value, used by every tap, or a list of `N_TAPS`
values. A list of any other length is rejected.

| Parameter       | Default     | Per tap | Meaning                                                       |
|-----------------|-------------|---------|---------------------------------------------------------------|
| `N_TAPS`        | `8`         | no      | number of taps                                                |
| `Q_SMPL`        | `'Q1.5'`    | no      | sample format, shared by every tap                            |
| `Q_TRMSMPL`     | see below   | yes     | trimmed sample format                                         |
| `TRMSMPL_ROUND` | `'half_up'` | no      | rounding mode of the sample trim                              |
| `TRMSMPL_SYM`   | `0`         | no      | symmetric clamp on the sample trim                            |
| `ISYM_SMPL`     | `1`         | no      | samples never take their most negative code                   |
| `Q_COEF`        | see below   | yes     | coefficient format                                            |
| `ISYM_COEF`     | `1`         | no      | coefficients never take their most negative code              |
| `PROD_FRAC`     | `None`      | no      | fractional bits of the requantized product; `None` derives it |
| `PROD_ROUND`    | `'trunc'`   | no      | rounding mode of the product requant                          |
| `N_GROUPS`      | `2`         | no      | number of groups the products are summed in                   |
| `TAP_GROUPS`    | `None`      | yes     | explicit group index per tap; `None` partitions               |
| `PARENTH`       | `1`         | no      | balance each adder tree instead of writing a flat sum         |
| `Q_RESULT`      | `'Q6.5'`    | no      | output format                                                 |
| `RESULT_ROUND`  | `'half_up'` | no      | rounding mode of the output requant                           |
| `RESULT_SYM`    | `1`         | no      | symmetric clamp on the output requant                         |
| `PIPE`          | see below   | no      | the stages that carry a register                              |

`PIPE` is a list of stage names, in any order; the word `none` or an empty list is no register
at all. A name it does not know, or one named twice, is rejected.

| Stage     | Registers                           | Clocked by |
|-----------|-------------------------------------|------------|
| `trmsmpl` | the trimmed samples, `qsampleNN`    | `t_clk[i]` |
| `prod`    | the requantized products, `qprodNN` | `t_clk[i]` |
| `groups`  | the group sums, `gsumNN`            | `clk`      |
| `result`  | the output, after its requant       | `clk`      |

The default is `['prod', 'groups']`. A sweep spells the list with commas: `PIPE=trmsmpl,prod`.

The two per-tap defaults marked `see below` are, in tap order:

- `Q_TRMSMPL`: `Q1.4` on tap 0, `Q1.5` on taps 1 to 5, `Q1.4` on taps 6 and 7, so three of the
  outer samples lose their last fractional bit.
- `Q_COEF`: `Q2.5`, `Q4.5`, `Q6.5`, `Q6.5`, `Q6.5`, `Q4.5`, `Q2.5`, `Q1.5`, a coefficient range
  that tapers from the center taps outwards.

These defaults derive `PROD_FRAC` 8 and `Q_SUM` `Q8.8`, a sum reaching `-112.96875 .. 112.9375`.
The default `Q_RESULT` of `Q6.5` holds `+/-31.96875` of that, so the output requant clamps on the
corner vectors.

Every format is signed. `Q_TRMSMPL` may not have more fractional bits than `Q_SMPL`, which would
only append zeros, nor more integer bits, which nothing reaches.

### Tap enable

`tap_en` is `N_TAPS` bits wide and bit `i` belongs to tap `i`. The bit's effect depends on whether
`PIPE` names `trmsmpl` or `prod`.

With either stage in `PIPE`, the module builds one clock per tap:

```verilog
wire [N_TAPS-1:0] t_clk = {N_TAPS{clk}} & tap_en;
```

and tap `i`'s registers run on `t_clk[i]`. A tap whose bit is clear therefore stops updating and
holds its last product, which stays in the sum. `tap_en` has to change away from the rising edge of
`clk`, or the gate passes an edge the tap was not meant to see; driving it on the falling edge is
enough. `dotp` has no reset, so a tap holds `x` until its first enabled edge.

With neither the tap has no register to gate, and the bit zeroes the sample into the multiplier
instead: the tap contributes nothing and the multiplier does not toggle.

### Ports

All ports are `wire`, except `result`, which is a `reg` when `PIPE` names `result`. Widths follow
the formats above.

| Port     | Direction | Present                 | Is                                  |
|----------|-----------|-------------------------|-------------------------------------|
| `result` | output    | always                  | the dot product, in `Q_RESULT`      |
| `sample` | input     | always                  | one sample per tap, in `Q_SMPL`     |
| `coefNN` | input     | one per tap             | that tap's coefficient, in `Q_COEF` |
| `tap_en` | input     | always                  | one bit per tap, by tap index       |
| `clk`    | input     | always                  | unused if `PIPE` is empty           |

`sample` is an unpacked array `[0:N_TAPS-1]` when `N_TAPS > 1`, and a plain scalar port when
`N_TAPS` is 1: Icarus 12 cannot connect a one-element unpacked array port and verilator cannot
connect an element in its place.

The coefficient port number is zero-padded to two digits, or to the digit count of `N_TAPS-1` when
that is wider: the ports are `coef00 .. coef03` at `N_TAPS=4` and `coef000 .. coef119` at
`N_TAPS=120`. The width does not follow the tap count below two digits, so a port name does not
change across configurations.

Internal nets are named the same way: `qsampleNN` for the trimmed sample, `gsampleNN` for the
zeroed operand of an unregistered tap, `prodNN` and `qprodNN` for the product before and after its
requant, `gsumNN` per group, and `sum`. `t_clk` is the per-tap clock.

### Product format and grouping

`PROD_FRAC` is the fractional-bit count every product is requantized to. Left at `None` it is
`min(Q_RESULT.frac + clog2(N_TAPS), max(Q_COEF.frac + Q_TRMSMPL.frac))`: enough that the sum loses
no bit the output shows, and no more than a product carries. Above that a product would only be
padded with zeros, so the cap is enforced.

The products are summed in `N_GROUPS` groups. Without `TAP_GROUPS` the taps are cut into contiguous
groups by `partition.cut` over the requantized product widths, which makes the widest group as
narrow as it can be; see [lib](lib.md#partition). With `TAP_GROUPS` the caller gives the group index
of each tap directly. Either way every group must hold at least one tap. `N_GROUPS=1` is one flat
sum.

### Latency

Each stage in `PIPE` adds one cycle. A coefficient enters the datapath one stage later than a
sample, so the two latencies differ:

- `LATENCY_SMPL` counts every stage in `PIPE`, from `sample` to `result`
- `LATENCY_COEF` counts every stage but `trmsmpl`, from `coefNN` to `result`

With `PIPE` empty the module is combinational. `clk` stays a port, so that the interface does not
change with the parameters, and the module ties it to a net named `unused_clk` to say so.

### Published values

A parent generator can read these back after `dotp` is generated, in place of deriving them again:

| Value                          | Is                                                      |
|--------------------------------|---------------------------------------------------------|
| `Q_TRMSMPL`, `Q_COEF`          | the per-tap trimmed sample and coefficient formats      |
| `Q_PROD`                       | the per-tap requantized product formats                 |
| `Q_GROUPS`, `Q_SUM`            | the per-group sum formats and the total's format        |
| `TAP_GROUPS`                   | the group index of each tap, however it was chosen      |
| `PIPE`                         | the registered stages, in datapath order                |
| `LATENCY_SMPL`, `LATENCY_COEF` | the two latencies above                                 |
| `PROD_FRAC`                    | the value used, derived or given                        |
| `REQUANT`                      | one record per conversion, described below              |

A `REQUANT` record names the step (`trim`, `prod` or `out`), the tap it belongs to, the source and
target format, the rounding mode, and whether the conversion is symmetric, lossless, or has a clamp
some code can reach.

### Rejections

Generation reports the offending value and writes no file for: `N_TAPS` below 1; a rounding mode
outside the five; an unsigned format; a `Q_TRMSMPL` wider than `Q_SMPL` in either direction; a
`PROD_FRAC` above the cap; `N_GROUPS` outside `1..N_TAPS`; a `TAP_GROUPS` index outside
`0..N_GROUPS-1`; an empty group; and a per-tap list whose length is not `N_TAPS`.

Setting both `TRMSMPL_SYM` and `ISYM_SMPL` warns: the clamp already fixes every trim's low bound, so
`ISYM_SMPL` narrows nothing, but it still places the low clamp and is kept.
