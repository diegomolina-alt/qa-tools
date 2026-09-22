"""Aplicación local para generar casos de prueba e informes QA."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from csv_generator import generate_csv
from evidence_generator import ApiEvidenceData, EvidenceCase, evidence_filename, generate_api_evidence, parse_xray_tests
from qa_engine import generate_test_cases


MINIMUM_PYTHON = (3, 11)
MINIMUM_TK = 8.6


def downloads_directory() -> Path:
    """Obtiene Descargas del usuario actual o HOME cuando esa carpeta no existe."""
    downloads = Path.home() / "Downloads"
    return downloads if downloads.is_dir() else Path.home()


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
        self.header_var.set(f"{icon} {self.case.xray_test} - {self.case.title}")


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
        self.api_evidence_var = tk.BooleanVar(value=False)
        self.mobile_evidence_var = tk.BooleanVar(value=False)
        self.evidence_jira_var = tk.StringVar()
        self.qa_agile_var = tk.StringVar()
        self.service_var = tk.StringVar()
        self.test_plan_var = tk.StringVar()
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
        notebook.add(cases_tab, text="▤  Generar Casos")
        notebook.add(evidence_tab, text="▧  Generar Evidencia")

        self._build_cases_tab(cases_tab)
        self._build_evidence_tab(evidence_tab)

    def _build_cases_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)

        general_card = ttk.LabelFrame(tab, text="DATOS GENERALES", style="Card.TLabelframe", padding=(16, 12))
        general_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        general_card.columnconfigure(1, weight=1)
        general_card.columnconfigure(3, weight=1)
        ttk.Label(general_card, text="Número Jira:", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(general_card, textvariable=self.jira_var).grid(row=0, column=1, sticky="ew", pady=5)
        ttk.Label(general_card, text="Analista QA:", style="Field.TLabel").grid(row=0, column=2, sticky="w", pady=5, padx=(28, 14))
        ttk.Entry(general_card, textvariable=self.analyst_var).grid(row=0, column=3, sticky="ew", pady=5)
        ttk.Button(general_card, text="↻  NUEVO", command=self.reset_cases, style="New.TButton").grid(
            row=0, column=4, rowspan=3, sticky="n", padx=(16, 0), pady=5
        )
        ttk.Label(general_card, text="Directorio repositorio Xray:", style="Field.TLabel").grid(row=1, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(general_card, textvariable=self.repository_directory_var).grid(
            row=1, column=1, columnspan=3, sticky="ew", pady=5
        )
        ttk.Label(general_card, text="Dominio:", style="Field.TLabel").grid(row=2, column=0, sticky="w", pady=5, padx=(0, 14))
        ttk.Entry(general_card, textvariable=self.domain_var).grid(row=2, column=1, columnspan=3, sticky="ew", pady=5)

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
        ttk.Button(footer, text="▣  GENERAR CASOS", command=self.generate_cases, style="Primary.TButton").grid(
            row=0, column=1, sticky="e"
        )

    def _build_evidence_tab(self, tab: ttk.Frame) -> None:
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(2, weight=1)

        general_card = ttk.LabelFrame(tab, text="DATOS GENERALES", style="Card.TLabelframe", padding=(16, 12))
        general_card.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        general_card.columnconfigure(1, weight=1)
        general_card.columnconfigure(3, weight=1)
        ttk.Label(general_card, text="Tipo de evidencia:", style="Field.TLabel").grid(row=0, column=0, sticky="w", pady=5, padx=(0, 14))
        evidence_type_frame = ttk.Frame(general_card, style="Card.TFrame")
        evidence_type_frame.grid(row=0, column=1, sticky="w", pady=5)
        ttk.Checkbutton(evidence_type_frame, text="API", variable=self.api_evidence_var).grid(row=0, column=0, sticky="w")
        self.mobile_evidence_button = ttk.Checkbutton(
            evidence_type_frame,
            text="Mobile (pendiente)",
            variable=self.mobile_evidence_var,
            state="disabled",
        )
        self.mobile_evidence_button.grid(row=0, column=1, sticky="w", padx=(16, 0))
        ttk.Button(general_card, text="↻  NUEVO", command=self.reset_evidence, style="New.TButton").grid(
            row=0, column=4, rowspan=2, sticky="n", padx=(16, 0), pady=5
        )

        self._add_evidence_entry(general_card, "Número Jira:", self.evidence_jira_var, 1)
        self._add_evidence_entry(general_card, "Test Plan:", self.test_plan_var, 1, column=2, label_padx=(28, 14))
        self._add_evidence_entry(general_card, "QA Agile:", self.qa_agile_var, 0, column=2, label_padx=(28, 14))
        self._add_evidence_entry(general_card, "Servicio:", self.service_var, 2, entry_columnspan=3)

        content_card = ttk.LabelFrame(tab, text="TÍTULOS DE LOS TEST", style="Card.TLabelframe", padding=(16, 10))
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
        ttk.Button(footer, text="▣  GENERAR EVIDENCIA", command=self.generate_evidence, style="Primary.TButton").grid(
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
        cases = parse_xray_tests(self.test_titles_text.get("1.0", "end-1c"))
        if not cases:
            self._show_required_field("No se encontraron casos con el formato Xray Test.")
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

        self.api_evidence_var.set(False)
        self.mobile_evidence_var.set(False)
        self.evidence_jira_var.set("")
        self.qa_agile_var.set(self.default_qa_agile)
        self.service_var.set("")
        self.test_plan_var.set("")
        self.test_titles_text.delete("1.0", "end")
        for panel in self.evidence_panels:
            panel.destroy()
        self.evidence_panels = []
        self.cards_canvas.configure(scrollregion=(0, 0, 0, 0))
        self._set_evidence_cases_count(0)
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
            self.api_evidence_var.get()
            or self.mobile_evidence_var.get()
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
        if not domain:
            self._show_required_field("Ingresa el Dominio para generar los casos.")
            return
        if not criteria:
            self._show_required_field("Debe ingresar los criterios de aceptación.")
            return

        test_cases = generate_test_cases(jira, analyst, criteria, repository_directory=repository_directory)
        if not test_cases:
            self._show_required_field("No se encontraron criterios de aceptación identificados con el formato CA-XX.")
            return

        destination = filedialog.askdirectory(
            title="Seleccionar carpeta de destino",
            initialdir=str(downloads_directory()),
        )
        if not destination:
            self.status_var.set("Generación cancelada")
            return

        try:
            csv_path = Path(destination) / f"carga casos XRAY {jira}.csv"
            generate_csv(csv_path, test_cases, domain)
        except Exception:
            self.status_var.set("No se pudieron generar los casos")
            messagebox.showerror(
                "Error al generar casos",
                "No fue posible generar el archivo CSV. Verifique la carpeta seleccionada e inténtelo nuevamente.",
            )
            return

        self.status_var.set("Casos generados correctamente.")
        messagebox.showinfo("Generación completada", f"Casos generados correctamente:\n\n{csv_path.name}")

    def generate_evidence(self) -> None:
        template_path = self._selected_evidence_template()
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

        destination = filedialog.askdirectory(
            title="Seleccionar carpeta de destino",
            initialdir=str(downloads_directory()),
        )
        if not destination:
            self.evidence_result_var.set("Generación cancelada")
            return

        data = ApiEvidenceData(
            jira=jira,
            qa_agile=qa_agile,
            execution_date=execution_date,
            service=service,
            test_plan=self.test_plan_var.get(),
            cases=evidence_cases,
        )
        output_path = Path(destination) / evidence_filename(jira)

        try:
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
        messagebox.showinfo("Generación completada", f"{message}\n\n{output_path.name}")

    def _selected_evidence_template(self) -> Path | None:
        """Devuelve la plantilla correspondiente al tipo de evidencia elegido."""
        if self.api_evidence_var.get():
            return Path(__file__).parent / "templates" / "Evidencias_APIs_template.docx"
        return None

    @staticmethod
    def _show_required_field(message: str) -> None:
        messagebox.showwarning("Campo obligatorio", message)


def main() -> None:
    if not validate_runtime():
        return
    root = tk.Tk()
    QATestGeneratorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
