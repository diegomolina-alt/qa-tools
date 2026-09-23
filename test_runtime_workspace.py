"""Pruebas del workspace y log temporal controlado por QA Tools."""

import logging
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from evidence_generator import ApiEvidenceData, EvidenceCase, evidence_filename, generate_api_evidence
from mobile_evidence_generator import MobileEvidenceData, generate_mobile_evidence, mobile_evidence_filename
from resource_paths import resource_path
from runtime_workspace import clean_runtime_workspace, configure_runtime_logging, get_runtime_log_path, get_runtime_output_dir, prepare_runtime_workspace


class RuntimeWorkspaceTests(unittest.TestCase):
    def test_runtime_log_is_created_outside_the_generated_workspace(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "runtime_workspace.tempfile.gettempdir", return_value=temporary_directory
        ):
            logger = logging.getLogger("qa_tools")
            existing_handlers = list(logger.handlers)
            try:
                configured_logger = configure_runtime_logging()
                configured_logger.error("error de prueba")
                for handler in configured_logger.handlers:
                    handler.flush()

                log_path = get_runtime_log_path()
                self.assertTrue(log_path.is_file())
                self.assertIn("error de prueba", log_path.read_text(encoding="utf-8"))
                self.assertNotIn(get_runtime_output_dir(), log_path.parents)
            finally:
                for handler in list(logger.handlers):
                    if handler not in existing_handlers:
                        logger.removeHandler(handler)
                        handler.close()

    def test_prepare_creates_workspace_when_missing(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "runtime_workspace.tempfile.gettempdir", return_value=temporary_directory
        ):
            workspace = prepare_runtime_workspace()

            self.assertEqual(Path(temporary_directory) / "qa-tools" / "generated", workspace)
            self.assertTrue(workspace.is_dir())

    def test_clean_removes_only_files_inside_controlled_workspace(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "runtime_workspace.tempfile.gettempdir", return_value=temporary_directory
        ):
            workspace = prepare_runtime_workspace()
            generated_file = workspace / "Evidencias_APIs_ADN-234.docx"
            generated_file.write_text("temporal")
            nested_directory = workspace / "nested"
            nested_directory.mkdir()
            (nested_directory / "output.docx").write_text("temporal")
            outside_file = Path(temporary_directory) / "Evidencias_APIs_ADN-234.docx"
            outside_file.write_text("conservar")

            clean_runtime_workspace()

            self.assertEqual([], list(workspace.iterdir()))
            self.assertTrue(outside_file.exists())
            self.assertEqual("conservar", outside_file.read_text())

    def test_clean_supports_missing_or_empty_workspace(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "runtime_workspace.tempfile.gettempdir", return_value=temporary_directory
        ):
            self.assertEqual(Path(temporary_directory) / "qa-tools" / "generated", get_runtime_output_dir())
            workspace = clean_runtime_workspace()
            self.assertTrue(workspace.is_dir())
            self.assertEqual([], list(workspace.iterdir()))

    def test_clean_handles_a_locked_temporary_file_without_failing(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "runtime_workspace.tempfile.gettempdir", return_value=temporary_directory
        ):
            locked_file = prepare_runtime_workspace() / "abierto.docx"
            locked_file.write_text("temporal")

            with self.assertLogs("runtime_workspace", level="WARNING"), patch(
                "runtime_workspace.Path.unlink", side_effect=PermissionError("archivo bloqueado")
            ):
                clean_runtime_workspace()

            self.assertTrue(locked_file.exists())

    def test_api_and_mobile_documents_use_the_runtime_workspace_for_a_session(self) -> None:
        with TemporaryDirectory() as temporary_directory, patch(
            "runtime_workspace.tempfile.gettempdir", return_value=temporary_directory
        ):
            workspace = clean_runtime_workspace()
            api_output = get_runtime_output_dir() / evidence_filename("ADN-234")
            mobile_output = get_runtime_output_dir() / mobile_evidence_filename("ADN-234")
            api_data = ApiEvidenceData(
                "ADN-234", "Ana", "23/09/2026", "/service", "TP-1", [EvidenceCase("TAP-1", "Escenario API")]
            )
            mobile_data = MobileEvidenceData(
                qa_agile="Ana", execution_date="23/09/2026", test_plan="TP-1", test_environment="QA"
            )

            generate_api_evidence(api_data, resource_path("templates/Evidencias_APIs_template.docx"), api_output)
            generate_mobile_evidence(
                mobile_data,
                [EvidenceCase("TAP-2", "Escenario Mobile")],
                resource_path("templates/Evidencias_Mobile_template.docx"),
                mobile_output,
            )

            self.assertTrue(api_output.is_file())
            self.assertTrue(mobile_output.is_file())
            self.assertEqual(workspace, get_runtime_output_dir())

            clean_runtime_workspace()  # Equivale a Nuevo o a un nuevo inicio.
            self.assertEqual([], list(workspace.iterdir()))


if __name__ == "__main__":
    unittest.main()
