"""Workspace temporal y descartable utilizado durante la ejecución de QA Tools."""

from __future__ import annotations

import logging
from pathlib import Path
import shutil
import tempfile


LOGGER = logging.getLogger(__name__)
APPLICATION_TEMP_DIRECTORY = "qa-tools"
GENERATED_DIRECTORY = "generated"
RUNTIME_LOG_FILENAME = "qa-tools.log"


def get_runtime_output_dir() -> Path:
    """Devuelve la única ubicación temporal de salida controlada por QA Tools."""
    return Path(tempfile.gettempdir()) / APPLICATION_TEMP_DIRECTORY / GENERATED_DIRECTORY


def get_runtime_log_path() -> Path:
    """Devuelve el registro persistente entre limpiezas del workspace generado."""
    return Path(tempfile.gettempdir()) / APPLICATION_TEMP_DIRECTORY / RUNTIME_LOG_FILENAME


def configure_runtime_logging() -> logging.Logger:
    """Configura el registro de runtime en una ubicación escribible para la .app."""
    logger = logging.getLogger("qa_tools")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    log_path = get_runtime_log_path()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if not any(isinstance(handler, logging.FileHandler) and Path(handler.baseFilename) == log_path for handler in logger.handlers):
            handler = logging.FileHandler(log_path, encoding="utf-8")
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
            logger.addHandler(handler)
    except OSError as error:
        LOGGER.warning("No se pudo preparar el log de runtime %s: %s", log_path, error)
    return logger


def prepare_runtime_workspace() -> Path:
    """Crea el workspace temporal cuando aún no existe."""
    workspace = get_runtime_output_dir()
    try:
        workspace.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        LOGGER.warning("No se pudo preparar el workspace temporal %s: %s", workspace, error)
    return workspace


def clean_runtime_workspace() -> Path:
    """Elimina solo el contenido del workspace temporal de QA Tools.

    Un fallo al borrar un elemento (por ejemplo, un DOCX abierto) queda
    registrado y no impide que la aplicación continúe funcionando.
    """
    workspace = prepare_runtime_workspace()
    try:
        entries = list(workspace.iterdir())
    except OSError as error:
        LOGGER.warning("No se pudo leer el workspace temporal %s: %s", workspace, error)
        return workspace

    for entry in entries:
        try:
            # Un enlace simbólico se elimina como enlace; nunca se sigue hacia
            # una ruta ajena al workspace controlado.
            if entry.is_dir() and not entry.is_symlink():
                shutil.rmtree(entry)
            else:
                entry.unlink()
        except FileNotFoundError:
            continue
        except OSError as error:
            LOGGER.warning("No se pudo eliminar el archivo temporal %s: %s", entry, error)

    return workspace
