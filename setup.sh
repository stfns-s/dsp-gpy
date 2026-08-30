# Put genesispy on PATH for this shell.
#
#     source setup.sh
#
# genesispy is expected in a checkout beside this repo. Point elsewhere with:
#
#     GENESISPY_HOME=/path/to/genesispy source setup.sh
#
# No `set -euo pipefail` here on purpose: this runs in your interactive shell,
# where -e would kill the shell on the next unrelated error.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "setup.sh: source this, do not run it:  source ${0}" >&2
    exit 2
fi

_vpy_setup() {
    local repo="$1"
    local bindir

    if [[ -n "${GENESISPY_HOME:-}" ]]; then
        bindir="${GENESISPY_HOME%/}/bin"
    else
        bindir="$(dirname "$repo")/genesispy-port/genesispy/bin"
    fi

    if [[ ! -x "${bindir}/genesispy" ]]; then
        echo "setup.sh: no genesispy at ${bindir}" >&2
        echo "setup.sh: set GENESISPY_HOME to the genesispy checkout and source again" >&2
        return 1
    fi

    case ":${PATH}:" in
    *":${bindir}:"*)
        echo "genesispy already on PATH: ${bindir}"
        return 0
        ;;
    esac

    export PATH="${bindir}:${PATH}"
    echo "genesispy on PATH: ${bindir}"
}

_vpy_here=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# The unsets are spelled out on both branches rather than stashed through a
# status variable, which would itself be left behind in the shell.
if _vpy_setup "$_vpy_here"; then
    unset -f _vpy_setup
    unset _vpy_here
    return 0
else
    unset -f _vpy_setup
    unset _vpy_here
    return 1
fi
