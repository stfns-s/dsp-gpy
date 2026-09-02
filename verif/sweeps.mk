# Test tables for dsp-gpy, included by the Makefile.
#
# FUNCS and MODS name what gets tested; the Makefile builds one test-<name> target per
# entry. Three tables per name, all optional and all keyed by that name:
#
#   SWEEP_<name>  configurations to run, each expected to match its reference
#   NEG_<name>    configurations the generator must reject
#   XFAIL_<name>  configurations known to mismatch, excused from turning make test red

MODS  ?= intg iir dotp

FUNCS ?= f_abs f_log2 f_logmult f_negate f_qcvt f_round f_s2sm f_sat f_sh f_shleft \
         f_shright f_slogmult f_sm2s f_sx f_sym f_trunc f_umod

# One configuration per word: generation parameters joined by ':', or 'default'.
SWEEP_f_abs      := default IW=2 IW=3 IW=5 IW=16 IW=8:APPROX=1 IW=8:ISYM=1 \
                    IW=8:APPROX=1:ISYM=1 IW=5:APPROX=1:ISYM=1
SWEEP_f_negate   := default IW=2 IW=3 IW=5 IW=16 IW=8:APPROX=1 IW=8:ISYM=1 \
                    IW=8:APPROX=1:ISYM=1 IW=5:APPROX=1:ISYM=1
SWEEP_f_sym      := default IW=2 IW=3 IW=5 IW=16
SWEEP_f_sx       := default IW=12:OW=13 IW=8:OW=9 IW=2:OW=8 IW=5:OW=6 IW=1:OW=2
SWEEP_f_sat      := default IW=8:OW=2 IW=8:OW=3 IW=8:OW=7 IW=5:OW=3 IW=8:OW=6:OSYM=1 \
                    IW=5:OW=3:OSYM=1 IW=16:OW=8 IW=5:OW=8 IW=2:OW=3
SWEEP_f_trunc    := default IW=8:OW=2 IW=8:OW=3 IW=8:OW=6:OSYM=1 IW=5:OW=2 IW=16:OW=8 \
                    IW=4:OW=6 IW=8:OW=8
SWEEP_f_round    := default IW=8:OW=2 IW=8:OW=3 IW=8:OW=6:OSYM=1 IW=5:OW=2 IW=16:OW=8 \
                    IW=8:OW=8 IW=8:OW=9 IW=8:OW=8:OSYM=1
# f_s2sm and f_sm2s take w = min(iwidth, owidth) and give both ports that width, so an
# OW above IW is a no-op and an OW below IW narrows the input to match. Neither can
# convert between widths, and a configuration differing only in the wider of the two
# widths repeats one already listed; what these entries vary is w itself and SM_PLUS.
SWEEP_f_s2sm     := default IW=3:OW=3 IW=16:OW=16 IW=5:OW=5 IW=2:OW=2 IW=8:OW=8:SM_PLUS=0 \
                    IW=8:OW=5:SM_PLUS=0
SWEEP_f_sm2s     := default IW=3:OW=3 IW=16:OW=16 IW=5:OW=5 IW=2:OW=2 IW=8:OW=8:SM_PLUS=0 \
                    IW=8:OW=5:SM_PLUS=0
SWEEP_f_umod     := default IW=2 IW=3 IW=5
SWEEP_f_shleft   := default IW=8:CW=1 IW=8:CW=2 IW=8:CW=4:OSYM=1 IW=5:CW=3 IW=5:CW=3:OSYM=1 \
                    IW=3:CW=2
SWEEP_f_shright  := default IW=8:CW=1 IW=8:CW=2 IW=5:CW=3 IW=3:CW=2 IW=8:CW=4:OSYM=1 \
                    IW=5:CW=3:OSYM=1
SWEEP_f_sh       := default IW=8:CW=1 IW=8:CW=2 IW=8:CW=3 IW=5:CW=3 IW=3:CW=2 IW=16:CW=4
SWEEP_f_log2     := default IW=2 IW=3 IW=5 IW=16 IW=8:ISYM=1 IW=8:APPROX=0 IW=8:LFRAC=1 \
                    IW=8:LFRAC=2 IW=5:LFRAC=2 IW=16:LFRAC=2 IW=8:LFRAC=4 \
                    IW=8:LFRAC=2:ISYM=1 IW=8:LFRAC=2:APPROX=0
SWEEP_f_slogmult := default AW=5:BW=5 AW=8:BW=4 AW=4:BW=8 AW=3:BW=3 AW=8:BW=8:ISYM=1 \
                    AW=8:BW=8:ZDET=0 AW=8:BW=8:OAPPROX=1 AW=8:BW=8:IAPPROX=0
