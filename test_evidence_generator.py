"""Pruebas de parsing y generación de evidencias API por Xray Test."""

from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
import unittest

from docx import Document

from evidence_generator import DEFAULT_DOCUMENT_STATUS, ApiEvidenceData, EvidenceCase, evidence_filename, generate_api_evidence, parse_xray_tests


class ApiEvidenceGeneratorTests(unittest.TestCase):
    def test_parse_xray_tests_preserves_case_title_and_order(self) -> None:
        source = """Xray Test
TAP-79281

T-ADN1-2694 Error por salesRepReference no resuelto

Xray Test
TAP-79280

T-ADN1-2694 Respuesta separada por secciones

Xray Test
TAP-79279

T-ADN1-2694 Consulta pre-solicitudes PRE_APPLICATION

Xray Test
TAP-79278

T-ADN1-2694 Consulta solicitudes APPLICATION"""

        cases = parse_xray_tests(source)

        self.assertEqual(["TAP-79281", "TAP-79280", "TAP-79279", "TAP-79278"], [case.xray_test for case in cases])
        self.assertEqual(
            "T-ADN1-2694 Error por salesRepReference no resuelto",
            cases[0].title,
        )
        self.assertEqual("POST", cases[0].method)

    def test_evidence_case_defaults_to_post(self) -> None:
        case = EvidenceCase(
            "TAP-79281",
            "Caso simplificado",
            endpoint="/legacy-endpoint",
            status_response="200",
            request='{"legacy": true}',
        )

        self.assertEqual("POST", case.method)

    def test_parse_xray_test_executions_format(self) -> None:
        source = """1
TAP-79276
T-ADN1-2694 Consulta bandeja de solicitudes del AdN
Cucumber
0
TO DO

2
TAP-79277
T-ADN1-2694 Cálculo automático del periodo
Cucumber
0
TO DO"""

        cases = parse_xray_tests(source)

        self.assertEqual(["TAP-79276", "TAP-79277"], [case.xray_test for case in cases])
        self.assertEqual(
            [
                "T-ADN1-2694 Consulta bandeja de solicitudes del AdN",
                "T-ADN1-2694 Cálculo automático del periodo",
            ],
            [case.title for case in cases],
        )

    def test_parse_xray_test_executions_keeps_six_cases_in_order(self) -> None:
        source = """1
TAP-79276
T-ADN1-2694 Consulta bandeja de solicitudes del AdN
Cucumber
0
TO DO

2
TAP-79277
T-ADN1-2694 Cálculo automático del periodo
Cucumber
0
TO DO

3
TAP-79278
T-ADN1-2694 Consulta solicitudes APPLICATION
Cucumber
0
TO DO

4
TAP-79279
T-ADN1-2694 Consulta pre-solicitudes PRE_APPLICATION
Cucumber
0
TO DO

5
TAP-79280
T-ADN1-2694 Respuesta separada por secciones
Cucumber
0
TO DO

6
TAP-79281
T-ADN1-2694 Error por salesRepReference no resuelto
Cucumber
0
TO DO"""

        cases = parse_xray_tests(source)

        self.assertEqual(
            ["TAP-79276", "TAP-79277", "TAP-79278", "TAP-79279", "TAP-79280", "TAP-79281"],
            [case.xray_test for case in cases],
        )
        self.assertEqual("T-ADN1-2694 Error por salesRepReference no resuelto", cases[-1].title)

    def test_parse_xray_tests_supports_tabs_and_ignores_metadata(self) -> None:
        source = (
            "1\tTAP-80001\tT-ABC-1234 Primer caso\tCucumber\t0\tTO DO\n"
            "2\tTAP-80002\tT-XYZ-999 Segundo caso\tManual\t0\tPASS\n"
            "3\tTAP-80003\tT-ABC-1235 Tercer caso\tCucumber\t0\tBLOCKED"
        )

        cases = parse_xray_tests(source)

        self.assertEqual(["TAP-80001", "TAP-80002", "TAP-80003"], [case.xray_test for case in cases])
        self.assertEqual(
            ["T-ABC-1234 Primer caso", "T-XYZ-999 Segundo caso", "T-ABC-1235 Tercer caso"],
            [case.title for case in cases],
        )
        metadata = {"Cucumber", "0", "TO DO", "PASS", "FAIL", "BLOCKED"}
        self.assertTrue(all(case.title not in metadata for case in cases))

    def test_parse_real_jira_markdown_table(self) -> None:
        source = """| 1  | [TAP-79276](https://mibancoinnova.atlassian.net/browse/TAP-79276) | T-ADN1-2694 Consulta bandeja de solicitudes del AdN | Cucumber | | 0 | **TO DO** |
| :- | :---------------------------------------------------------------- | :-------------------------------------------------- | :------- | :- | - | :-------- |
|    | | 2 | [TAP-79277](https://mibancoinnova.atlassian.net/browse/TAP-79277) | T-ADN1-2694 Cálculo automático del periodo | Cucumber | | 0 | **TO DO** |
|    | | 3 | [TAP-79278](https://mibancoinnova.atlassian.net/browse/TAP-79278) | T-ADN1-2694 Consulta solicitudes APPLICATION | Cucumber | | 0 | **TO DO** |
|    | | 4 | [TAP-79279](https://mibancoinnova.atlassian.net/browse/TAP-79279) | T-ADN1-2694 Consulta pre-solicitudes PRE_APPLICATION | Cucumber | | 0 | **TO DO** |
|    | | 5 | [TAP-79280](https://mibancoinnova.atlassian.net/browse/TAP-79280) | T-ADN1-2694 Respuesta separada por secciones | Cucumber | | 0 | **TO DO** |
|    | | 6 | [TAP-79281](https://mibancoinnova.atlassian.net/browse/TAP-79281) | T-ADN1-2694 Error por salesRepReference no resuelto | Cucumber | | 0 | **TO DO** |"""

        cases = parse_xray_tests(source)

        self.assertEqual(
            ["TAP-79276", "TAP-79277", "TAP-79278", "TAP-79279", "TAP-79280", "TAP-79281"],
            [case.xray_test for case in cases],
        )
        self.assertEqual(
            [
                "T-ADN1-2694 Consulta bandeja de solicitudes del AdN",
                "T-ADN1-2694 Cálculo automático del periodo",
                "T-ADN1-2694 Consulta solicitudes APPLICATION",
                "T-ADN1-2694 Consulta pre-solicitudes PRE_APPLICATION",
                "T-ADN1-2694 Respuesta separada por secciones",
                "T-ADN1-2694 Error por salesRepReference no resuelto",
            ],
            [case.title for case in cases],
        )
        forbidden = ("Cucumber", "0", "TO DO", "**", "https://")
        self.assertTrue(all(not any(value in case.title for value in forbidden) for case in cases))

    def test_parse_markdown_handles_empty_columns_and_tap_duplicates(self) -> None:
        source = """| | | 6 | [TAP-79281](https://example.test/TAP-79281) | T-CUSTOMER-123 Consulta cliente | Cucumber | | 0 | **TO DO** |
| | 7 | [TAP-79281](https://example.test/TAP-79281) | T-CUSTOMER-999 Debe ignorarse por duplicado | Cucumber | | 0 | **PASS** |"""

        cases = parse_xray_tests(source)

        self.assertEqual(1, len(cases))
        self.assertEqual("TAP-79281", cases[0].xray_test)
        self.assertEqual("T-CUSTOMER-123 Consulta cliente", cases[0].title)

    def test_generates_one_populated_block_per_xray_test(self) -> None:
        template = Path("templates/Evidencias_APIs_template.docx")
        original_hash = sha256(template.read_bytes()).hexdigest()
        cases = [
            EvidenceCase("TAP-79281", "T-ADN1-2694 Error por salesRepReference no resuelto", "POST", "/sales", "400", "Bad Request", '{"id": 1}', '{"error": "unresolved"}', "Se valida el error."),
            EvidenceCase("TAP-79280", "T-ADN1-2694 Respuesta separada por secciones", "GET", "/sections", "200", "OK", "", '{"items": []}', "Se valida la respuesta."),
            EvidenceCase("TAP-79279", "T-ADN1-2694 Consulta pre-solicitudes PRE_APPLICATION"),
            EvidenceCase("TAP-79278", "T-ADN1-2694 Consulta solicitudes APPLICATION", "DELETE", "/requests/1"),
        ]
        data = ApiEvidenceData("ADN1-2694", "Diego Molina", "21/09/2026", "Customer Request", "TP-123", cases)

        with TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / evidence_filename(data.jira)
            generate_api_evidence(data, template, output)
            document = Document(output)

            general, *evidence_tables = document.tables
            self.assertEqual(5, len(document.tables))
            self.assertEqual(data.qa_agile, general.cell(0, 1).text)
            self.assertEqual(DEFAULT_DOCUMENT_STATUS, general.cell(2, 1).text)
            self.assertEqual(data.test_plan, general.cell(3, 1).text)
            self.assertEqual([case.xray_test for case in cases], [table.cell(0, 1).text for table in evidence_tables])
            self.assertEqual(cases[0].method, evidence_tables[0].cell(0, 3).text)
            self.assertEqual(cases[1].response, evidence_tables[1].cell(4, 1).text)
            self.assertEqual("POST", evidence_tables[2].cell(0, 3).text)
            self.assertEqual([f"Evidencia: {case.title}" for case in cases], [
                paragraph.text.strip() for paragraph in document.paragraphs if paragraph.text.strip().startswith("Evidencia:")
            ])
            self.assertEqual([(6, 4)] * 4, [(len(table.rows), len(table.columns)) for table in evidence_tables])

            with ZipFile(template) as source, ZipFile(output) as generated:
                self.assertEqual(source.read("word/media/image1.png"), generated.read("word/media/image1.png"))

        self.assertEqual(original_hash, sha256(template.read_bytes()).hexdigest())


if __name__ == "__main__":
    unittest.main()
