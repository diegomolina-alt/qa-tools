"""Resolución centralizada de recursos permanentes y de solo lectura."""

from __future__ import annotations

from pathlib import Path
import sys


def resource_root() -> Path:
    """Devuelve el directorio de recursos en desarrollo o dentro de PyInstaller."""
    if getattr(sys, "frozen", False) and sys.platform == "darwin":
        # En un bundle macOS de PyInstaller, _MEIPASS puede apuntar a
        # Contents/Frameworks, mientras que los datos están en Contents/Resources.
        return (Path(sys.executable).resolve().parent.parent / "Resources").resolve()

    bundle_root = getattr(sys, "_MEIPASS", None)
    return Path(bundle_root).resolve() if bundle_root else Path(__file__).resolve().parent


def resource_path(relative_path: str | Path) -> Path:
    """Resuelve un recurso empaquetable, verificando que exista y no escape de su raíz."""
    requested_path = Path(relative_path)
    if requested_path.is_absolute():
        raise ValueError("Los recursos permanentes deben indicarse mediante una ruta relativa.")

    root = resource_root().resolve()
    resolved_path = (root / requested_path).resolve()
    try:
        resolved_path.relative_to(root)
    except ValueError as error:
        raise ValueError("La ruta del recurso debe permanecer dentro de los recursos de QA Tools.") from error

    if not resolved_path.exists():
        raise FileNotFoundError(f"No se encontró el recurso requerido: {resolved_path}")
    return resolved_path