SWEEP_f_logmult  := default AW=5:BW=5 AW=8:BW=4 AW=8:BW=8:ZDET=1 AW=8:BW=8:ISYM=1 \
                    AW=8:BW=8:OSM=1 AW=8:BW=8:SIGN_ONLY=1 AW=8:BW=8:SIGN_ONLY=1:OSM=1 \
                    AW=8:BW=8:OAPPROX=1 AW=8:BW=8:ANTILOG=0:OAPPROX=1 \
                    AW=8:BW=8:IAPPROX=0 AW=8:BW=8:ANTILOG=0 AW=8:BW=8:ANTILOG=0:ZDET=1 \
                    AW=8:BW=8:ANTILOG=0:OSM=1 AW=8:BW=8:ANTILOG=0:ALFRAC=1:BLFRAC=1 \
                    AW=8:BW=8:ANTILOG=1:ALFRAC=1:BLFRAC=1
# The UQ entries widen an unsigned output past the input range, where the largest output
# code needs one bit more than the output width to sit in the signed accumulator.
SWEEP_f_qcvt     := default Q_IN=Q4.12:Q_OUT=Q2.6:ROUND_MODE=half_even \
                    Q_IN=UQ8.8:Q_OUT=UQ4.4:ROUND_MODE=half_up Q_IN=Q3.5:Q_OUT=Q3.9 \
                    Q_IN=Q4.4:Q_OUT=UQ4.4 Q_IN=UQ4.4:Q_OUT=Q4.4 Q_IN=Q4.4:Q_OUT=Q4.4:OSYM=1 \
                    Q_IN=Q4.4:Q_OUT=Q2.2:ROUND_MODE=half_up \
                    Q_IN=Q8.8:Q_OUT=Q1.1:ROUND_MODE=half_even \
                    Q_IN=Q-1.5:Q_OUT=Q0.5 Q_IN=Q1.6:Q_OUT=Q-1.5:ROUND_MODE=half_up \
                    Q_IN=Q-2.6:Q_OUT=Q-1.4:ROUND_MODE=half_even Q_IN=UQ0.4:Q_OUT=UQ-1.3 \
                    Q_IN=Q3.-1:Q_OUT=Q3.0 Q_IN=Q6.-2:Q_OUT=Q4.-2:OSYM=1 Q_IN=Q0.1:Q_OUT=Q0.1 \
                    Q_IN=Q2.5:Q_OUT=Q7.5 Q_IN=UQ4.4:Q_OUT=UQ5.4 Q_IN=UQ4.4:Q_OUT=UQ6.4 \
                    Q_IN=UQ4.4:Q_OUT=UQ12.4 Q_IN=UQ4.4:Q_OUT=UQ12.4:OSYM=1 \
                    Q_IN=UQ4.4:Q_OUT=UQ12.2:ROUND_MODE=half_up \
                    Q_IN=UQ4.4:Q_OUT=UQ12.2:ROUND_MODE=half_even \
                    Q_IN=Q4.4:Q_OUT=Q2.4:SRC_LO=-16:SRC_HI=40 \
                    Q_IN=Q4.4:Q_OUT=Q2.4:SRC_LO=-64:SRC_HI=20 \
                    Q_IN=Q4.4:Q_OUT=Q3.2:ROUND_MODE=half_up:SRC_LO=-20:SRC_HI=20 \
                    Q_IN=Q4.4:Q_OUT=Q4.2:SRC_LO=-64:SRC_HI=60:SATURATE=0 \
                    Q_IN=Q4.12:Q_OUT=Q2.6:ROUND_MODE=half_away \
                    Q_IN=Q4.12:Q_OUT=Q2.6:ROUND_MODE=to_zero \
                    Q_IN=UQ8.8:Q_OUT=UQ4.4:ROUND_MODE=half_away \
                    Q_IN=UQ8.8:Q_OUT=UQ4.4:ROUND_MODE=to_zero \
                    Q_IN=Q4.4:Q_OUT=Q4.3:ROUND_MODE=half_even \
                    Q_IN=Q4.4:Q_OUT=Q4.3:ROUND_MODE=half_away \
                    Q_IN=Q4.4:Q_OUT=Q4.3:ROUND_MODE=to_zero \
                    Q_IN=Q4.4:Q_OUT=Q2.2:ROUND_MODE=half_away:OSYM=1 \
                    Q_IN=Q-2.6:Q_OUT=Q-1.4:ROUND_MODE=half_away \
                    Q_IN=Q4.4:Q_OUT=Q3.2:ROUND_MODE=to_zero:SRC_LO=0:SRC_HI=60 \
                    Q_IN=Q4.4:Q_OUT=Q4.4:ROUND_MODE=to_zero \
                    Q_IN=Q3.5:Q_OUT=Q3.9:ROUND_MODE=half_away

