"""Normalización de componentes de nombres de archivos multiplataforma."""

from __future__ import annotations

import re


INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*]')


def sanitize_filename_component(value: str, *, fallback: str = "SIN_NOMBRE") -> str:
    """Conserva el valor de negocio y lo hace seguro solo para usarlo en un archivo."""
    sanitized = INVALID_FILENAME_CHARACTERS.sub("_", value.strip()).rstrip(". ")
    return sanitized or fallback
