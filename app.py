"""Aplicación local para generar casos de prueba e informes QA."""

from __future__ import annotations

from datetime import date
import logging
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from csv_generator import generate_csv
from evidence_generator import ApiEvidenceData, EvidenceCase, evidence_filename, generate_api_evidence, parse_test_titles
from mobile_evidence_generator import (
    MobileEvidenceData,
    generate_mobile_evidence,
    mobile_evidence_filename,
)
from filename_helpers import sanitize_filename_component
from qa_engine import generate_test_cases, normalize_jira_text
from resource_paths import resource_path
from runtime_workspace import clean_runtime_workspace, configure_runtime_logging


MINIMUM_PYTHON = (3, 11)
MINIMUM_TK = 8.6
EVIDENCE_TEMPLATES = {
    "API": "Evidencias_APIs_template.docx",
    "MOBILE": "Evidencias_Mobile_template.docx",
}
LOGGER = logging.getLogger("qa_tools")


def downloads_directory() -> Path:
    """Obtiene Descargas del usuario actual o HOME cuando esa carpeta no existe."""
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()


def choose_document_destination(filename: str) -> Path | None:
    """Solicita un destino final para API o Mobile sin tocar el workspace temporal."""
    destination = filedialog.askdirectory(
        title="Seleccionar carpeta donde guardar el documento",
        initialdir=str(downloads_directory()),
    )
    if not destination:
        return None

    output_path = Path(destination) / filename
    if output_path.exists() and not messagebox.askyesno(
        "Archivo existente",
        f"El archivo ya existe:\n\n{output_path.name}\n\n¿Deseas reemplazarlo?",
    ):
        return None
    return output_path


def evidence_template_path(evidence_type: str) -> Path | None:
    """Obtiene la plantilla exclusiva del tipo elegido en la pantalla de evidencias."""
    filename = EVIDENCE_TEMPLATES.get(evidence_type)
    if filename is None:
        return None
    try:
        return resource_path(Path("templates") / filename)
    except FileNotFoundError as error:
        label = "API" if evidence_type == "API" else "Mobile"
        raise FileNotFoundError(f"No se encontró el template de evidencias {label}:\n{error.filename or error}") from error


def domain_validation_message(domain: str) -> str | None:
    """Valida el formato de dominio requerido para los títulos de Test en Xray."""
    if not domain.strip():
        return "El campo Dominio es obligatorio."
    if not domain.strip().endswith("/"):
        return "El campo Dominio debe finalizar con '/' para generar correctamente los títulos de los Test."
    return None


def install_callback_exception_handler(root: tk.Tk) -> None:
    """Hace visibles y registrables las excepciones no controladas de callbacks Tk."""
    def report_callback_exception(exception_type: type[BaseException], exception: BaseException, traceback: object) -> None:
        LOGGER.error(
            "TKINTER_CALLBACK_EXCEPTION",
            exc_info=(exception_type, exception, traceback),
        )
        try:
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un error al ejecutar la operación.\n\nRevisa el registro de QA Tools para más detalles.",
                parent=root,
            )
        except tk.TclError:
            LOGGER.exception("No se pudo mostrar el error del callback en la interfaz")

    root.report_callback_exception = report_callback_exception


def validate_runtime() -> bool:
    """Informa el entorno actual y evita abrir la interfaz si es incompatible."""
    python_version = sys.version.split()[0]
    python_path = sys.executable
    tk_version = tk.TkVersion
    compatible = sys.version_info >= MINIMUM_PYTHON and tk_version >= MINIMUM_TK

    if compatible:
        print(f"Entorno validado: Python {python_version} | Tcl/Tk {tk_version} | Intérprete: {python_path}")
        return True

    print("\nNo se puede iniciar QA Test Generator con este entorno.\n")
    print(f"Python detectado: {python_version}")
    print(f"Ruta de Python: {python_path}")
    print(f"Tcl/Tk detectado: {tk_version}")
    print("Mínimo requerido: Python 3.11 y Tcl/Tk 8.6.")
    print("\nInstale una versión actual de Python desde https://www.python.org/downloads/macos/")
    print("o mediante Homebrew: brew install python")
    print("Después ejecute: ./run.command")
    return False