# dotp. Per-tap lists are comma-spelled and split by the testbench; widths are derived, so
# a configuration names formats and shape only. The per-tap defaults are lists of 8 and only
# broadcast at N_TAPS=8, so an entry at another tap count restates both: UNIF does that, and
# UNIF_C and UNIF_T drop the one the entry sets itself. The sweep covers one tap, one group,
# unequal groups, per-tap coefficient and trim formats from rename through fractional-only to
# clipping, an empty PIPE, each of its four stages alone and four combinations of them, every
# rounding mode on each step, TRMSMPL_SYM, and RESULT_SYM, ISYM_SMPL and ISYM_COEF at both
# polarities, two eight-tap entries and one N_TAPS=9 (the tabulated corner-mask path). The
# first entry names no parameter at all, so it is dotp's own defaults that run.
# Q_RESULT=Q8.10 is Q_SUM of the default, so its output requant is a rename.
UNIF   := Q_COEF=Q1.5:Q_TRMSMPL=Q1.5
UNIF_C := Q_TRMSMPL=Q1.5
UNIF_T := Q_COEF=Q1.5
SWEEP_dotp := default N_TAPS=1:N_GROUPS=1:$(UNIF) N_TAPS=2:N_GROUPS=2:$(UNIF) \
              N_TAPS=5:N_GROUPS=2:TAP_GROUPS=0,0,0,1,1:$(UNIF) \
              N_TAPS=4:Q_COEF=Q1.5,Q1.3,Q2.5,Q-1.4:$(UNIF_C) \
              N_TAPS=4:Q_TRMSMPL=Q1.5,Q1.4,Q1.2,Q1.1:$(UNIF_T) \
              N_TAPS=4:Q_TRMSMPL=Q1.5,Q0.5,Q-1.5,Q-2.5:TRMSMPL_ROUND=trunc:$(UNIF_T) \
              N_TAPS=4:Q_TRMSMPL=Q1.5,Q0.5,Q-1.4,Q1.1:TRMSMPL_ROUND=half_even:PROD_ROUND=half_even:$(UNIF_T) \
              N_TAPS=4:Q_TRMSMPL=Q0.4:TRMSMPL_SYM=1:$(UNIF_T) N_TAPS=4:TRMSMPL_SYM=1:ISYM_SMPL=1:$(UNIF) \
              N_TAPS=4:ISYM_SMPL=0:ISYM_COEF=0:PROD_ROUND=half_up:$(UNIF) N_TAPS=4:PROD_FRAC=10:$(UNIF) \
              N_TAPS=4:PROD_FRAC=6:RESULT_ROUND=trunc:Q_RESULT=Q3.4:$(UNIF) \
              N_TAPS=4:RESULT_ROUND=half_even:RESULT_SYM=0:$(UNIF) Q_RESULT=Q8.10 \
              N_TAPS=4:N_GROUPS=1:PIPE=none:$(UNIF) N_TAPS=4:PIPE=trmsmpl:$(UNIF) \
              N_TAPS=4:PIPE=prod:$(UNIF) N_TAPS=4:PIPE=groups:$(UNIF) \
              N_TAPS=4:PIPE=result:$(UNIF) N_TAPS=4:PIPE=trmsmpl,prod:$(UNIF) \
              N_TAPS=4:PIPE=trmsmpl,prod,groups:$(UNIF) \
              N_TAPS=3:N_GROUPS=2:$(UNIF) N_TAPS=2:N_GROUPS=1:$(UNIF) \
              N_TAPS=4:PIPE=trmsmpl,prod,groups,result:$(UNIF) \
              N_TAPS=6:N_GROUPS=2:PARENTH=1:PIPE=groups,result:$(UNIF) \
              N_TAPS=8:N_GROUPS=3:Q_COEF=Q1.5,Q1.3,Q2.5,Q-1.4,Q1.5,Q1.2,Q3.5,Q0.5:Q_TRMSMPL=Q1.5,Q1.4,Q1.2,Q1.1,Q0.5,Q-1.5,Q1.5,Q1.3:PIPE=trmsmpl,prod,groups \
              N_TAPS=9:N_GROUPS=4:PIPE=trmsmpl,prod,groups:$(UNIF) \
              N_TAPS=4:Q_TRMSMPL=Q1.5,Q0.5,Q-1.4,Q1.1:TRMSMPL_ROUND=half_away:PROD_ROUND=to_zero:$(UNIF_T)

