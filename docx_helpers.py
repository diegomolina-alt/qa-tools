"""Helpers compartidos para conservar el formato definido en templates DOCX."""

from docx.text.paragraph import Paragraph


def set_scenario_title_text(paragraph: Paragraph, value: str) -> None:
    """Actualiza el marcador del título sin perder su formato tipográfico.

    El primer ``run`` del marcador contiene el formato del template. Modificar
    únicamente su texto preserva fuente, tamaño, negrita y demás propiedades
    para los documentos API y Mobile.
    """
    if paragraph.runs:
        paragraph.runs[0].text = value
        for run in paragraph.runs[1:]:
            run.text = ""
        return

    # Compatibilidad con templates que no incluyan un run de marcador.
    paragraph.add_run(value)
