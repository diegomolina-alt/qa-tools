"""Generación del CSV de casos de prueba compatible con Xray."""

from __future__ import annotations

import csv
from pathlib import Path

from qa_engine import TestCase


CSV_HEADERS = [
    "TCID",
    "Resumen",
    "Nombre de Prioridad",
    "Tipo de test",
    "Definicion en Gherkin",
    "Etiquetas",
    "Descripcion",
    "Nombre de asignado",
    "Directorio de repositorio de test",
]


def normalize_labels(labels: str) -> str:
    """Normaliza etiquetas Xray sin espacios alrededor del separador punto y coma."""
    return ";".join(label.strip() for label in labels.split(";") if label.strip())


DEFAULT_LABELS = normalize_labels("Manual; URPIPRO")


def build_summary(domain: str, case_name: str) -> str:
    """Construye el resumen Xray a partir del dominio y el nombre limpio del caso."""
    normalized_domain = domain.strip()
    if not normalized_domain:
        raise ValueError("El Dominio es obligatorio para construir el resumen del CSV.")
    if normalized_domain.endswith("/"):
        return f"{normalized_domain}{case_name.strip()}"
    return f"{normalized_domain} - {case_name.strip()}"


def generate_csv(destination: Path, test_cases: list[TestCase], domain: str) -> None:
    """Crea el CSV UTF-8 separado por comas con una fila por caso de prueba."""
    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file, delimiter=",")
        writer.writerow(CSV_HEADERS)
        for tcid, case in enumerate(test_cases, start=1):
            writer.writerow(
                [
                    tcid,
                    build_summary(domain, case.titulo),
                    "Low",
                    "Cucumber",
                    case.resultado_esperado,
                    DEFAULT_LABELS,
                    case.titulo,
                    case.analista,
                    case.directorio_repositorio,
                ]
            )
    validate_csv_contract(destination)


def validate_csv_contract(destination: Path) -> None:
    """Verifica el contrato requerido por Xray después de generar el CSV."""
    raw_content = destination.read_bytes()
    if raw_content.startswith(b"\xef\xbb\xbf"):
        raise ValueError("El CSV no debe incluir BOM.")
    raw_content.decode("utf-8")

    with destination.open("r", encoding="utf-8", newline="") as file:
        reader = csv.reader(file, delimiter=",")
        headers = next(reader, None)
        if headers != CSV_HEADERS:
            raise ValueError("La cabecera del CSV no coincide con el formato requerido por Xray.")

        for row in reader:
            if len(row) != len(CSV_HEADERS):
                raise ValueError("Una fila del CSV no contiene las 9 columnas requeridas.")
            labels = row[5]
            if labels != normalize_labels(labels):
                raise ValueError("Las etiquetas del CSV contienen espacios inválidos.")
