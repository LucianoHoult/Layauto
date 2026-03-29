#!/bin/bash
# =============================================================
# Extract device and net information from Calibre SVDB
#
# Prerequisites:
#   - Calibre LVS has been run, producing SVDB database
#   - calibrequery command is in PATH
#
# Usage:
#   ./calibre_query_extract.sh <svdb_dir> <cell_name> <output_dir>
#
# Outputs:
#   <output_dir>/calibre_device_query.json
#   <output_dir>/calibre_net_query.json
# =============================================================

set -e

SVDB_DIR=${1:?"Usage: $0 <svdb_dir> <cell_name> <output_dir>"}
CELL_NAME=${2:?"Provide cell name"}
OUTPUT_DIR=${3:?"Provide output directory"}

mkdir -p "$OUTPUT_DIR"

echo "Extracting from SVDB: $SVDB_DIR"
echo "Cell: $CELL_NAME"

# --- Device query ---
# Adapt the calibrequery syntax to your Calibre version
# The output format should match docs/data_formats.md
echo "Querying devices..."
# calibrequery -svdb "$SVDB_DIR" \
#   -cell "$CELL_NAME" \
#   -query device \
#   -format json \
#   > "$OUTPUT_DIR/calibre_device_query.json"

echo "TODO: Implement calibrequery command for your environment"
echo "Expected output format: see docs/data_formats.md"

# --- Net query ---
echo "Querying nets..."
# calibrequery -svdb "$SVDB_DIR" \
#   -cell "$CELL_NAME" \
#   -query net \
#   -format json \
#   > "$OUTPUT_DIR/calibre_net_query.json"

echo "Extraction complete. Output in: $OUTPUT_DIR"