class EvidenceCasePanel(ttk.Frame):
    """Tarjeta plegable que presenta el caso y título detectados desde Xray."""

    def __init__(self, parent: ttk.Frame, case: EvidenceCase, on_expand: object) -> None:
        super().__init__(parent, padding=(7, 5), style="EvidenceCard.TFrame")
        self.case = case
        self.on_expand = on_expand
        self.is_expanded = False
        self.header_var = tk.StringVar()

        ttk.Button(self, textvariable=self.header_var, command=self.toggle, style="CardHeader.TButton").grid(
            row=0, column=0, sticky="ew"
        )
        self.columnconfigure(0, weight=1)
        self.body = ttk.Frame(self, padding=(14, 10), style="EvidenceCard.TFrame")
        self.body.columnconfigure(1, weight=1)
        self._build_fields()
        self._refresh_header()

    def _build_fields(self) -> None:
        ttk.Label(self.body, text="Caso:").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(self.body, text=self.case.xray_test).grid(row=0, column=1, sticky="w", pady=3)
        ttk.Label(self.body, text="Título:").grid(row=1, column=0, sticky="w", pady=3)
        ttk.Label(self.body, text=self.case.title).grid(row=1, column=1, sticky="w", pady=3)

    def toggle(self) -> None:
        if self.is_expanded:
            self.collapse()
            return
        self.on_expand(self)

    def expand(self) -> None:
        if not self.is_expanded:
            self.body.grid(row=1, column=0, sticky="ew")
            self.is_expanded = True
            self._refresh_header()

    def collapse(self) -> None:
        if self.is_expanded:
            self.body.grid_remove()
            self.is_expanded = False
            self._refresh_header()

    def _refresh_header(self) -> None:
        icon = "▼" if self.is_expanded else "▶"
        self.header_var.set(f"{icon} {self.case.xray_test} - {self.case.display_title}")


