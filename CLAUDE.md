# CLAUDE.md

Rules for agents working in this repository. The README covers how the flow is built and run; this
file covers what not to do.

## Verification

- The check is `make -j8 test`, which runs iverilog. Quote the PASS count and the exit status.
- Never run `make test-extra` on your own initiative. It re-runs the whole sweep under verilator and
  is the user's call. One targeted `verif/run-tb.sh <name> <cfg> verilator` is fine when a change is
  verilator-specific.
- `run-tb.sh` forms its output path as `${REPO}/${BUILDDIR}/...`, so `BUILDDIR` must be relative to
  the repository root. An absolute path is joined anyway and the run lands somewhere unintended.
  Give each concurrent job its own repo-relative `BUILDDIR` under `build/`; two runs of the same
  name and configuration otherwise race on the shared generation directory.

## Writing SystemVerilog here

Both simulators have to accept every testbench, so two constructs are barred:

- No `continue` or `break` in a loop. Icarus Verilog 12.0 rejects both with `-g2012`; verilator
  accepts them, so the failure only appears on the second simulator. Use `if`/`else`.
- No function call inside a ternary (`?:`). Verilator 5.020 aborts with an internal fault when
  the calling function runs in a loop, which every testbench here does. Write
  `if (sign) ix = neg(ix);` instead of `ix = sign ? neg(ix) : ix;`. Plain operators in a
  ternary are fine.

In a clocked testbench, generate only legal stimulus. Applying an input and then skipping the check
does not stop the clock: the design consumes the input, the reference does not, and the two diverge
from that point on. Step over an excluded value in the loop, or map it to a legal one.
