"""Pruebas de nombres de archivo seguros para macOS y Windows."""

import unittest

from evidence_generator import evidence_filename
from filename_helpers import sanitize_filename_component
from mobile_evidence_generator import mobile_evidence_filename


class FilenameHelperTests(unittest.TestCase):
    def test_sanitizes_windows_invalid_characters_and_trailing_space_or_dot(self) -> None:
        self.assertEqual("TAP_12________", sanitize_filename_component(' TAP:12<>"/\\|?*. '))

    def test_uses_a_fallback_for_an_empty_component(self) -> None:
        self.assertEqual("SIN_JIRA", sanitize_filename_component(" . ", fallback="SIN_JIRA"))

    def test_api_and_mobile_reuse_the_same_sanitization(self) -> None:
        jira = ' ADN:234? '
        self.assertEqual("Evidencias_APIs_ADN_234_.docx", evidence_filename(jira))
        self.assertEqual("Evidencia_Mobile_ADN_234_.docx", mobile_evidence_filename(jira))
