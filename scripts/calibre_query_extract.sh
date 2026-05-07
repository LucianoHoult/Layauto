#!/bin/bash
# =============================================================
# Extract LVS-side artifacts from a Calibre SVDB.
#
# Two outputs are produced (when the corresponding sub-step is
# requested via the --steps flag):
#   1. Instance Cross Reference  -- pairs each schematic device
#      with its SVDB-extracted device. Driven by the
#      `INSTANCE XREF WRITE` command inside the executive
#      module spawned by `calibre -query`.
#   2. Device / net JSON queries -- the existing legacy pass
#      that feeds the dummy parser today (kept commented as
#      M7 will replace it with a real `calibrequery` invocation).
#
# Prerequisites:
#   - Calibre LVS has been run, producing the SVDB at
#     <svdb_dir>.
#   - `calibre` is in PATH.
#
# Usage:
#   ./calibre_query_extract.sh <svdb_dir> <cell_name> <output_dir> \
#                              [--steps ixref,devicejson,netjson] \
#                              [--ixref-out <path>]
#
#   The default --steps list is `ixref` (the only step wired
#   end-to-end today). The other two stay TODO until M7.
#
# Outputs:
#   <output_dir>/iXref_<cell>_<timestamp>.temp        (default)
#   <output_dir>/calibre_device_query.json            (TODO)
#   <output_dir>/calibre_net_query.json               (TODO)
#
# The --ixref-out override lets the Python pipeline pass in the
# resolved-from-config output path (with {ts}/{cell} pattern
# already expanded) so the shell + Python sides agree byte-for
# byte on the artifact path.
# =============================================================

set -euo pipefail

SVDB_DIR=${1:?"Usage: $0 <svdb_dir> <cell_name> <output_dir> [--steps ...] [--ixref-out PATH]"}
CELL_NAME=${2:?"Provide cell name"}
OUTPUT_DIR=${3:?"Provide output directory"}
shift 3

STEPS="ixref"
IXREF_OUT=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --steps)        STEPS="$2"; shift 2;;
    --ixref-out)    IXREF_OUT="$2"; shift 2;;
    *) echo "Unknown flag: $1" >&2; exit 2;;
  esac
done

mkdir -p "$OUTPUT_DIR"

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
if [[ -z "$IXREF_OUT" ]]; then
  IXREF_OUT="${OUTPUT_DIR}/iXref_${CELL_NAME}_${TIMESTAMP}.temp"
fi

echo "Calibre query-extract:"
echo "  SVDB:     $SVDB_DIR"
echo "  cell:     $CELL_NAME"
echo "  out_dir:  $OUTPUT_DIR"
echo "  steps:    $STEPS"
echo "  iXref out: $IXREF_OUT"

step_enabled() {
  [[ ",${STEPS}," == *",$1,"* ]]
}

# -------------------------------------------------------------
# Step 1: Instance Cross Reference
#
# `calibre -query <svdb>` opens the executive module on stdin.
# We script it by piping the textual command list. The output
# file path is set on the `INSTANCE XREF WRITE` line and quoted
# to survive paths with spaces.
# -------------------------------------------------------------
if step_enabled ixref; then
  echo "[ixref] dumping instance cross reference -> $IXREF_OUT"
  # Note: real Calibre needs the executive prompt to actually be
  # ready before EXIT lands. Production scripts usually wrap this
  # in `expect`; for a deterministic CI / dummy run we pipe the
  # commands and let the dummy stub below short-circuit it.
  if command -v calibre >/dev/null 2>&1; then
    calibre -query "$SVDB_DIR" <<EOF
INSTANCE XREF WRITE "$IXREF_OUT"
EXIT
EOF
  else
    echo "  calibre binary not on PATH — skipping (dummy_mode handled in Python)" >&2
  fi
fi

# -------------------------------------------------------------
# Step 2/3: device + net JSON queries (legacy MVP pass)
#
# Still placeholders — M7 ports them to `calibrequery` and the
# resulting JSON shape is documented in docs/architecture.md §9.
# -------------------------------------------------------------
if step_enabled devicejson; then
  echo "[devicejson] TODO — implement calibrequery -query device for $CELL_NAME"
  # calibrequery -svdb "$SVDB_DIR" -cell "$CELL_NAME" \
  #   -query device -format json \
  #   > "$OUTPUT_DIR/calibre_device_query.json"
fi

if step_enabled netjson; then
  echo "[netjson]    TODO — implement calibrequery -query net for $CELL_NAME"
  # calibrequery -svdb "$SVDB_DIR" -cell "$CELL_NAME" \
  #   -query net -format json \
  #   > "$OUTPUT_DIR/calibre_net_query.json"
fi

echo "Done. Outputs in: $OUTPUT_DIR"
