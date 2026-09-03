# dsp-gpy verification

[dsp-gpy](../README.md) | [functions](functions.md) | [modules](modules.md) | [lib](lib.md)

`verif/functions/` holds a self-checking testbench per function: it includes the function under
test, sweeps its whole input space, and compares the result against a reference written in 64-bit
arithmetic. The function works in `IW` bits; the reference works in 64, where nothing overflows, so
the two agree only if the bit manipulation is right. `verif/modules/` holds one per module, which
instantiates it and steps a 64-bit reference alongside, one clock at a time.

```sh
make test                  # pytest, then every function and module under iverilog; use -j
make test-f_round          # one function
make pytest                # the lib/ tests, no simulator involved
make test test-extra       # and again under verilator
make -j8 test-smoke        # default configuration only, both simulators
```

`make test` runs iverilog only. It builds in about a sixth of verilator's wall time over the sweep,
and, being four-state, it catches an X coming out of a function; verilator turns an X into 0 and
notices only when 0 differs from the expected value. `TB_SIMS` picks the simulators explicitly. Each
writes under its own directory, so `make test test-extra` keeps both sets of logs.

`test-smoke` is the quick check: it runs each function and module once, in its default
configuration, under both simulators, and skips the sweeps. `SMOKE_SIMS` picks the
simulators, and one rule per name means `-j` runs them at once. Its output goes under
`build/smoke/`, apart from the sweep's.

## One run at a time

`verif/run-tb.sh` generates, builds and runs a single testbench in a single configuration. `make`
calls it once per configuration; call it by hand to examine one failing case.

```sh
verif/run-tb.sh <name> <config> <simulator|gen> [-data] [-plot] [-dump]

verif/run-tb.sh f_round IW=8:OW=6 verilator
verif/run-tb.sh f_negate default iverilog -data
verif/run-tb.sh intg default gen          # elaborate only, leaving tb.vf
```

`<name>` is the function or module, without the `tb_` prefix. `<config>` is the generation
parameters joined by `:`, or the word `default` for none. These are the testbench's parameters, not
the [function options](functions.md).

Output goes to `build/tb_<name>/<config tag>/<simulator>/`, the tag being the configuration with
`:` turned into `_` and `=` dropped. `BUILDDIR` moves that tree, and must be relative to the
repository root; `run-tb.sh` rejects an absolute path. Two runs of the same name, configuration and
simulator share the tree, so concurrent jobs need one `BUILDDIR` each.

## Sweep tables

`verif/sweeps.mk` says what gets tested. `FUNCS` and `MODS` name the testbenches; the Makefile
builds one `test-<name>` target per entry. Three tables per name, all optional:

| Table          | Holds                                                                        |
|----------------|------------------------------------------------------------------------------|
| `SWEEP_<name>` | configurations to run, each expected to match its reference                  |
| `NEG_<name>`   | configurations the generator must reject; `make test` fails if one generates |
| `XFAIL_<name>` | configurations known to mismatch, excused from failing `make test`           |

Each entry is one word: generation parameters joined by `:`, or `default`. The sweeps are written
per function because several functions reject parts of the space.

## Expected failures

A configuration listed in `XFAIL_<name>` reports `XFAIL` when it mismatches and does not fail the
run; one that passes reports `XPASS` and does fail it, so fixing a function forces the table to be
updated. An entry excuses a wrong answer, never a missing one: a listed configuration that fails to
generate, build, or run reports `ERROR` and still fails the run. `run-tb.sh` separates the two by
exit status, taken from the `PASS` or `FAIL` line the testbench prints rather than the simulator's
own exit code, because verilator aborts with 134 on `$fatal` while iverilog exits 1.

| Status | Meaning                                                                                 |
|--------|-----------------------------------------------------------------------------------------|
| 0      | matches the reference                                                                   |
| 1      | ran and mismatched -- the only `XFAIL`-able case                                        |
| 2      | usage error, including a `genesispy` that is not on `PATH`                              |
| 3      | generation failed                                                                       |
| 4      | build failed                                                                            |
| 5      | build produced a verilator warning                                                      |
| 6      | ran but reported no usable result: neither `PASS` nor `FAIL`, or a `PASS` over no cases |
| 7      | ran and passed, but a parameter the run asked for is missing from the `PASS` line       |
| 8      | generation crashed with a Python traceback, rather than rejecting the configuration     |

## Waveforms

`verif/common/tb_util.svpy` wraps its `$dumpvars` in `` `ifdef DUMP ``, so a waveform costs nothing
unless asked for. `verif/run-tb.sh <name> <config> <simulator> -dump` builds with `DUMP` defined and
leaves `dump.vcd` beside the run logs; `make sim DUMP=1` does the same for an interactive run and
writes `dump.vcd` in the repository root, where `make cleansim` removes it. Ask for one on a module
testbench: a function testbench has no clock and finishes at time zero, so its trace holds only the
last case.

## Plotting

Each function testbench can write a CSV of its inputs, its result and the reference, gated behind
a plusarg so `make test` stays quiet. `verif/plot.py` draws the result solid and the reference
dashed, one pair of lines per distinct value of the leading input columns, and marks differences.
`--key` selects one series from a file holding several:

```sh
make plot FUNC=f_shright CFG=IW=8:CW=2 OUT=shr.png
verif/run-tb.sh f_shright IW=8:CW=2 verilator -plot
verif/plot.py build/tb_f_shright/IW8_CW2/verilator/data.csv --key frac=3 --out shr.png
```

`run-tb.sh` takes `-data` to write the file and `-plot` to write it and open the plot. Neither
works with `gen`, which runs no simulator, and nor does `-dump`. Plotting needs matplotlib, which
`make test` does not import: `pip install -r requirements.txt`.
