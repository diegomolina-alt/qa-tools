"""Prepara el entorno local de QA Tools y abre la aplicación.

Este módulo usa exclusivamente la biblioteca estándar para poder ejecutarse
antes de instalar las dependencias declaradas en requirements.txt.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import os
import shutil
import subprocess
import sys


MINIMUM_PYTHON = (3, 11)
MINIMUM_TK = 8.6
PROJECT_DIR = Path(__file__).resolve().parent
VENV_DIR = PROJECT_DIR / ".venv"
REQUIREMENTS_PATH = PROJECT_DIR / "requirements.txt"
REQUIREMENTS_MARKER = VENV_DIR / ".qa-tools-requirements.sha256"


class BootstrapError(Exception):
    """Error presentado al usuario durante la preparación del entorno."""


def is_compatible(python: Path) -> bool:
    """Comprueba versión y soporte gráfico sin importar paquetes externos."""
    check = (
        "import sys\n"
        "try:\n"
        "    import tkinter as tk\n"
        "except ImportError:\n"
        "    raise SystemExit(1)\n"
        "raise SystemExit(0 if sys.version_info >= (3, 11) and tk.TkVersion >= 8.6 else 1)\n"
    )
    result = subprocess.run([str(python), "-c", check], capture_output=True, text=True)
    return result.returncode == 0


def venv_python() -> Path:
    return VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def recreate_venv(base_python: Path) -> Path:
    if VENV_DIR.exists():
        print("[OK] El entorno existente no es compatible; se recreará.")
        try:
            shutil.rmtree(VENV_DIR)
        except OSError as error:
            raise BootstrapError("No se pudo reparar el entorno de QA Tools.") from error

    print("[OK] Creando entorno virtual...")
    result = subprocess.run([str(base_python), "-m", "venv", str(VENV_DIR)], cwd=PROJECT_DIR, capture_output=True, text=True)
    if result.returncode:
        raise BootstrapError("No se pudo crear el entorno de QA Tools.\n" + _details(result))

    python = venv_python()
    if not python.is_file() or not is_compatible(python):
        raise BootstrapError("El entorno creado no tiene un Python compatible con Tcl/Tk 8.6+.")
    return python


def requirements_hash() -> str:
    if not REQUIREMENTS_PATH.is_file():
        raise BootstrapError("No se encontró requirements.txt en la carpeta de QA Tools.")
    return sha256(REQUIREMENTS_PATH.read_bytes()).hexdigest()


def critical_imports_are_available(python: Path) -> bool:
    check = "import docx\nimport tkinter as tk\nassert tk.TkVersion >= 8.6\n"
    return subprocess.run([str(python), "-c", check], cwd=PROJECT_DIR, capture_output=True, text=True).returncode == 0


def install_requirements(python: Path, current_hash: str) -> None:
    should_install = REQUIREMENTS_MARKER.read_text().strip() != current_hash if REQUIREMENTS_MARKER.is_file() else True
    if not should_install and critical_imports_are_available(python):
        return

    print("[OK] Instalando dependencias...")
    result = subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(REQUIREMENTS_PATH)],
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise BootstrapError(
            "No se pudieron instalar las dependencias de QA Tools.\n"
            "Verifica tu conexión a Internet, red o proxy y vuelve a intentarlo.\n"
            + _details(result)
        )
    REQUIREMENTS_MARKER.write_text(f"{current_hash}\n", encoding="utf-8")

    if not critical_imports_are_available(python):
        raise BootstrapError("Las dependencias se instalaron, pero no se pudieron validar los imports críticos.")


def _details(result: subprocess.CompletedProcess[str]) -> str:
    output = (result.stdout + result.stderr).strip()
    return f"\n\nDetalle técnico:\n{output}" if output else ""


def main() -> int:
    print("QA Tools - Preparando entorno...", flush=True)
    base_python = Path(sys.executable)
    if not is_compatible(base_python):
        raise BootstrapError("El Python seleccionado no es compatible con QA Tools (se requiere Python 3.11+ y Tcl/Tk 8.6+).")

    import tkinter as tk

    print(f"[OK] Python {sys.version.split()[0]}", flush=True)
    print(f"[OK] Tcl/Tk {tk.TkVersion}", flush=True)
    python = venv_python()
    if not python.is_file() or not is_compatible(python):
        python = recreate_venv(base_python)
    else:
        print("[OK] Entorno virtual validado.")

    install_requirements(python, requirements_hash())
    print("[OK] Entorno preparado.", flush=True)
    print("Iniciando QA Tools...", flush=True)
    app_command = [str(python), str(PROJECT_DIR / "app.py")]
    if os.name != "nt":
        os.execv(str(python), app_command)
    return subprocess.run(app_command, cwd=PROJECT_DIR).returncode


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BootstrapError as error:
        print(f"\n[ERROR] {error}", file=sys.stderr)
        raise SystemExit(1)
