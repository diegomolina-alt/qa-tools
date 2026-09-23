"""Pruebas de resolución de recursos permanentes en desarrollo y empaquetado."""

import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from resource_paths import resource_path, resource_root
from runtime_workspace import get_runtime_output_dir


class ResourcePathTests(unittest.TestCase):
    def test_templates_are_resolved_as_absolute_paths(self) -> None:
        api_template = resource_path("templates/Evidencias_APIs_template.docx")
        mobile_template = resource_path("templates/Evidencias_Mobile_template.docx")

        self.assertTrue(api_template.is_absolute())
        self.assertTrue(mobile_template.is_absolute())
        self.assertTrue(api_template.is_file())
        self.assertTrue(mobile_template.is_file())

    def test_resolution_does_not_depend_on_current_working_directory(self) -> None:
        expected_template = resource_path("templates/Evidencias_APIs_template.docx")
        original_directory = Path.cwd()
        with TemporaryDirectory() as temporary_directory:
            try:
                os.chdir(temporary_directory)
                self.assertEqual(expected_template, resource_path("templates/Evidencias_APIs_template.docx"))
            finally:
                os.chdir(original_directory)

    def test_missing_resource_has_a_clear_absolute_path(self) -> None:
        with self.assertRaisesRegex(FileNotFoundError, "No se encontró el recurso requerido") as raised:
            resource_path("templates/inexistente.docx")

        self.assertIn(str(resource_root()), str(raised.exception))

    def test_pyinstaller_resource_root_is_supported(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            bundled_template = Path(temporary_directory) / "templates" / "template.docx"
            bundled_template.parent.mkdir()
            bundled_template.write_text("template")

            with patch("resource_paths.sys._MEIPASS", temporary_directory, create=True):
                self.assertEqual(bundled_template.resolve(), resource_path("templates/template.docx"))

    def test_macos_frozen_bundle_uses_contents_resources_not_frameworks(self) -> None:
        with TemporaryDirectory() as temporary_directory:
            contents = Path(temporary_directory) / "QA Tools.app" / "Contents"
            executable = contents / "MacOS" / "QA Tools"
            frameworks = contents / "Frameworks"
            bundled_template = contents / "Resources" / "templates" / "Evidencias_APIs_template.docx"
            executable.parent.mkdir(parents=True)
            executable.touch()
            frameworks.mkdir()
            bundled_template.parent.mkdir(parents=True)
            bundled_template.write_text("template")

            with (
                patch("resource_paths.sys.frozen", True, create=True),
                patch("resource_paths.sys.platform", "darwin"),
                patch("resource_paths.sys.executable", str(executable)),
                patch("resource_paths.sys._MEIPASS", str(frameworks), create=True),
            ):
                self.assertEqual((contents / "Resources").resolve(), resource_root())
                self.assertEqual(bundled_template.resolve(), resource_path("templates/Evidencias_APIs_template.docx"))

    def test_path_traversal_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "debe permanecer dentro"):
            resource_path("../../archivo")

    def test_runtime_workspace_is_not_inside_resource_directory(self) -> None:
        self.assertNotEqual(resource_root(), get_runtime_output_dir())
        self.assertNotIn(resource_root(), get_runtime_output_dir().parents)


if __name__ == "__main__":
    unittest.main()