class QATestGeneratorApp(ttk.Frame):
    """Ventana principal de la herramienta."""

    def __init__(self, root: tk.Tk) -> None:
        super().__init__(root, padding=16)
        self.root = root
        self.jira_var = tk.StringVar()
        self.analyst_var = tk.StringVar()
        self.repository_directory_var = tk.StringVar()
        self.domain_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Listo")
        self.evidence_type_var = tk.StringVar(value="")
        self.evidence_jira_var = tk.StringVar()
        self.qa_agile_var = tk.StringVar()
        self.service_var = tk.StringVar()
        self.test_plan_var = tk.StringVar()
        self.test_environment_var = tk.StringVar(value="QA")
        self.evidence_result_var = tk.StringVar(value="Listo")
        self.evidence_panels: list[EvidenceCasePanel] = []
        self.default_qa_agile = self.qa_agile_var.get()
        self._configure_window()
        self._build_interface()

    def _configure_window(self) -> None:
        self.root.title("QA Tools")
        self.root.minsize(900, 760)
        self.root.configure(background="#f4f7fb")
        self._configure_styles()
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        self.grid(sticky="nsew", padx=0, pady=0)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

    @staticmethod
    def _configure_styles() -> None:
        """Define la apariencia corporativa sin cambiar el comportamiento de los widgets."""
        style = ttk.Style()
        style.theme_use("clam")

        background = "#f4f7fb"
        surface = "#ffffff"
        navy = "#163a5f"
        blue = "#2f6fa8"
        border = "#d9e1eb"
        muted = "#607086"

        style.configure(".", background=background, foreground="#1f2937", font=("Helvetica", 12))
        style.configure("TFrame", background=background)
        style.configure("TLabel", background=background, foreground="#334155")
        style.configure("Field.TLabel", font=("Helvetica", 11, "bold"), foreground="#44546a")
        style.configure("Section.TLabel", font=("Helvetica", 11, "bold"), foreground=navy)
        style.configure("Description.TLabel", font=("Helvetica", 10), foreground=muted)
        style.configure("Status.TLabel", background="#edf4fa", foreground="#315a80", font=("Helvetica", 11))

        style.configure("TEntry", padding=(9, 7), fieldbackground=surface, bordercolor=border)
        style.map("TEntry", bordercolor=[("focus", blue)], lightcolor=[("focus", blue)], darkcolor=[("focus", blue)])
        style.configure("TCombobox", padding=(8, 6), fieldbackground=surface, bordercolor=border)
        style.map("TCombobox", bordercolor=[("focus", blue)])
        style.configure("TCheckbutton", background=surface, foreground="#334155", font=("Helvetica", 11))
        style.map("TCheckbutton", foreground=[("disabled", "#95a3b5")])

        style.configure("TNotebook", background=background, borderwidth=0, tabmargins=(0, 0, 0, 8))
        style.configure(
            "TNotebook.Tab",
            background="#e7edf5",
            foreground="#536276",
            font=("Helvetica", 11, "bold"),
            padding=(18, 9),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", navy), ("active", "#dce7f2")],
            foreground=[("selected", "#ffffff"), ("active", navy)],
        )

        style.configure("Card.TLabelframe", background=surface, bordercolor=border, relief="solid", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background=surface, foreground=navy, font=("Helvetica", 11, "bold"))
        style.configure("Card.TFrame", background=surface)
        style.configure("EvidenceCard.TFrame", background=surface, relief="solid", borderwidth=1, bordercolor=border)

        style.configure("Primary.TButton", background=navy, foreground="#ffffff", font=("Helvetica", 11, "bold"), padding=(16, 8), borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#0e2c49"), ("pressed", "#0a2138")])
        style.configure("Secondary.TButton", background="#e5eff8", foreground=navy, font=("Helvetica", 11, "bold"), padding=(14, 8), borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#d5e5f3")])
        style.configure("Tertiary.TButton", background=surface, foreground=muted, font=("Helvetica", 10, "bold"), padding=(12, 8), borderwidth=1, bordercolor=border)
        style.map("Tertiary.TButton", background=[("active", "#f0f4f8")], bordercolor=[("active", "#aebccc")])
        style.configure("New.TButton", background="#cfe2f3", foreground=navy, font=("Helvetica", 10, "bold"), padding=(12, 8), borderwidth=1, bordercolor="#b6d0e8")
        style.map("New.TButton", background=[("active", "#bdd8ee"), ("pressed", "#aacbe6")], bordercolor=[("active", "#8fb7d8")])
        style.configure("CardHeader.TButton", background="#f7f9fc", foreground=navy, font=("Helvetica", 11, "bold"), anchor="w", padding=(11, 7), borderwidth=0)
        style.map("CardHeader.TButton", background=[("active", "#e9f1f8")])

        style.configure("Vertical.TScrollbar", background="#d4dde8", troughcolor="#f4f7fb", borderwidth=0, arrowsize=12)

    def _build_interface(self) -> None:
        header = tk.Frame(self, background="#163a5f", height=76)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.columnconfigure(1, weight=1)
        tk.Label(header, text="◆", background="#163a5f", foreground="#8dc2ed", font=("Helvetica", 23, "bold")).grid(
            row=0, column=0, rowspan=2, padx=(28, 12), pady=13
        )
        tk.Label(header, text="QA Tools", background="#163a5f", foreground="#ffffff", font=("Helvetica", 21, "bold")).grid(
            row=0, column=1, sticky="sw", pady=(12, 0)
        )
        tk.Label(
            header,
            text="Gestión de casos y evidencias QA",
            background="#163a5f",
            foreground="#c5d9eb",
            font=("Helvetica", 10),
        ).grid(row=1, column=1, sticky="nw", pady=(1, 12))

        notebook = ttk.Notebook(self)
        notebook.grid(row=1, column=0, sticky="nsew", padx=20, pady=(12, 18))

        cases_tab = ttk.Frame(notebook, padding=18, style="TFrame")
        evidence_tab = ttk.Frame(notebook, padding=18, style="TFrame")
        notebook.add(cases_tab, text="▤  Generar Test Jira")
        notebook.add(evidence_tab, text="▧  Generar Docs de Evidencias")

        self._build_cases_tab(cases_tab)
        self._build_evidence_tab(evidence_tab)

    def _build_cases_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        general_card = ttk.LabelFrame(tab, text="DATOS GENERALES", style="Card.TLabelframe", padding=(16, 12))
        general_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        general_card.columnconfigure(1, weight=1)
        general_card.columnconfigure(3, weight=1)
        ttk.Label(
            general_card,
            text="Genera el archivo CSV para importar en Jira/Xray y crear los Test a partir de los criterios de aceptación definidos en la card de Jira.",
            style="Description.TLabel",
            wraplength=760,
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Label(general_card, text="Número Jira:", style="Field.TLabel").grid(row=1, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(general_card, textvariable=self.jira_var).grid(row=1, column=1, sticky="ew", pady=5)
        ttk.Label(general_card, text="Analista QA:", style="Field.TLabel").grid(row=1, column=2, sticky="w", pady=5, padx=(28, 14))
        ttk.Entry(general_card, textvariable=self.analyst_var).grid(row=1, column=3, sticky="ew", pady=5)
        ttk.Button(general_card, text="↻  NUEVO", command=self.reset_cases, style="New.TButton").grid(
            row=0, column=4, rowspan=4, sticky="n", padx=(16, 0), pady=5
        )
        ttk.Label(general_card, text="Directorio repositorio Xray:", style="Field.TLabel").grid(row=2, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(general_card, textvariable=self.repository_directory_var).grid(
            row=2, column=1, columnspan=3, sticky="ew", pady=5
        )
        ttk.Label(general_card, text="Dominio:", style="Field.TLabel").grid(row=3, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(general_card, textvariable=self.domain_var).grid(row=3, column=1, columnspan=3, sticky="ew", pady=5)

        criteria_card = ttk.LabelFrame(tab, text="CRITERIOS DE ACEPTACIÓN", style="Card.TLabelframe", padding=(16, 12))
        criteria_card.grid(row=1, column=0, sticky="nsew", pady=(0, 12))
        criteria_card.columnconfigure(0, weight=1)
        criteria_card.rowconfigure(0, weight=1)
        criteria_frame = ttk.Frame(criteria_card, style="Card.TFrame")
        criteria_frame.grid(row=0, column=0, sticky="nsew")
        criteria_frame.columnconfigure(0, weight=1)
        criteria_frame.rowconfigure(0, weight=1)
        self.criteria_text = self._create_text_area(criteria_frame, height=18)
        scrollbar = ttk.Scrollbar(criteria_frame, orient="vertical", command=self.criteria_text.yview)
        self.criteria_text.configure(yscrollcommand=scrollbar.set)
        self.criteria_text.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        footer = ttk.Frame(tab, style="TFrame")
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        status = ttk.Frame(footer, style="Card.TFrame", padding=(10, 6))
        status.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="ESTADO", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel", padding=(8, 2)).grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Button(footer, text="▣  GENERAR CSV", command=self.generate_cases, style="Primary.TButton").grid(
            row=0, column=1, sticky="e"
        )

    def _build_evidence_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        general_card = ttk.LabelFrame(tab, text="DATOS GENERALES", style="Card.TLabelframe", padding=(16, 12))
        general_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        general_card.columnconfigure(1, weight=1)
        general_card.columnconfigure(3, weight=1)
        ttk.Label(
            general_card,
            text="Genera el documento de evidencias para pruebas de APIs y Mobile.",
            style="Description.TLabel",
            wraplength=760,
        ).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        ttk.Label(general_card, text="Tipo de evidencia:", style="Field.TLabel").grid(row=1, column=0, sticky="w", pady=5, padx=(0, 14))
        evidence_type_frame = ttk.Frame(general_card, style="Card.TFrame")
        evidence_type_frame.grid(row=1, column=1, sticky="w", pady=5)
        ttk.Radiobutton(
            evidence_type_frame, text="API", value="API", variable=self.evidence_type_var, command=self.change_evidence_type
        ).grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(
            evidence_type_frame, text="Mobile", value="MOBILE", variable=self.evidence_type_var, command=self.change_evidence_type
        ).grid(row=0, column=1, sticky="w", padx=(16, 0))
        ttk.Button(general_card, text="↻  NUEVO", command=self.reset_evidence, style="New.TButton").grid(
            row=0, column=4, rowspan=5, sticky="n", padx=(16, 0), pady=5
        )

        self._add_evidence_entry(general_card, "Número Jira:", self.evidence_jira_var, 2)
        self._add_evidence_entry(general_card, "Test Plan:", self.test_plan_var, 2, column=2, label_padx=(28, 14))
        self._add_evidence_entry(general_card, "QA Agile:", self.qa_agile_var, 1, column=2, label_padx=(28, 14))
        self.service_label = ttk.Label(general_card, text="Servicio:", style="Field.TLabel")
        self.service_label.grid(row=3, column=0, sticky="w", pady=5, padx=(0, 14))
        self.service_entry = ttk.Entry(general_card, textvariable=self.service_var)
        self.service_entry.grid(row=3, column=1, columnspan=3, sticky="ew", pady=5)
        self.test_environment_label = ttk.Label(general_card, text="Entorno de prueba:", style="Field.TLabel")
        self.test_environment_label.grid(row=4, column=0, sticky="w", pady=5, padx=(0, 14))
        self.test_environment_combo = ttk.Combobox(
            general_card, textvariable=self.test_environment_var, values=("QA", "STG"), state="readonly"
        )
        self.test_environment_combo.grid(row=4, column=1, sticky="ew", pady=5)

        content_card = ttk.LabelFrame(tab, text="TÍTULOS DE LOS TEST", style="Card.TLabelframe", padding=(16, 10))
        self.evidence_content_card = content_card
        content_card.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        content_card.columnconfigure(0, weight=1)
        titles_frame = ttk.Frame(content_card, style="Card.TFrame")
        titles_frame.grid(row=0, column=0, sticky="ew")
        titles_frame.columnconfigure(0, weight=1)
        titles_frame.rowconfigure(0, weight=1)
        self.test_titles_text = self._create_text_area(titles_frame, height=6)
        titles_scrollbar = ttk.Scrollbar(titles_frame, orient="vertical", command=self.test_titles_text.yview)
        self.test_titles_text.configure(yscrollcommand=titles_scrollbar.set)
        self.test_titles_text.grid(row=0, column=0, sticky="nsew")
        titles_scrollbar.grid(row=0, column=1, sticky="ns")

        ttk.Button(content_card, text="⇣  CARGAR CASOS", command=self.load_evidence_cases, style="Secondary.TButton").grid(
            row=1, column=0, sticky="e", pady=(10, 0)
        )

        cards_card = ttk.LabelFrame(
            tab,
            text="CASOS DETECTADOS (0)",
            style="Card.TLabelframe",
            padding=(16, 10),
        )
        self.cards_card = cards_card
        cards_card.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        cards_card.columnconfigure(0, weight=1)
        cards_card.rowconfigure(0, weight=1)
        cards_frame = ttk.Frame(cards_card, style="Card.TFrame")
        cards_frame.grid(row=0, column=0, sticky="nsew")
        cards_frame.columnconfigure(0, weight=1)
        cards_frame.rowconfigure(0, weight=1)
        self.cards_canvas = tk.Canvas(cards_frame, highlightthickness=0, background="#ffffff")
        cards_scrollbar = ttk.Scrollbar(cards_frame, orient="vertical", command=self.cards_canvas.yview)
        self.cards_container = ttk.Frame(self.cards_canvas)
        self.cards_window = self.cards_canvas.create_window((0, 0), window=self.cards_container, anchor="nw")
        self.cards_canvas.configure(yscrollcommand=cards_scrollbar.set)
        self.cards_container.bind("<Configure>", self._update_cards_scroll_region)
        self.cards_canvas.bind("<Configure>", self._resize_cards_container)
        self.cards_canvas.grid(row=0, column=0, sticky="nsew")
        cards_scrollbar.grid(row=0, column=1, sticky="ns")
        self._bind_cards_scroll_events(self.cards_canvas)

        footer = ttk.Frame(tab, style="TFrame")
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        status = ttk.Frame(footer, style="Card.TFrame", padding=(10, 6))
        status.grid(row=0, column=0, sticky="ew", padx=(0, 16))
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="ESTADO", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(status, textvariable=self.evidence_result_var, style="Status.TLabel", padding=(8, 2)).grid(
            row=0, column=1, sticky="ew"
        )
        ttk.Button(footer, text="▣  GENERAR DOCUMENTO", command=self.generate_evidence, style="Primary.TButton").grid(
            row=0, column=1, sticky="e"
        )

    @staticmethod
    def _create_text_area(parent: ttk.Frame, height: int) -> tk.Text:
        return tk.Text(
            parent,
            wrap="word",
            height=height,
            undo=True,
            background="#ffffff",
            foreground="#1f2937",
            insertbackground="#163a5f",
            relief="solid",
            borderwidth=1,
            highlightthickness=1,
            highlightbackground="#d9e1eb",
            highlightcolor="#5a8dbd",
            padx=10,
            pady=9,
        )

    @staticmethod
    def _add_evidence_entry(
        tab: ttk.Frame,
        label: str,
        variable: tk.StringVar,
        row: int,
        column: int = 0,
        label_padx: tuple[int, int] = (0, 14),
        entry_columnspan: int = 1,
    ) -> None:
        ttk.Label(tab, text=label, style="Field.TLabel").grid(
            row=row, column=column, sticky="w", pady=5, padx=label_padx
        )
        ttk.Entry(tab, textvariable=variable).grid(
            row=row, column=column + 1, columnspan=entry_columnspan, sticky="ew", pady=5
        )

    @staticmethod
    def _add_status_bar(tab: ttk.Frame, variable: tk.StringVar, row: int) -> None:
        status = ttk.Frame(tab, style="Card.TFrame", padding=(10, 6))
        status.grid(row=row, column=0, sticky="ew")
        status.columnconfigure(1, weight=1)
        ttk.Label(status, text="ESTADO", style="Section.TLabel").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Label(status, textvariable=variable, style="Status.TLabel", padding=(8, 2)).grid(row=0, column=1, sticky="ew")

    def load_evidence_cases(self) -> bool:
        if self.evidence_type_var.get() not in EVIDENCE_TEMPLATES:
            self._show_required_field("Seleccione API o Mobile como tipo de evidencia.")
            return False
        cases = parse_test_titles(self.test_titles_text.get("1.0", "end-1c"))
        if not cases:
            self._show_required_field("No se encontraron títulos de test para cargar.")
            return False

        for panel in self.evidence_panels:
            panel.destroy()
        self.evidence_panels = []
        for row, case in enumerate(cases):
            panel = EvidenceCasePanel(self.cards_container, case, self.expand_evidence_case)
            panel.grid(row=row, column=0, sticky="ew")
            self._bind_cards_scroll_events(panel)
            self.evidence_panels.append(panel)
        self.cards_container.columnconfigure(0, weight=1)
        detected_count = len(self.evidence_panels)
        self._set_evidence_cases_count(detected_count)
        self.evidence_result_var.set(f"{detected_count} casos detectados correctamente.")
        return True

    def change_evidence_type(self) -> None:
        """Conserva la misma captura de datos; solo cambia el generador de salida."""
        selected_type = self.evidence_type_var.get()
        if selected_type == "MOBILE":
            self.service_label.grid_remove()
            self.service_entry.grid_remove()
            self.test_environment_label.grid_configure(row=3)
            self.test_environment_combo.grid_configure(row=3)
        else:
            self.service_label.grid()
            self.service_entry.grid()
            self.test_environment_label.grid_configure(row=4)
            self.test_environment_combo.grid_configure(row=4)
        self.evidence_result_var.set(f"Modo {selected_type}: use CARGAR CASOS con los títulos de Jira.")

    def _clear_evidence_cases(self) -> None:
        for panel in self.evidence_panels:
            panel.destroy()
        self.evidence_panels = []
        self.cards_canvas.configure(scrollregion=(0, 0, 0, 0))
        self._set_evidence_cases_count(0)

    def expand_evidence_case(self, selected_panel: EvidenceCasePanel) -> None:
        for panel in self.evidence_panels:
            if panel is selected_panel:
                panel.expand()
            else:
                panel.collapse()

    def _update_cards_scroll_region(self, _: tk.Event[ttk.Frame]) -> None:
        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox("all"))

    def _resize_cards_container(self, event: tk.Event[tk.Canvas]) -> None:
        self.cards_canvas.itemconfigure(self.cards_window, width=event.width)

    def _bind_cards_scroll_events(self, widget: tk.Misc) -> None:
        """Asigna scroll vertical al canvas solo dentro de Casos detectados."""
        widget.bind("<MouseWheel>", self._scroll_cards, add="+")
        widget.bind("<Button-4>", lambda _: self._scroll_cards_by(-1), add="+")
        widget.bind("<Button-5>", lambda _: self._scroll_cards_by(1), add="+")
        for child in widget.winfo_children():
            self._bind_cards_scroll_events(child)

    def _scroll_cards(self, event: tk.Event[tk.Misc]) -> str:
        if event.delta:
            self._scroll_cards_by(-1 if event.delta > 0 else 1)
        return "break"

    def _scroll_cards_by(self, units: int) -> str:
        self.cards_canvas.yview_scroll(units, "units")
        return "break"

    def reset_cases(self) -> None:
        """Limpia únicamente el estado temporal de Generar Casos."""
        if self._cases_have_data() and not self._confirm_new_document():
            return

        clean_runtime_workspace()
        self.jira_var.set("")
        self.analyst_var.set("")
        self.repository_directory_var.set("")
        self.domain_var.set("")
        self.criteria_text.delete("1.0", "end")
        self.status_var.set("Listo")

    def reset_evidence(self) -> None:
        """Limpia únicamente el estado temporal de Generar Evidencia."""
        if self._evidence_has_data() and not self._confirm_new_document():
            return

        clean_runtime_workspace()
        self.evidence_type_var.set("")
        self.evidence_jira_var.set("")
        self.qa_agile_var.set(self.default_qa_agile)
        self.service_var.set("")
        self.test_plan_var.set("")
        self.test_environment_var.set("QA")
        self.test_titles_text.delete("1.0", "end")
        self._clear_evidence_cases()
        self.evidence_result_var.set("Listo")

    def _set_evidence_cases_count(self, count: int) -> None:
        """Actualiza el encabezado con el total real de tarjetas de evidencia."""
        self.cards_card.configure(text=f"CASOS DETECTADOS ({count})")

    def _cases_have_data(self) -> bool:
        return any(
            value.get().strip() for value in (self.jira_var, self.analyst_var, self.repository_directory_var, self.domain_var)
        ) or bool(self.criteria_text.get("1.0", "end-1c").strip())

    def _evidence_has_data(self) -> bool:
        return (
            bool(self.evidence_type_var.get())
            or any(
                value.get().strip()
                for value in (
                    self.evidence_jira_var,
                    self.service_var,
                    self.test_plan_var,
                )
            )
            or self.qa_agile_var.get() != self.default_qa_agile
            or bool(self.test_titles_text.get("1.0", "end-1c").strip())
            or bool(self.evidence_panels)
        )

    def _confirm_new_document(self) -> bool:
        dialog = tk.Toplevel(self.root)
        dialog.title("Nuevo documento")
        dialog.transient(self.root)
        dialog.resizable(False, False)
        dialog.grab_set()

        content = ttk.Frame(dialog, padding=16)
        content.grid(sticky="nsew")
        ttk.Label(content, text="¿Deseas iniciar un nuevo documento?").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(content, text="Se eliminará la información actual de esta pestaña.").grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(4, 16)
        )

        confirmed = tk.BooleanVar(value=False)
        ttk.Button(content, text="Cancelar", command=dialog.destroy).grid(row=2, column=0, sticky="e", padx=(0, 8))
        ttk.Button(
            content,
            text="Nuevo documento",
            command=lambda: (confirmed.set(True), dialog.destroy()),
        ).grid(row=2, column=1, sticky="w")

        dialog.protocol("WM_DELETE_WINDOW", dialog.destroy)
        dialog.wait_window()
        return confirmed.get()

    def generate_cases(self) -> None:
        LOGGER.info("GENERAR_CSV_START")
        jira = self.jira_var.get().strip()
        analyst = self.analyst_var.get().strip()
        repository_directory = self.repository_directory_var.get().strip()
        domain = self.domain_var.get().strip()
        criteria = self.criteria_text.get("1.0", "end-1c").strip()

        if not jira:
            self._show_required_field("Debe ingresar el número de Jira.")
            return
        if not analyst:
            self._show_required_field("Debe ingresar el analista QA.")
            return
        if not repository_directory:
            self._show_required_field("Debe ingresar el directorio repositorio Xray.")
            return
        domain_error = domain_validation_message(domain)
        if domain_error:
            self.status_var.set(domain_error)
            self._show_required_field(domain_error)
            return
        if not criteria:
            self._show_required_field("Debe ingresar los criterios de aceptación.")
            return

        normalized_criteria = normalize_jira_text(criteria)
        test_cases = generate_test_cases(jira, analyst, normalized_criteria, repository_directory=repository_directory)
        if not test_cases:
            self._show_required_field("No se encontraron criterios de aceptación identificados con el formato CA-XX.")
            return

        LOGGER.info("GENERAR_CSV_OPEN_DIRECTORY_DIALOG")
        destination = filedialog.askdirectory(
            title="Seleccionar carpeta de destino",
            initialdir=str(downloads_directory()),
        )
        if not destination:
            LOGGER.info("GENERAR_CSV_CANCELLED")
            self.status_var.set("Generación cancelada")
            return

        try:
            csv_path = Path(destination) / f"carga casos XRAY {sanitize_filename_component(jira, fallback='SIN_JIRA')}.csv"
            LOGGER.info("GENERAR_CSV_START_WRITE destination=%s", csv_path.parent)
            generate_csv(csv_path, test_cases, domain)
        except Exception:
            self.status_var.set("No se pudieron generar los casos")
            messagebox.showerror(
                "Error al generar casos",
                "No fue posible generar el archivo CSV. Verifique la carpeta seleccionada e inténtelo nuevamente.",
            )
            return

        self.status_var.set("Casos generados correctamente.")
        LOGGER.info("GENERAR_CSV_OK path=%s", csv_path)
        messagebox.showinfo("Generación completada", f"Casos generados correctamente:\n\n{csv_path.name}")

    def generate_evidence(self) -> None:
        LOGGER.info("GENERAR_DOCUMENTO_START type=%s", self.evidence_type_var.get())
        if self.evidence_type_var.get() == "MOBILE":
            self.generate_mobile_evidence()
            return
        try:
            template_path = self._selected_evidence_template()
        except FileNotFoundError as error:
            self.evidence_result_var.set("No se encontró el template de evidencias API")
            messagebox.showerror("Template no encontrado", str(error))
            return
        if template_path is None:
            self._show_required_field("Seleccione un tipo de evidencia para generar el documento.")
            return

        execution_date = date.today().strftime("%d/%m/%Y")
        jira = self.evidence_jira_var.get().strip()
        qa_agile = self.qa_agile_var.get().strip()
        if not jira:
            self._show_required_field("Ingrese el número Jira.")
            return
        if not qa_agile:
            self._show_required_field("Ingrese el analista QA.")
            return

        if not self.evidence_panels and not self.load_evidence_cases():
            return
        service = self.service_var.get()
        evidence_cases = [
            EvidenceCase(
                xray_test=panel.case.xray_test,
                title=panel.case.title,
                method="POST",
                endpoint=service,
                status_response="200",
                value_status_response="OK",
            )
            for panel in self.evidence_panels
        ]

        data = ApiEvidenceData(
            jira=jira,
            qa_agile=qa_agile,
            execution_date=execution_date,
            service=service,
            test_plan=self.test_plan_var.get(),
            cases=evidence_cases,
            test_environment=self.test_environment_var.get(),
        )
        LOGGER.info("GENERAR_DOCUMENTO_OPEN_DIRECTORY_DIALOG type=API")
        output_path = choose_document_destination(evidence_filename(jira))
        if output_path is None:
            LOGGER.info("GENERAR_DOCUMENTO_CANCELLED type=API")
            return

        try:
            LOGGER.info("GENERAR_DOCUMENTO_START_WRITE type=API destination=%s", output_path.parent)
            generate_api_evidence(data, template_path, output_path)
        except Exception:
            self.evidence_result_var.set("No se pudo generar la evidencia")
            messagebox.showerror(
                "Error al generar evidencia",
                "No fue posible generar el documento. Verifique la plantilla y la carpeta seleccionada.",
            )
            return

        message = f"Evidencia API generada correctamente: {len(evidence_cases)} tests."
        self.evidence_result_var.set(message)
        LOGGER.info("GENERAR_DOCUMENTO_OK type=API path=%s", output_path)
        messagebox.showinfo("Generación completada", f"{message}\n\n{output_path.name}\n\nGuardado en:\n{output_path.parent}")

    def generate_mobile_evidence(self) -> None:
        """Genera escenarios Mobile desde los mismos casos detectados que consume API."""
        jira = self.evidence_jira_var.get().strip()
        qa_agile = self.qa_agile_var.get().strip()
        if not jira:
            self._show_required_field("Ingrese el número Jira.")
            return
        if not qa_agile:
            self._show_required_field("Ingrese el analista QA.")
            return
        if not self.evidence_panels and not self.load_evidence_cases():
            return

        data = MobileEvidenceData(
            qa_agile=qa_agile,
            execution_date=date.today().strftime("%d/%m/%Y"),
            test_plan=self.test_plan_var.get().strip(),
            test_environment=self.test_environment_var.get(),
        )

        try:
            template_path = self._selected_evidence_template()
        except FileNotFoundError as error:
            self.evidence_result_var.set("No se encontró el template de evidencias Mobile")
            messagebox.showerror("Template no encontrado", str(error))
            return
        LOGGER.info("GENERAR_DOCUMENTO_OPEN_DIRECTORY_DIALOG type=MOBILE")
        output_path = choose_document_destination(mobile_evidence_filename(jira))
        if output_path is None:
            LOGGER.info("GENERAR_DOCUMENTO_CANCELLED type=MOBILE")
            return
        try:
            LOGGER.info("GENERAR_DOCUMENTO_START_WRITE type=MOBILE destination=%s", output_path.parent)
            generate_mobile_evidence(data, [panel.case for panel in self.evidence_panels], template_path, output_path)
        except (OSError, ValueError) as error:
            self.evidence_result_var.set("No se pudo generar el reporte")
            messagebox.showerror("Error al generar reporte", str(error))
            return

        self.evidence_result_var.set("Reporte Mobile generado correctamente.")
        LOGGER.info("GENERAR_DOCUMENTO_OK type=MOBILE path=%s", output_path)
        messagebox.showinfo(
            "Generación completada",
            f"Reporte Mobile generado correctamente:\n\n{output_path.name}\n\nGuardado en:\n{output_path.parent}",
        )

    def _selected_evidence_template(self) -> Path | None:
        """Devuelve la plantilla correspondiente al tipo de evidencia elegido."""
        return evidence_template_path(self.evidence_type_var.get())

    @staticmethod
    def _show_required_field(message: str) -> None:
        messagebox.showwarning("Campo obligatorio", message)


def main() -> None:
    if not validate_runtime():
        return
    configure_runtime_logging()
    clean_runtime_workspace()
    root = tk.Tk()
    install_callback_exception_handler(root)
    QATestGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
