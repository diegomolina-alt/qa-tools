"""Regresiones de configuración, destinos y errores de callbacks."""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app import (
    EVIDENCE_TEMPLATES,
    QATestGeneratorApp,
    choose_document_destination,
    domain_validation_message,
    evidence_template_path,
    install_callback_exception_handler,
)
from evidence_generator import ApiEvidenceData, EvidenceCase, generate_api_evidence
from mobile_evidence_generator import MobileEvidenceData, generate_mobile_evidence
from resource_paths import resource_path


class _Value:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def get(self) -> str:
        return self.value

    def set(self, value: str) -> None:
        self.value = value


class _Text:
    def get(self, _: str, __: str) -> str:
        return ""

    def delete(self, _: str, __: str) -> None:
        pass


class _CallbackRoot:
    report_callback_exception: object


class EvidenceModeConfigurationTests(unittest.TestCase):
    def test_validates_required_domain_and_final_slash(self) -> None:
        self.assertEqual("El campo Dominio es obligatorio.", domain_validation_message("   "))
        self.assertEqual(
            "El campo Dominio debe finalizar con '/' para generar correctamente los títulos de los Test.",
            domain_validation_message("Urpipro/Loan/Derivacion App MiBanco"),
        )
        self.assertIsNone(domain_validation_message("  Urpipro/Loan/Derivacion App MiBanco/  "))

    def test_api_and_mobile_have_exclusive_template_configuration(self) -> None:
        self.assertEqual({"API", "MOBILE"}, set(EVIDENCE_TEMPLATES))
        self.assertEqual(resource_path("templates/Evidencias_APIs_template.docx"), evidence_template_path("API"))
        self.assertEqual(resource_path("templates/Evidencias_Mobile_template.docx"), evidence_template_path("MOBILE"))

    def test_unknown_evidence_type_has_no_template(self) -> None:
        self.assertIsNone(evidence_template_path("API_MOBILE"))

    def test_missing_template_has_an_evidence_specific_error(self) -> None:
        with patch("app.resource_path", side_effect=FileNotFoundError("/bundle/templates/api.docx")):
            with self.assertRaisesRegex(FileNotFoundError, "No se encontró el template de evidencias API"):
                evidence_template_path("API")

    def test_cancelled_document_destination_does_not_create_an_output_path(self) -> None:
        with patch("app.filedialog.askdirectory", return_value=""):
            self.assertIsNone(choose_document_destination("Evidencias_APIs_ADN-234.docx"))

    def test_existing_document_requires_confirmation_before_replacing(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            existing_file = Path(temporary_directory) / "Evidencias_APIs_ADN-234.docx"
            existing_file.write_text("conservar")

            with patch("app.filedialog.askdirectory", return_value=temporary_directory), patch(
                "app.messagebox.askyesno", return_value=False
            ) as confirm:
                self.assertIsNone(choose_document_destination(existing_file.name))

            confirm.assert_called_once()
            self.assertEqual("conservar", existing_file.read_text())

            with patch("app.filedialog.askdirectory", return_value=temporary_directory), patch(
                "app.messagebox.askyesno", return_value=True
            ):
                self.assertEqual(existing_file, choose_document_destination(existing_file.name))

    def test_confirmed_destination_is_shared_by_api_and_mobile_generators(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "app.filedialog.askdirectory", return_value=temporary_directory
        ):
            api_output = choose_document_destination("Evidencias_APIs_ADN-234.docx")
            mobile_output = choose_document_destination("Evidencia_Mobile_ADN-234.docx")
            self.assertIsNotNone(api_output)
            self.assertIsNotNone(mobile_output)

            generate_api_evidence(
                ApiEvidenceData("ADN-234", "Ana", "23/09/2026", "/service", "TP-1", [EvidenceCase("TAP-1", "API")]),
                resource_path("templates/Evidencias_APIs_template.docx"),
                api_output,
            )
            generate_mobile_evidence(
                MobileEvidenceData(qa_agile="Ana", execution_date="23/09/2026", test_plan="TP-1", test_environment="QA"),
                [EvidenceCase("TAP-2", "Mobile")],
                resource_path("templates/Evidencias_Mobile_template.docx"),
                mobile_output,
            )

            self.assertTrue(api_output.is_file())
            self.assertTrue(mobile_output.is_file())

    def test_callback_exception_handler_shows_a_concise_error(self) -> None:
        root = _CallbackRoot()
        install_callback_exception_handler(root)  # type: ignore[arg-type]

        with patch("app.LOGGER"), patch("app.messagebox.showerror") as show_error:
            try:
                raise RuntimeError("fallo de prueba")
            except RuntimeError:
                exception_type, exception, traceback = sys.exc_info()
                root.report_callback_exception(exception_type, exception, traceback)  # type: ignore[operator]

        show_error.assert_called_once()
        self.assertIn("Revisa el registro", show_error.call_args.args[1])

    def test_new_actions_clean_the_runtime_workspace(self) -> None:
        app = QATestGeneratorApp.__new__(QATestGeneratorApp)
        app._cases_have_data = lambda: False
        app._evidence_has_data = lambda: False
        app.jira_var = _Value("JIRA-1")
        app.analyst_var = _Value("Ana")
        app.repository_directory_var = _Value("/repo")
        app.domain_var = _Value("dominio/")
        app.criteria_text = _Text()
        app.status_var = _Value()
        app.evidence_type_var = _Value("API")
        app.evidence_jira_var = _Value("JIRA-1")
        app.qa_agile_var = _Value("Ana")
        app.service_var = _Value("/service")
        app.test_plan_var = _Value("TP-1")
        app.test_environment_var = _Value("QA")
        app.test_titles_text = _Text()
        app.evidence_panels = []
        app.evidence_result_var = _Value()
        app.default_qa_agile = "Ana"
        app._clear_evidence_cases = lambda: None

        with patch("app.clean_runtime_workspace") as clean_workspace:
            app.reset_cases()
            app.reset_evidence()

        self.assertEqual(2, clean_workspace.call_count)


if __name__ == "__main__":
    unittest.main()
