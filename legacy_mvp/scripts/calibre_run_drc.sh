#!/bin/bash
# =============================================================
# Run Calibre DRC on a GDS file
#
# Usage:
#   ./calibre_run_drc.sh <gds_file> <rule_file> [output_dir]
# =============================================================

set -e

GDS_FILE=${1:?"Usage: $0 <gds_file> <rule_file> [output_dir]"}
RULE_FILE=${2:?"Provide DRC rule file path"}
OUTPUT_DIR=${3:-"./drc_results"}

mkdir -p "$OUTPUT_DIR"

CELL_NAME=$(basename "$GDS_FILE" .gds)

echo "Running Calibre DRC"
echo "  GDS: $GDS_FILE"
echo "  Rules: $RULE_FILE"
echo "  Output: $OUTPUT_DIR"

# calibre -drc -hier \
#   -turbo \
#   "$RULE_FILE" \
#   -gds "$GDS_FILE" \
#   -cell "$CELL_NAME" \
#   -resultdb "$OUTPUT_DIR/drc_results.db" \
#   2>&1 | tee "$OUTPUT_DIR/drc.log"

echo "TODO: Adapt calibre command for your environment"
echo "Check $OUTPUT_DIR/drc.log for results"