# One per rejection dotp makes, in the order it checks them: N_TAPS, a list of the wrong
# length (the testbench passes it through unchanged), an unknown PIPE stage and one named
# twice, Q_TRMSMPL with more fractional bits, more integer bits, other signedness than
# Q_SMPL, PROD_FRAC above the cap, N_GROUPS above the tap count and below 1, a TAP_GROUPS
# index out of range and an empty group, an unsigned Q_SMPL, Q_COEF and Q_RESULT, and a bad
# mode on each step.
NEG_dotp := N_TAPS=0 N_TAPS=4:Q_COEF=Q1.5,Q1.3:$(UNIF_C) PIPE=bogus PIPE=prod,prod \
            Q_TRMSMPL=Q1.7 Q_TRMSMPL=Q2.5 \
            Q_TRMSMPL=UQ1.5 PROD_FRAC=12 N_GROUPS=9 N_GROUPS=0 \
            N_GROUPS=2:TAP_GROUPS=0,0,0,0,0,0,0,2 N_GROUPS=2:TAP_GROUPS=0,0,0,0,0,0,0,0 \
            Q_SMPL=UQ1.5:Q_TRMSMPL=UQ1.5 Q_COEF=UQ1.5 \
            Q_RESULT=UQ6.5 TRMSMPL_ROUND=nearest PROD_ROUND=up RESULT_ROUND=floor

# intg. EXH=1 adds a sweep of every input vector against the walked accumulator state
# and reports how many states it reached; it needs a configuration small enough to
# finish, which the template enforces. EXH_MIN is the count that sweep must reach, and
# turns the coverage into a check instead of a number nothing reads.
#
# The walk reaches every state only when some legal shift puts a term on the
# accumulator's least significant bit. The update places the input in the top IW bits and
# shifts right by mu, so its lsb sits at AW-IW-mu; the leak places the top LW bits and
# shifts by lk_mu, giving AW-LW-lk_mu. lk_mu > mu > 0 bounds mu at 2**MW-2 and lk_mu at
# 2**MW-1, and AW defaults to IW+2**MW, so at the default AW the update's lsb stops at 2
# and only the leak can reach zero -- which needs AW-LW <= 2**MW-1, that is LW >= IW+1.
# AW=5 below reaches it by lowering AW, and is the only entry here that visits every
# state; the default-AW entries have LW = IW and stop at half. NEG_APPROX loses three
# more states, because an approximate negation never produces the value it folds away.
SWEEP_intg := default OW=4:IW=2:MW=2 OW=8:IW=4:MW=2 OW=12:IW=6:MW=3 OW=16:IW=8:MW=4 \
              OW=8:IW=4:MW=4:AW=12 OW=8:IW=4:MW=4:LW=2 OW=8:IW=4:MW=4:LW=8 \
              NEG_APPROX=1 ISYM=1 OW=6:IW=3:MW=2 NEG_APPROX=1:ISYM=1 \
              OW=4:IW=2:MW=2:EXH=1:EXH_MIN=32 OW=4:IW=2:MW=2:AW=5:EXH=1:EXH_MIN=32 \
              OW=4:IW=2:MW=2:ISYM=1:EXH=1:EXH_MIN=32 \
              OW=4:IW=2:MW=2:NEG_APPROX=1:EXH=1:EXH_MIN=29

# One per check that rejects a configuration, in table order: the module's AW >= OW,
# OW >= 2, AW >= IW, AW >= LW and LW >= 2, then the testbench's own MW >= 2 (lk_mu > mu > 0
# needs two values above zero), the two bounds of its 64-bit reference, and its two EXH
# size guards. LW defaults to OW>>1, so OW=3 and OW=2 both leave a one-bit leak word, whose
# signed negation is zero for either value it holds. The EXH pair is ordered: the default
# configuration is small enough for AW but far too large for the vector count, and the AW
# entry keeps the vector count small so the AW guard is the one that fires.
NEG_intg := OW=8:IW=4:MW=1 OW=1 OW=2:IW=8:AW=4 OW=4:IW=2:MW=2:AW=6:LW=8 OW=3 OW=2 \
            OW=4:IW=2:MW=1 OW=4:IW=2:MW=6:AW=20 OW=4:IW=2:MW=2:AW=64 EXH=1 \
            OW=4:IW=2:MW=2:AW=23:EXH=1

