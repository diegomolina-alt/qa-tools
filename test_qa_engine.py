"""Pruebas de parsing de criterios de aceptación y generación de CSV."""

import csv
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from csv_generator import CSV_HEADERS, build_summary, generate_csv, normalize_labels, validate_csv_contract
from qa_engine import generate_test_cases, normalize_jira_text, split_acceptance_criteria


class AcceptanceCriteriaTests(unittest.TestCase):
    def test_normalize_jira_text_converts_spanish_accents_without_changing_structure(self) -> None:
        self.assertEqual("a e i o u u n", normalize_jira_text("á é í ó ú ü ñ"))
        self.assertEqual("A E I O U U N", normalize_jira_text("Á É Í Ó Ú Ü Ñ"))
        self.assertEqual("Visualizacion del modulo", normalize_jira_text("Visualización del módulo"))
        self.assertEqual("El nino valido la informacion", normalize_jira_text("El niño validó la información"))
        self.assertEqual("ANO / CONFIRMACION / EJECUCION", normalize_jira_text("AÑO / CONFIRMACIÓN / EJECUCIÓN"))
        self.assertEqual("Dado uno\nCuando ocurre: A-B_[x]", normalize_jira_text("Dado uno\nCuando ocurre: A-B_[x]"))

    def test_normalized_criteria_produces_ascii_safe_csv_content(self) -> None:
        criteria = normalize_jira_text(
            "CA01: Visualización del módulo\nDado que el niño está autenticado\n"
            "Cuando ingrese a Crédito\nEntonces deberá visualizar información válida"
        )
        cases = generate_test_cases("ADN1-666", "Diego", criteria, repository_directory="XRAY")

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "casos.csv"
            generate_csv(destination, cases, "Urpipro/Loan/")
            content = destination.read_text(encoding="utf-8")

        self.assertNotIn("�", content)
        self.assertTrue(content.isascii())
        self.assertIn("Urpipro/Loan/Visualizacion del modulo", content)
        self.assertIn("Dado que el nino esta autenticado", content)
    def test_detects_hyphenated_criteria_and_keeps_gherkin_separate(self) -> None:
        criteria = """CA-01 — Consulta bandeja de solicitudes
Dado que existe un AdN autenticado
Cuando se consulta GET /customer-request
Entonces el BFF retorna 200

CA-02 — Cálculo automático del período
Dado que el front consulta la bandeja
Cuando el BFF procesa la petición
Entonces calcula correctamente el período

CA-03 — Consulta solicitudes APPLICATION
Dado que existe un salesRepReference
Cuando el BFF consulta al MS Customer
Entonces retorna las solicitudes correspondientes"""

        cases = generate_test_cases("ADN1-5647", "Diego Molina", criteria)

        self.assertEqual(3, len(cases))
        self.assertEqual("Consulta bandeja de solicitudes", cases[0].titulo)
        self.assertEqual("Cálculo automático del período", cases[1].titulo)
        self.assertEqual("Consulta solicitudes APPLICATION", cases[2].titulo)
        self.assertEqual(
            "Dado que existe un AdN autenticado\nCuando se consulta GET /customer-request\nEntonces el BFF retorna 200",
            cases[0].resultado_esperado,
        )
        self.assertNotIn("CA-02", cases[0].resultado_esperado)

    def test_detects_supported_ca_variants(self) -> None:
        for separator in ("", " ", "-", "–", "—"):
            criteria = f"CA{separator}01 — Primer caso\nDado uno\n\nCA{separator}02 — Segundo caso\nDado dos"
            with self.subTest(separator=separator):
                self.assertEqual(2, len(split_acceptance_criteria(criteria)))

    def test_does_not_detect_ca_inside_regular_text(self) -> None:
        criteria = "El analista menciona CA dentro de una oración, pero no es un encabezado."
        self.assertEqual([], split_acceptance_criteria(criteria))
        self.assertEqual([], generate_test_cases("ADN1-1", "Diego", criteria))

    def test_csv_has_one_row_per_criterion(self) -> None:
        criteria = "CA-01: Primer caso\nDado uno\nCuando uno\nEntonces uno\n\nCA-02: Segundo caso\nDado dos"
        cases = generate_test_cases("ADN1-1", "Diego", criteria, repository_directory="DIRECTORIO XRAY")

        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "casos.csv"
            generate_csv(destination, cases, "Urpipro/Loan/Bandeja de entrada")
            with destination.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))

        self.assertEqual(9, len(CSV_HEADERS))
        self.assertEqual(["1", "2"], [row["TCID"] for row in rows])
        self.assertEqual("Urpipro/Loan/Bandeja de entrada - Primer caso", rows[0]["Resumen"])
        self.assertNotIn("T-ADN1-1", rows[0]["Resumen"])
        self.assertEqual("Dado uno\nCuando uno\nEntonces uno", rows[0]["Definicion en Gherkin"])
        self.assertEqual("Dado dos", rows[1]["Definicion en Gherkin"])

    def test_normalizes_labels_and_validates_xray_csv_contract(self) -> None:
        self.assertEqual("Manual;URPIPRO", normalize_labels("Manual; URPIPRO"))
        self.assertEqual("Manual;URPIPRO;Smoke", normalize_labels(" Manual ; URPIPRO ; Smoke "))

        criteria = "CA-01: Primer caso\nDado uno\n\nCA-02: Segundo caso\nDado dos\n\nCA-03: Tercer caso\nDado tres"
        cases = generate_test_cases("ADN1-2694", "Diego", criteria, repository_directory="DIRECTORIO XRAY")
        with TemporaryDirectory() as temporary_directory:
            destination = Path(temporary_directory) / "casos.csv"
            generate_csv(destination, cases, "Urpipro/Loan/Bandeja de entrada")
            validate_csv_contract(destination)
            with destination.open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file, delimiter=","))

        self.assertEqual(3, len(rows))
        self.assertEqual("Manual;URPIPRO", rows[0]["Etiquetas"])
        self.assertTrue(all(label == label.strip() for label in rows[0]["Etiquetas"].split(";")))

    def test_summary_uses_trimmed_domain_and_clean_case_name(self) -> None:
        self.assertEqual(
            "Urpipro/Customer/Profile - Cliente existente",
            build_summary(" Urpipro/Customer/Profile ", " Cliente existente "),
        )

    def test_summary_preserves_a_valid_final_slash_without_duplicating_it(self) -> None:
        self.assertEqual(
            "Urpipro/Loan/Derivacion App MiBanco/Confirmación y procesamiento de la solicitud",
            build_summary(
                "  Urpipro/Loan/Derivacion App MiBanco/  ",
                " Confirmación y procesamiento de la solicitud ",
            ),
        )

    def test_summary_requires_domain(self) -> None:
        with self.assertRaises(ValueError):
            build_summary("   ", "Cliente existente")


if __name__ == "__main__":
    unittest.main()
