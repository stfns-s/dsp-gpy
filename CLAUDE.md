# CLAUDE.md

Rules for agents working in this repository. The README covers how the flow is built and run; this
file covers what not to do.

## Environment

`genesispy` comes from `pip install -r requirements.txt`, which puts it on `PATH` in the
environment you installed it into. Check with `command -v genesispy` before invoking `make` or
`verif/run-tb.sh`; if it is missing, the install did not reach the active environment.

`source 0.setup.sh` is needed only to use a checkout of your own instead of the installed
generator. It takes the first of two: `${GENESISPY_HOME}/bin`, then a `genesispy` already on
`PATH`.

## Verification

- The check is `make -j8 test`, which runs iverilog. Quote the PASS count and the exit status.
- Never run `make test-extra` on your own initiative. It re-runs the whole sweep under verilator and
  is the user's call. One targeted `verif/run-tb.sh <name> <cfg> verilator` is fine when a change is
  verilator-specific.
- `BUILDDIR` must be relative to the repository root, and each concurrent job of the same name,
  configuration and simulator needs its own under `build/`; see
  [verification](doc/verif.md#one-run-at-a-time).

## Writing SystemVerilog here

Both simulators have to accept every testbench, so two constructs are barred:

- No `continue` or `break` in a loop. Icarus Verilog 12.0 rejects both with `-g2012`; verilator
  accepts them, so the failure only appears on the second simulator. Use `if`/`else`.
- No function call inside a ternary (`?:`) within a function or task. Verilator 5.020 aborts
  with an internal fault when the calling function runs in a loop, which every testbench here
  does. Write `if (sign) ix = neg(ix);` instead of `ix = sign ? neg(ix) : ix;`. Plain operators
  in a ternary are fine, and so is a call in a ternary in a continuous assignment, as in `intg`.

A testbench that drives an unpacked array port must hold the stimulus in one variable per element
and gather them into the array with continuous assignments, the way `tb_dotp` builds `sample`.
Verilator 5.020 raises no event for a procedural write to an unpacked-array element, so logic whose
only inputs are that array is evaluated once, at time zero, and holds. Logic that also reads a
scalar hides the defect, so only some configurations show it. Icarus is not affected.

In a clocked testbench, generate only legal stimulus. Applying an input and then skipping the check
does not stop the clock: the design consumes the input, the reference does not, and the two diverge
from that point on. Step over an excluded value in the loop, or map it to a legal one.

A function's formal is declared in the scope of the module that includes it. Six functions in
`functions/` name their input `x`: `f_abs`, `f_log2`, `f_negate`, `f_sat`, `f_sx` and `f_sym`. A
module with a port or net called `x` that includes one of them gets `VARHIDDEN` from verilator
under `-Wall`, and `make vlint` fails on it. The hide is harmless (inside the function `x` is the
argument) and slang does not report it; neither a different lifetime nor an ANSI port list removes
it. Either give the module's net another name, or rename the function's formal as `f_qcvt` does
with `qin`. No inline `lint_off`.
