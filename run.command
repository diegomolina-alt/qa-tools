#!/bin/bash
# Ejecuta QA Test Generator con Python 3.11+ y Tcl/Tk 8.6+.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

is_compatible() {
    "$1" -c '
import sys
try:
    import tkinter as tk
except ImportError:
    raise SystemExit(1)
raise SystemExit(0 if sys.version_info >= (3, 11) and tk.TkVersion >= 8.6 else 1)
' >/dev/null 2>&1
}

add_candidate() {
    if [ -n "${1:-}" ] && [ -x "$1" ]; then
        CANDIDATES+=("$1")
    fi
}

CANDIDATES=()
for framework_python in /Library/Frameworks/Python.framework/Versions/*/bin/python3; do
    add_candidate "$framework_python"
done
add_candidate "/opt/homebrew/bin/python3"
add_candidate "/usr/local/bin/python3"
add_candidate "$(command -v python3.13 2>/dev/null || true)"
add_candidate "$(command -v python3.12 2>/dev/null || true)"
add_candidate "$(command -v python3.11 2>/dev/null || true)"
add_candidate "$(command -v python3 2>/dev/null || true)"

PYTHON=""
for candidate in "${CANDIDATES[@]}"; do
    if is_compatible "$candidate"; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "No se encontró Python 3.11+ con Tcl/Tk 8.6+."
    echo "El Python de Apple Command Line Tools no es compatible con esta aplicación."
    echo
    echo "Instale Python actual desde: https://www.python.org/downloads/macos/"
    echo "o ejecute: brew install python"
    exit 1
fi

exec "$PYTHON" "$PROJECT_DIR/bootstrap.py"
