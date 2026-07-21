#!/usr/bin/env bash
# Buffer Fin Resize - Linux / macOS one-click dependency installer.
#
# Usage:
#   scripts/install.sh           -- check + install required deps
#   scripts/install.sh --check   -- report only, no install
#   scripts/install.sh --all     -- install required + optional

set -euo pipefail

# Force UTF-8 so the install run prints / writes consistently even if
# LANG=C. (Not strictly needed on POSIX, but mirrors install.bat.)
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

PY=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PY="$candidate"
        break
    fi
done

if [ -z "$PY" ]; then
    echo "[ERROR] No Python interpreter found on PATH."
    echo "        Install Python 3.10+ and re-run this script."
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
CHECKER="$SCRIPT_DIR/check_deps.py"

case "${1:-}" in
    --check)
        exec "$PY" "$CHECKER"
        ;;
    --all)
        exec "$PY" "$CHECKER" --with-optional
        ;;
    *)
        exec "$PY" "$CHECKER" --install
        ;;
esac
