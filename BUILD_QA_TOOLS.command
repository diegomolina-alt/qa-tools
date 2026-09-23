#!/bin/bash
# Construye localmente QA Tools.app para la arquitectura de esta Mac.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"
APP_PATH="$PROJECT_DIR/dist/QA Tools.app"

cd "$PROJECT_DIR"

finish_on_error() {
    echo
    printf '%b\n' "$1" >&2
    if [[ -t 0 ]]; then
        read -r -p "Presiona Enter para cerrar..." _
    fi
    exit 1
}

is_compatible_python() {
    "$1" -c '
import sys
try:
    import tkinter as tk
except ImportError:
    raise SystemExit(1)
raise SystemExit(0 if sys.version_info >= (3, 11) and tk.TkVersion >= 8.6 else 1)
' >/dev/null 2>&1
}

find_python() {
    local name candidate
    local -a names=(python3.14 python3.13 python3.12 python3.11 python3)

    for name in "${names[@]}"; do
        candidate="$(command -v "$name" 2>/dev/null || true)"
        if [[ -n "$candidate" ]] && is_compatible_python "$candidate"; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

echo "QA Tools - preparación de build local"
echo "Raíz del proyecto: $PROJECT_DIR"

PYTHON="$(find_python || true)"
if [[ -z "$PYTHON" ]]; then
    finish_on_error "No se encontró una versión compatible de Python.\nInstala Python 3.11+ con Tcl/Tk 8.6+ y vuelve a ejecutar BUILD_QA_TOOLS.command."
fi

echo "[OK] Python compatible: $($PYTHON --version)"

if [[ ! -x "$VENV_PYTHON" ]] || ! is_compatible_python "$VENV_PYTHON"; then
    echo "[OK] Creando entorno virtual local..."
    rm -rf "$VENV_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
fi

echo "[OK] Instalando/actualizando dependencias runtime..."
"$VENV_PYTHON" -m pip install --disable-pip-version-check --upgrade -r requirements.txt

echo "[OK] Instalando/actualizando PyInstaller en el entorno local..."
"$VENV_PYTHON" -m pip install --disable-pip-version-check --upgrade PyInstaller

echo "[OK] Ejecutando pruebas..."
if ! "$VENV_PYTHON" -m unittest discover -v; then
    finish_on_error "BUILD CANCELADO - existen pruebas fallidas."
fi

APP_VERSION="$("$VENV_PYTHON" -c 'from app_metadata import APP_VERSION; print(APP_VERSION)')"
ARCHITECTURE="$(uname -m)"

echo "[OK] Limpiando artefactos anteriores..."
rm -rf "$PROJECT_DIR/build" "$PROJECT_DIR/dist"

echo "[OK] Construyendo QA Tools.app..."
"$VENV_PYTHON" -m PyInstaller -y "QA Tools.spec"

if [[ ! -d "$APP_PATH" ]] || [[ ! -f "$APP_PATH/Contents/Info.plist" ]] || \
   [[ ! -d "$APP_PATH/Contents/MacOS" ]] || [[ ! -d "$APP_PATH/Contents/Resources" ]] || \
   [[ ! -f "$APP_PATH/Contents/Resources/templates/Evidencias_APIs_template.docx" ]] || \
   [[ ! -f "$APP_PATH/Contents/Resources/templates/Evidencias_Mobile_template.docx" ]]; then
    finish_on_error "BUILD CANCELADO - el bundle generado no contiene la estructura o templates requeridos."
fi

open "$PROJECT_DIR/dist"

echo
echo "========================================"
echo "QA Tools $APP_VERSION - BUILD COMPLETADO"
echo "========================================"
echo
echo "Se creó:"
echo "dist/QA Tools.app"
echo
echo "Arquitectura detectada: $ARCHITECTURE"
echo "Finder se abrirá automáticamente."
echo
echo "Arrastra QA Tools.app a la carpeta Aplicaciones."
echo "NO copies la carpeta QA Tools ni el ejecutable Unix interno."
echo "========================================"

if [[ -t 0 ]]; then
    read -r -p "Presiona Enter para cerrar..." _
fi
