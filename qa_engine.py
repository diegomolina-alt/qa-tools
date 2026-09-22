"""Lógica determinista para convertir criterios de aceptación en casos base."""

from __future__ import annotations

from dataclasses import dataclass
import re


CA_HEADER_PATTERN = re.compile(
    r"^\s*(?P<identifier>CA\s*(?:[-–—]\s*)?\d+)\b(?P<title>.*)$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TestCase:
    """Representa un caso de prueba generado para un criterio de aceptación."""

    id: str
    jira: str
    criterio: str
    titulo: str
    precondiciones: str
    pasos: str
    resultado_esperado: str
    tipo: str
    analista: str
    tipo_prueba: str = ""
    directorio_repositorio: str = ""


def split_acceptance_criteria(text: str) -> list[tuple[str, str, str]]:
    """Divide el texto por encabezados CA al inicio de cada línea.

    Cada resultado contiene identificador, título extraído del encabezado y el
    bloque Gherkin asociado. Si no hay encabezados CA, no se genera ningún caso.
    """
    criteria: list[tuple[str, str, str]] = []
    identifier = ""
    title = ""
    gherkin_lines: list[str] = []

    def add_current_criterion() -> None:
        if identifier:
            criteria.append((identifier, title, "\n".join(gherkin_lines).strip()))

    for line in text.splitlines():
        match = CA_HEADER_PATTERN.match(line)
        if match:
            add_current_criterion()
            identifier = _normalize_identifier(match.group("identifier"))
            title = _extract_title(match.group("title"))
            gherkin_lines = []
        elif identifier:
            gherkin_lines.append(line)

    add_current_criterion()
    return criteria


def generate_test_cases(
    jira: str,
    analyst: str,
    criteria_text: str,
    test_type: str = "",
    repository_directory: str = "",
) -> list[TestCase]:
    """Genera un caso funcional base por cada criterio de aceptación detectado."""
    test_cases: list[TestCase] = []

    for number, (criterion_id, title, gherkin) in enumerate(split_acceptance_criteria(criteria_text), start=1):
        case_title = title or f"Criterio de aceptación {number}"
        test_cases.append(
            TestCase(
                id=f"CP-{number:03d}",
                jira=jira,
                criterio=criterion_id,
                titulo=case_title,
                precondiciones="Contar con acceso al sistema y los datos necesarios para ejecutar la prueba.",
                pasos="",
                resultado_esperado=gherkin,
                tipo="Funcional",
                analista=analyst,
                tipo_prueba=test_type,
                directorio_repositorio=repository_directory,
            )
        )

    return test_cases


def _normalize_identifier(identifier: str) -> str:
    number = re.search(r"\d+", identifier)
    return f"CA-{number.group(0)}" if number else identifier.upper()


def _extract_title(value: str) -> str:
    return value.lstrip(" \t-–—:").strip()
