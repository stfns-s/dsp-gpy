# dsp-gpy

Fixed-point DSP building blocks for hardware, using
[genesispy](https://github.com/stfns-s/genesispy) templates.

## Requirements

The genesispy generator, which comes with the repository as a submodule at `ext/genesispy`.
`source 0.setup.sh` puts it on `PATH`.

```sh
git clone --recurse-submodules git@github.com:stfns-s/dsp-gpy.git
source 0.setup.sh
```

An existing clone populates the submodule with `git submodule update --init ext/genesispy`.

`0.setup.sh` takes the first of three: `${GENESISPY_HOME}/bin`, a `genesispy` already on `PATH`,
and `ext/genesispy/bin`. To use a checkout of your own instead of the submodule:

```sh
GENESISPY_HOME=/path/to/genesispy source 0.setup.sh
```

The rest are the tools the make targets run:

- `iverilog`, in 2012 mode: `make test`
- `verilator`: `make test-extra`, `make test-smoke`, `make plot`, `vlint-tb`, and `vlint` by default
- `xrun`, `vcs`, `vlog`: optional; `make sim SIMULATOR=<name>` drives them too
- `pytest`: the `lib/` tests
- matplotlib: `verif/plot.py`, installed with `pip install -r verif/requirements.txt`

## Documentation

| Document                      | Covers                                                              |
|-------------------------------|---------------------------------------------------------------------|
| [functions](doc/functions.md) | the arithmetic functions in `functions/` and the options each takes |
| [modules](doc/modules.md)     | `iir`, `intg` and `dotp`: what each does and how it is configured   |
| [verification](doc/verif.md)  | the testbenches, the sweep tables, `run-tb.sh`, waveforms and plots |
| [lib](doc/lib.md)             | the Q format, and `qfmt`, `vexpr` and `partition` call by call      |

This file covers the layout and the make targets only.

## Directory structure

```text
functions/        arithmetic functions, pulled in with include()
lib/              qfmt.py, vexpr.py and partition.py, imported by the templates; on --py-path
  tests/          pytest suite for the three
modules/          synthesizable modules, one top each
verif/
  functions/      tb_f_<name>.svpy, one testbench per function
  modules/        tb_<name>.svpy, one testbench per module
  common/         tb_util.svpy (fdiv, clamp, tb_sext, tb_check, data and report tasks) and
                  tb_ref_log2.svpy (64-bit f_log2 reference, shared by the three log tests)
  sweeps.mk       which configurations make test runs
  run-tb.sh       generate, build and run one testbench in one configuration
  plot.py         plot a data file
doc/              the four documents above
ext/genesispy/    the genesispy generator, a submodule
build/            everything generated; not in git
```

`build/` holds one directory per top and configuration, named after the genesispy top, and under it
one directory per simulator, for instance `build/tb_f_round/IW8_OW2/iverilog/`:

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

An elaborate-only run lands in `gen/`, in place of a simulator directory; `make sim` reads its file
list from there and writes its own output to `sim/` beside it.

Each simulator gets a tree of its own. The generated Verilog is the same in each, but no two runs
write the same file, which is what lets `make -j test test-extra` run both simulators over one
configuration at once.

## Make targets

| Target                            | Does                                                                 |
|-----------------------------------|----------------------------------------------------------------------|
| `gen` (default)                   | elaborate every top in `TOPS`                                        |
| `iir`, `intg`, `dotp`             | elaborate one top                                                    |
| `vlint`, `vlint-<top>`            | lint, with `VERILINT=verilator` (default) or `slang`                 |
| `pylint`                          | `py_compile` the generated Python modules                            |
| `vlint-tb`, `vlint-tb-<f>`        | lint a function testbench with `-Wall`, in every swept configuration |
| `pytest`                          | the `lib/` tests; no simulator                                       |
| `lint`                            | `pylint`, `vlint` and `vlint-tb`                                     |
| `sim`                             | run `SIM_TOP` once under `SIMULATOR`; `DUMP=1` traces                |
| `test`                            | `pytest`, plus every function and module under `TB_SIMS`; use `-j`   |
| `test-extra`                      | re-run the whole suite under verilator                               |
| `test-smoke`, `test-smoke-<name>` | default configuration only, under `SMOKE_SIMS`                       |
| `test-<name>`                     | one function or module, e.g. `test-f_round`, `test-intg`             |
| `plot`                            | `make plot FUNC=f_shright [CFG=IW=8:CW=4] [OUT=x.png]`               |
| `cleangen`                        | remove `BUILDDIR`: elaboration output, test results and logs         |
| `cleansim`                        | remove the simulator intermediates                                   |
| `clean`                           | `cleangen` and `cleansim`                                            |
| `help`                            | the main targets, and the variables it lists with their values       |

`vlint-tb` skips the testbenches named in `VLINT_TB_SKIP`, currently `f_logmult` and `f_slogmult`.

| Variable     | Default                 | Is                                                     |
|--------------|-------------------------|--------------------------------------------------------|
| `TOPS`       | `iir intg dotp`         | which tops `gen` and `vlint` cover                     |
| `MODS`       | `intg iir dotp`         | which modules are tested                               |
| `FUNCS`      | every `functions/` file | which functions are tested                             |
| `TB_SIMS`    | `iverilog`              | simulators `test` runs                                 |
| `SMOKE_SIMS` | `iverilog verilator`    | simulators `test-smoke` runs                           |
| `SIMULATOR`  | `verilator`             | simulator `sim` runs                                   |
| `SIM_TOP`    | `tb_intg`               | testbench `sim` runs                                   |
| `SIM_CFG`    | `default`               | configuration `sim` runs it in                         |
| `VERILINT`   | `verilator`             | linter `vlint` uses; `slang` is the other              |
| `BUILDDIR`   | `build`                 | where everything generated goes; must be repo-relative |
| `DUMP`       | `0`                     | `1` makes `sim` write `dump.vcd`                       |

`MODS` and `FUNCS` come from `verif/sweeps.mk`; the rest from the Makefile.

Generation-time options go in `EXTRA_FLAGS_<top>`:

```sh
make intg EXTRA_FLAGS_intg='-p OW=12 -p IW=6 -p ISYM=1'
```

Manually with everything in one directory, the same options are `-p` arguments:

```sh
genesispy --input modules/intg.svpy --top intg \
          --inc-path functions --py-path lib --out-dir build/intg -p OW=12 -p IW=6
```

`--py-path lib` is required: the templates import `vexpr`, `qfmt` and `partition` from there, and
without it generation stops at `ModuleNotFoundError: No module named 'vexpr'`.

This writes `build/intg/intg.sv`, plus `intg.vlist` (file list), `intg.vlist.verif`,
`intg.depend` (dependency list, which tracks the included functions) and `genesispy_clean.sh`.
`modules/iir.svpy` needs no `--inc-path`; it includes nothing.

A run that gives no `--raw-dir` writes its Python intermediates to `genesis_raw/` in the current
directory, whether it succeeds or fails; `.gitignore` covers that.