# iir. IW/OW/MW are generation-time parameters of the module. The testbench declares them
# under the same names and hands them to unique_inst, so each configuration gets its own
# uniquified module and the DUT instance carries no parameter overrides. mu=0 is never
# driven: the module constrains mu > 0, since above a filter factor of one the accumulator
# provably overflows. EXH_MIN is the accumulator state count the exhaustive sweep must
# reach, as it is for intg. The filter converges toward its input, so the states at the
# two ends of the range are reached only by the transient a single vector stands for, and
# the walk settles into the middle: 242 of 256 at IW=4, and the same shortfall of 14 at
# each width below it.
SWEEP_iir := default ARST=0 IW=4:OW=4:MW=2 IW=4:OW=6:MW=2 IW=8:OW=4:MW=4 \
             IW=8:OW=24:MW=4 IW=2:OW=2:MW=1 IW=12:OW=12:MW=3 IW=16:OW=8:MW=5 \
             IW=4:OW=4:MW=2:EXH=1:EXH_MIN=242 IW=3:OW=3:MW=2:EXH=1:EXH_MIN=114 \
             IW=2:OW=2:MW=2:EXH=1:EXH_MIN=50 \
             IW=4:OW=4:MW=2:ARST=0:EXH=1:EXH_MIN=242 IW=4:OW=6:MW=2:EXH=1:EXH_MIN=242

# One per width check the module makes, then the testbench's own. A one-bit signed input
# has no magnitude bit under its sign; MW below 1 leaves the mu port with no bits; and OW
# above IW+2**MW would slice below the accumulator's least significant bit. The testbench
# then bounds its 64-bit reference twice, and guards the EXH sweep twice: the default
# configuration is small enough for W but needs far too many clocks, and the W entry pins
# EXH_HOLD to keep the clock count small so the W guard is the one that fires.
NEG_iir := IW=1 MW=0 OW=0 IW=4:OW=9:MW=2 IW=2:OW=2:MW=6 IW=32:OW=8:MW=5 EXH=1 \
           IW=7:OW=7:MW=4:EXH=1:EXH_HOLD=1

# Configurations the generator must reject: f_sat has nothing to saturate when the
# widths are equal, and f_sx nothing to extend when the output is no wider; both error
# out rather than emitting an empty slice. f_sat and f_round derive the output width as
# iwidth-1 when the requested one is no narrower, so IW=1 leaves them nothing to return.
NEG_f_sat   := IW=8:OW=8 IW=1:OW=2
NEG_f_sx    := IW=8:OW=8 IW=8:OW=4
NEG_f_round := IW=1:OW=2

# A zero-width output has no sign bit to hold the truncated value. The testbench rejects
# it first: it derives the reference output range from OW before it includes f_trunc.
NEG_f_trunc := OW=0

# Sign magnitude needs a sign bit and at least one magnitude bit, so the width the two
# conversions share -- the narrower of IW and OW -- must be at least 2.
NEG_f_s2sm := IW=8:OW=1
NEG_f_sm2s := IW=8:OW=1

# A zero-width shift control has no bits to shift by: all three would part-select
# sh[-1:0], and f_sh would size its accumulator from 2**(cwidth-1), which is not an
# integer at cwidth=0. CW=1 is legal and swept.
NEG_f_sh      := CW=0
NEG_f_shleft  := CW=0
NEG_f_shright := CW=0

# f_log2 needs a sign bit and at least one magnitude bit, and its reference caps lfrac
# where generation cost stops being worth it. Both multipliers take the log of an
# input, so each width they log has the same lower bound. f_qcvt rejects a malformed Q
# string, an unknown rounding mode, and a format with no bits in it. A signed format
# with no integer bit (Q0.1, Q-1.5) is accepted: the sign lives in the width, not in m.
# The SRC_LO/SRC_HI entries name the source codes that can arrive, so only the clamp end
# they reach is emitted: high only, low only, neither; the SATURATE=0 entry is accepted
# because its codes cannot reach a clamp, and rejected in NEG where they can, as is a
# source code outside the input format.
NEG_f_log2     := IW=1 LFRAC=13
NEG_f_logmult  := AW=1 BW=1
NEG_f_slogmult := BW=1
NEG_f_qcvt     := Q_IN=X4.4 ROUND_MODE=nearest Q_OUT=Q0.0 Q_IN=Q2.-2 \
                  Q_IN=Q4.4:Q_OUT=Q2.4:SATURATE=0 Q_IN=Q4.4:Q_OUT=Q2.2:SRC_LO=-200

# Configurations known to mismatch. A listed configuration that MISMATCHES reports XFAIL
# and does not turn make test red; one that PASSES reports XPASS and does, so settling a
# finding forces this table to be updated. A listed configuration that fails to generate,
# build, or run reports ERROR and still turns make test red -- XFAIL excuses a wrong
# answer, never a missing one. Empty: nothing is known-broken.
