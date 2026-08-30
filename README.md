# dsp-gpy

Fixed-point DSP building blocks for hardware, using
[genesispy](https://github.com/stfns-s/genesispy) templates.

## Requirements

The [genesispy](https://github.com/stfns-s/genesispy) generator. Install it somewhere locally.
`setup.sh` finds it and puts it on `PATH`.

```sh
source setup.sh                                    # checkout beside this one
GENESISPY_HOME=/path/to/genesispy source setup.sh  # or somewhere else
```

The rest are the tools the make targets run:

- `iverilog`, in 2012 mode: `make test`
- `verilator`: `make test-extra`, `make plot`, and `vlint` by default
- `xrun`: optional, `make sim` drives it too
- `pytest`: the Q format library tests
- matplotlib: `verif/plot.py`, installed with `pip install -r verif/requirements.txt`

## Directory structure

```text
funcs/            arithmetic functions, pulled in with include()
lib/              qfmt.py and vexpr.py, imported by the templates; on --py-path
  tests/          pytest suite for both
modules/          synthesizable modules, one top each
verif/
  funcs/          tb_f_<name>.svpy, one testbench per function
  modules/        tb_<name>.svpy, one testbench per module
  common/         tb_util.svpy (fdiv, clamp, tb_sext, check, data and report tasks) and
                  tb_ref_log2.svpy (64-bit f_log2 reference, shared by the three log tests)
  sweeps.mk       which configurations make test runs
  run-tb.sh       generate, build and run one testbench in one configuration
  plot.py         plot a data file
build/            everything generated; not in git
```

`build/` holds one directory per top and configuration, named after the genesispy top, and under it
one directory per simulator, for instance `build/tb_f_round/IW8_OW6/iverilog/`:

```text
raw/                  generated Python intermediates
synth/                the DUT, when the testbench instantiates one
verif/                the elaborated testbench, and gen.log from generating it
tb.vf                 file list naming both synth/ and verif/
build.log             what the build printed
run.log               what the run printed, including the simulator's $finish line
data.csv              the per-case data file, when the run was asked for one
obj/ or sim.vvp       the built binary, verilator or iverilog
tb_<name>.depend      the included functions, for make's dependency tracking
genesispy_clean.sh    genesispy's own cleanup script
```

`gen` is a simulator name here too: an elaborate-only run lands in `gen/`, which is where
`make sim` picks up its file list. `make sim` writes its own artifacts to `sim/` beside it.

Each simulator gets a whole tree of its own rather than sharing the generated Verilog. Generation
is deterministic, so the trees hold the same Verilog either way; what the separation buys is that
no two runs ever write the same file, which is what lets `make -j test test-extra` run both
simulators over one configuration at once.

`lib/` holds the utility functions the templates import at generation time:

- `qfmt.py`: defines fixed-point formats and derives the widths they imply.
- `vexpr.py`: common Verilog expression generation utilities:
  literals, sign extension, zero padding, declarations, and expression trees.

[lib/README.md](lib/README.md) defines the Q format and documents both modules call by call.

## Function library

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
| `f_round.svpy`    | narrow the width, rounding half up, clamped on overflow | `owidth`, `osym`          |
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
| `f_qcvt.svpy`     | convert between Q formats, rounding and saturating      | `round_mode`, `osym`      |

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
| `round_mode`        | `trunc`       | `f_qcvt` rounding: `trunc`, `half_up` or `half_even`            |

`approx` defaults to `0` in `f_negate` and `f_abs`, which are exact unless asked otherwise, and to
`1` in `f_log2` and in the multipliers' `iapprox`, where the cheap negate costs one LSB of a value
that is already an approximation. That is the operating point the algorithms were written for. The
`owidth` default differs per function so that each one is usable with no options at all.

`f_sh` and `f_shright` take an extra 2-bit `frac` port giving a finer step than a power of two: the
result is scaled by `1 + frac * 0.25`. Both scale before they shift, so the result is truncated once
rather than once per term. At `sh` of 0 the scaling can push the result past the output range, so
both saturate.

### Log multipliers

`f_log2` returns `{ sign, log2(abs x) }`. The log is the position of the leading one plus one, so a
power of two reports one more than its exponent, and with `lfrac` set the value carries that many
fractional bits: `floor(2**lfrac * log2(2 * m))`, `m` being the magnitude truncated to its top
`lfrac+1` significant bits.

`f_logmult` adds the two logs and shifts back, `f_slogmult` shifts `a` by the log of `b` alone. Both
are approximate. Because the log of a power of two is one high, a product can come out at twice its
true value: `f_log2` returns `floor(log2|x|) + 1`, and `f_logmult` removes only one of the two
offsets, so on a power-of-two pair the product comes out at exactly `2*a*b`. The testbenches check
every case bit-exact against their reference; they carry no relative-error bound, because a bound
loose enough to admit the 2x gain is also satisfied by an output stuck at zero, which scores the
same 100% with the opposite sign.

| Option              | Default | Meaning                                                          |
|---------------------|---------|------------------------------------------------------------------|
| `awidth` / `bwidth` | `8`     | operand widths                                                   |
| `isym`              | `0`     | operands already use a symmetric range                           |
| `iapprox`           | `1`     | approximate the negate that takes the input magnitude            |
| `oapprox`           | `0`     | approximate the negate that signs the result                     |
| `zdet`              | `0`/`1` | force zero when an operand is zero (`1` in `f_slogmult`)         |
| `alfrac` / `blfrac` | `0`     | fractional bits in each log (`f_logmult`)                        |
| `antilog`           | `1`     | shift back to a product; `0` leaves the result in the log domain |
| `osm`               | `0`     | leave the output in sign magnitude rather than two's complement  |
| `sign_only`         | `0`     | return only the sign of the product, as `+1`, `-1` or `0`        |

With `antilog` set, `alfrac` and `blfrac` are forced to zero and the function says so: the antilog
of a fractional log is a root, not a shift. With `antilog` clear and no fractional bits, the
function also emits `<func_name>_antilog`, which turns a log-domain result into the product later.
With `sign_only` clear, each also emits `<func_name>_core`, which takes the logs already taken, so
one log function can feed several cores. `sign_only=1` emits neither the log functions nor the core:
it reads the two sign bits directly.

### Q-format conversion

`f_qcvt` converts `Qm.n` to `Qm.n`, where `m + n` is the word width and `n` counts fractional
bits. This is the ARM convention, in which `m` includes the sign bit; the Texas Instruments
convention counts it separately and would call the same 16-bit integer `Q15.0` rather than
`Q16.0`. A leading `U` makes the format unsigned. `m` may be zero or negative: the sign bit is part
of the width, not of `m`, so `Q-1.5` is a four-bit signed word holding multiples of 1/32 below 1/4
in magnitude. The only rejected format is one with no bits. The function shifts to align the binary
points, rounds by `round_mode`, and saturates into the output range; `osym` clamps the low end one
above the most negative value. `trunc` rounds toward minus infinity, which is what an arithmetic
right shift does; `half_up` rounds a tie up, `half_even` rounds a tie to the even neighbour.

```systemverilog
//; self.include_params = {'func_name': 'f_scale', 'q_in': 'Q4.12', 'q_out': 'Q2.6',
//;                        'round_mode': 'half_even'}
//; include('f_qcvt.svpy')
```

### Q format library

`lib/qfmt.py` is where a template derives a width instead of writing one down: it computes
fixed-point formats and the widths they imply, from exact ranges rather than from a bound on the
widths. `lib/vexpr.py` is the other half, writing the Verilog that denotes a generation-time value
and computing no width of its own. `f_qcvt` gets its shift, rounding constant and clamp bounds from
`qfmt.requant`; its testbench keeps its own arithmetic, so the two stay independent.

## Modules

Both modules deviate from the house RTL style in one respect, deliberately and tree-wide: `reset` is
active high and carries no `_b` suffix, where the style file asks for active low. The testbenches,
the references and the generated code all assume active high, so the deviation is consistent rather
than accidental. Everything else follows the style file: `wire` on ports, `logic` for combinational
targets, `reg` for state, and no synthesis case directives.

### `modules/iir.svpy` -- single-pole IIR filter

`H(z) = f / (1 + (f - 1) * z^-1)`, where `f = 2^-mu`, refined by the 2-bit `mf` input to
`f = 2^-mu * (1 + mf * 0.25)`. Both `mu` and `mf` are runtime inputs, so the corner frequency can be
changed without regenerating. The file header lists the 3 dB corner for each `mu`.

`IW`, `OW`, `MW` and `ARST` are all generation-time options. They appear in the emitted module as
Verilog parameters as well, but the module is uniquified per configuration and derives its internal
widths from the generation-time values, so overriding the Verilog parameter on an instance does not
work. `ARST` (default 1) selects an asynchronous or synchronous reset.

Generation rejects `IW` below 2, `MW` below 1, and an `OW` outside `1..IW+2**MW`, which would slice
below the accumulator's least significant bit.

### `modules/intg.svpy` -- integrator

Accumulates `in`, scaled by `2^-mu`, into a wide accumulator and returns its top `OW` bits. With
`lk_en` set, a fraction `2^-lk_mu` of the current output is subtracted each cycle. When `lim` is
nonzero, the output is held within `+/-lim`. The accumulator clamps rather than wrapping on
overflow. `ld` loads `ld_val`, `neg` negates the input, `en` gates updates.

| Parameter    | Default      | Meaning                                             |
|--------------|--------------|-----------------------------------------------------|
| `OW`         | 8            | output width                                        |
| `IW`         | 4            | input width                                         |
| `MW`         | 4            | width of `mu` and `lk_mu`                           |
| `AW`         | `IW+(1<<MW)` | accumulator width                                   |
| `LW`         | `OW>>1`      | how many top bits the leak feedback is taken from   |
| `NEG_APPROX` | 0            | use the cheap negate (see `approx` above)           |
| `ISYM`       | 0            | input is already symmetric, skip the `f_sym` clamp  |
| `DEBUG`      | 0            | reserved; no debug logic at present, and nothing is emitted |

`AW` must be greater than or equal to `OW`, `IW` and `LW`; `OW` must be at least 2; and `LW` must be
at least 2, since the leak negates a signed `LW`-bit word and a one-bit one negates to zero either
way. `LW` defaults to `OW>>1`, so `OW=2` and `OW=3` need an explicit `LW`. Each is checked at
generation time; a violation reports the offending value and writes no file.

## Make targets

| Target                 | Does                                                                      |
|------------------------|---------------------------------------------------------------------------|
| `gen` (default)        | elaborate every top in `TOPS`                                             |
| `iir`, `intg`          | elaborate one top                                                         |
| `vlint`, `vlint-<top>` | lint, with `VERILINT=verilator` (default) or `slang`                      |
| `pylint`               | `py_compile` the generated Python modules                                 |
| `vlint-tb`             | lint each function testbench with `-Wall`, in every swept configuration   |
| `pytest`               | the Q format library in `lib/tests`; no simulator                         |
| `lint`                 | `pylint`, `vlint` and `vlint-tb`                                          |
| `sim`                  | run `SIM_TOP` (default `tb_intg`) once under `SIMULATOR`; `DUMP=1` traces |
| `test`                 | `pytest`, plus every function and module under `TB_SIMS`; use `-j`        |
| `test-extra`           | re-run the whole suite under verilator                                    |
| `test-smoke`           | every function and module in its default configuration, both simulators   |
| `test-<name>`          | one function or module, e.g. `test-f_round`, `test-intg`                  |
| `plot`                 | `make plot FUNC=f_shright [CFG=IW=8:CW=4] [OUT=x.png]`                    |
| `clean`                | remove `build/` and the simulator intermediates                           |

Generation-time options go in `EXTRA_FLAGS_<top>`:

```sh
make intg EXTRA_FLAGS_intg='-p OW=12 -p IW=6 -p ISYM=1'
```

Manually with everything in one directory, the same options are `-p` arguments:

```sh
genesispy --input modules/intg.svpy --top intg \
          --inc-path funcs --py-path lib --out-dir build/intg -p OW=12 -p IW=6
```

`--py-path lib` is required: the templates import `vexpr` and `qfmt` from there, and without it
generation stops at `ModuleNotFoundError: No module named 'vexpr'`.

This writes `build/intg/intg.sv`, plus `intg.vlist` (file list), `intg.vlist.verif`,
`intg.depend` (dependency list, which tracks the included functions) and `genesispy_clean.sh`.
`modules/iir.svpy` needs no `--inc-path`; it includes nothing.

A run that gives no `--raw-dir` writes its Python intermediates to `genesis_raw/` in the current
directory, whether it succeeds or fails; `.gitignore` covers that.

## Tests

`verif/funcs/` holds a self-checking testbench per function: it includes the function under test,
sweeps its whole input space, and compares the result against a reference written in 64-bit
arithmetic. The function works in `IW` bits with slices and two's-complement tricks; the reference
works in 64 bits where nothing overflows. They agree only if the bit manipulation is right.
`verif/modules/` holds one per module, which instantiates it and steps a 64-bit reference alongside,
one clock at a time. There are no vector files. The check happens inside the simulator.

```sh
make test                  # pytest, then every function and module under iverilog; use -j
make test-f_round          # one function
make pytest                # the Q format library, no simulator involved
make test test-extra       # and again under verilator
make -j8 test-smoke        # default configuration only, both simulators
```

`make test` runs iverilog only: it builds in about a sixth of verilator's wall time over the sweep,
and being four-state it is the only one that catches an X coming out of a function, where verilator
turns an X into 0 and notices only when 0 differs from the expected value. `TB_SIMS` picks the
simulators explicitly. Each writes under its own directory, so `make test test-extra` keeps both
sets of logs.

`test-smoke` is the quick check: it runs each function and module once, in its default
configuration, under both simulators, and skips the sweeps entirely. `SMOKE_SIMS` picks the
simulators, and one rule per name means `-j` runs them at once.

The `SWEEP_<name>` tables in `verif/sweeps.mk` list the configurations to try, written per function
because several reject parts of the space. `NEG_<name>` lists configurations the generator must
reject: `make test` fails if one of them generates instead of erroring.

### Waveforms

`tb_util.svpy` wraps its `$dumpvars` in `` `ifdef DUMP ``, so a waveform costs nothing unless asked
for. `verif/run-tb.sh <name> <config> <simulator> -dump` builds with `DUMP` defined and leaves
`dump.vcd` beside the run logs; `make sim DUMP=1` does the same for an interactive run and writes
`dump.vcd` in the repo root, where `make cleansim` removes it. Ask for one on a module testbench: a
function testbench has no clock and finishes at time zero, so its trace holds only the last case.

### Expected failures

`XFAIL_<name>` in `verif/sweeps.mk` lists configurations known to disagree with the function or
module it names. A listed configuration reports `XFAIL` when it mismatches and does not fail the
run; one that passes reports `XPASS` and does fail it, so fixing a function forces the table to be
updated. An entry excuses a wrong answer, never a missing one: a listed configuration that fails to
generate, build, or run reports `ERROR` and still fails the run. `verif/run-tb.sh` separates the two
by exit status, taken from the `PASS` or `FAIL` line the testbench prints rather than the
simulator's own exit code, because verilator aborts with 134 on `$fatal` while iverilog exits 1.

| Status | Meaning                                          |
|--------|--------------------------------------------------|
| 0      | matches the reference                            |
| 1      | ran and mismatched -- the only `XFAIL`-able case |
| 2      | usage error                                      |
| 3      | generation failed                                |
| 4      | build failed                                     |
| 5      | build produced a verilator warning               |
| 6      | ran but reported neither PASS nor FAIL           |

The tables are currently empty. Every function and module matches its reference on every
configuration.

### Plotting

Each testbench can write a CSV of its inputs, its result and the reference, gated behind a plusarg
so `make test` stays quiet. `verif/plot.py` draws the result solid and the reference dashed, one
pair of lines per distinct value of the leading input columns, and marks differences.
A data file including multiple series is unreadable all at once, so `--key` narrows it:

```sh
make plot FUNC=f_shright CFG=IW=8:CW=2 OUT=shr.png
verif/run-tb.sh f_shright IW=8:CW=2 verilator -plot
verif/plot.py build/tb_f_shright/IW8_CW2/verif/verilator/data.csv --key frac=3 --out shr.png
```

Manually, `verif/run-tb.sh` takes `-data` to write the file and `-plot` to write it and open the plot.
Plotting needs matplotlib, which `make test` does not import: `pip install -r verif/requirements.txt`.
