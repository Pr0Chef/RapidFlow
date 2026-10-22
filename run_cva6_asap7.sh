#!/usr/bin/env bash
# Run CVA6 through OpenROAD-flow-scripts on asap7.
#
# Usage: ./run_cva6_asap7.sh [-s STAGE] [-H] [-c] [-j JOBS] [-h]
#   -s STAGE  last stage to run: synth | floorplan | place | cts | route | final   (default: synth)
#   -H        hierarchical synthesis (config_hier.mk, results in .../asap7/cva6/hier)
#   -c        clean previous asap7/cva6 results, logs and reports first
#   -j JOBS   parallel jobs for the flow (default: nproc)
#
# Design config: designs/asap7/cva6/config.mk (slang frontend, fakeram7 macros as blackboxes).
# Output: <flow>/{logs,results,reports}/asap7/cva6/<base|hier>, plus a timestamped log in ./run_logs/.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Flow directory: $ORFS_FLOW if set, else the vendored ./orfs/flow, else an ORFS clone next to this script.
if [ -n "${ORFS_FLOW:-}" ]; then FLOW="$ORFS_FLOW"
elif [ -d "$ROOT/orfs/flow" ]; then FLOW="$ROOT/orfs/flow"
else FLOW="$ROOT/OpenROAD-flow-scripts/flow"; fi
CONFIG="designs/asap7/cva6/config.mk"
STAGE=synth
CLEAN=0
VARIANT=base
JOBS="$(nproc)"

usage() { sed -n '2,11p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while getopts "s:Hcj:h" opt; do
  case "$opt" in
    s) STAGE="$OPTARG" ;;
    H) CONFIG="designs/asap7/cva6/config_hier.mk"; VARIANT=hier ;;
    c) CLEAN=1 ;;
    j) JOBS="$OPTARG" ;;
    h) usage 0 ;;
    *) usage 1 ;;
  esac
done

case "$STAGE" in
  synth)     TARGET=synth ;;
  floorplan) TARGET=floorplan ;;
  place)     TARGET=place ;;
  cts)       TARGET=cts ;;
  route)     TARGET=route ;;
  final)     TARGET=finish ;;
  *) echo "unknown stage: $STAGE" >&2; usage 1 ;;
esac

[ -f "$FLOW/$CONFIG" ] || { echo "missing $FLOW/$CONFIG" >&2; exit 1; }
command -v yosys >/dev/null || { echo "yosys not on PATH" >&2; exit 1; }
command -v openroad >/dev/null || { echo "openroad not on PATH" >&2; exit 1; }

# ORFS only uses the installed tools when OPENROAD_EXE/YOSYS_EXE are set (or IN_NIX_SHELL);
# otherwise it looks under tools/install, which does not exist here.
export OPENROAD_EXE="${OPENROAD_EXE:-$(command -v openroad)}"
export YOSYS_EXE="${YOSYS_EXE:-$(command -v yosys)}"

cd "$FLOW"

if [ "$CLEAN" = 1 ]; then
  echo ">> cleaning asap7/cva6"
  rm -rf logs/asap7/cva6/$VARIANT results/asap7/cva6/$VARIANT reports/asap7/cva6/$VARIANT objects/asap7/cva6/$VARIANT
fi

mkdir -p "$ROOT/run_logs"
LOG="$ROOT/run_logs/cva6_asap7_${VARIANT}_${STAGE}_$(date +%Y%m%d_%H%M%S).log"
echo ">> make DESIGN_CONFIG=$CONFIG $TARGET  (jobs=$JOBS)"
echo ">> log: $LOG"

START=$(date +%s)
set +e
make DESIGN_CONFIG="$CONFIG" NUM_CORES="$JOBS" "$TARGET" 2>&1 | tee "$LOG"
RC=${PIPESTATUS[0]}
set -e
echo ">> make exit code $RC after $(( $(date +%s) - START ))s"

if [ "$RC" = 0 ] && [ -f reports/asap7/cva6/$VARIANT/synth_stat.txt ]; then
  echo ">> synthesis summary (reports/asap7/cva6/$VARIANT/synth_stat.txt):"
  grep -iE "number of cells|chip area|cells$" reports/asap7/cva6/$VARIANT/synth_stat.txt | tail -5 || true
fi
exit "$RC"
