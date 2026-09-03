# Put genesispy on PATH for this shell.
#
#     source 0.setup.sh
#
# The search order is:
#
#   1. "${GENESISPY_HOME}/bin", when GENESISPY_HOME is set; it names a checkout root
#   2. a genesispy already on PATH, which is left as it is
#
# `pip install -r requirements.txt` installs the generator, which covers case 2.
# Point at a checkout of your own with:
#
#     GENESISPY_HOME=/path/to/genesispy source 0.setup.sh
#
# No `set -euo pipefail` here on purpose: this runs in your interactive shell,
# where -e would kill the shell on the next unrelated error.

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "0.setup.sh: source this, do not run it:  source ${0}" >&2
    exit 2
fi

_vpy_setup() {
    local bindir found

    if [[ -n "${GENESISPY_HOME:-}" ]]; then
        bindir="${GENESISPY_HOME%/}/bin"
        if [[ ! -x "${bindir}/genesispy" ]]; then
            echo "0.setup.sh: no genesispy at ${bindir}" >&2
            echo "0.setup.sh: GENESISPY_HOME must name a genesispy checkout root" >&2
            return 1
        fi
    else
        found="$(command -v genesispy 2>/dev/null)"
        if [[ -z "${found}" ]]; then
            echo "0.setup.sh: no genesispy on PATH, and GENESISPY_HOME is not set" >&2
            echo "0.setup.sh: run 'pip install -r requirements.txt', or set GENESISPY_HOME" >&2
            return 1
        fi
        echo "genesispy already on PATH: ${found}"
        return 0
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

# The unsets are spelled out on both branches rather than stashed through a
# status variable, which would itself be left behind in the shell.
if _vpy_setup; then
    unset -f _vpy_setup
    return 0
else
    unset -f _vpy_setup
    return 1
fi
