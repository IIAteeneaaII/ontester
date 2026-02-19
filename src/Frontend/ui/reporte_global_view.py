# src/Frontend/ui/reporte_global_view.py
import customtkinter as ctk
import sys
import csv  # (si no lo usas, puedes quitarlo)
from datetime import date
from pathlib import Path

# Para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion
from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable


class ReporteGlobalView(ctk.CTkFrame):
    """
    Vista de Reporte Global - Título, contenido central y panel de pruebas.
    """

    def __init__(self, parent, modelo=None, viewmodel=None, **kwargs):
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)

        self.viewmodel = viewmodel
        self.modelo = modelo

        app = self.winfo_toplevel()
        self.q = getattr(app, "event_q", None)

        # Datos / referencias de tabla
        self.table_rows = []
        self.row_widgets = []

        # Headers de tabla
        self._headers = [
            "ID", "SERIE", "MAC", "VERSION_INICIAL", "VERSION_FINAL", "MODELO",
            "FECHA_DE_PRUEBA", "VERSION_DE_ONT_TES",
            "SSID", "SSID5", "CONTRASEÑA", "STATUS"
        ]

        self._header_cells = []  # lista de (frame,label)
        self._equipos_frame = None
        self._equipos_lbl = None
        self._controls_frame = None
        self._table_container = None
        self._title_frame = None
        self._title_lbl = None

        # referencias a contenedores
        self._central_frame = None
        self._date_frame = None
        self._search_frame = None

        # Day picker popup
        self._day_popup = None

        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # título
        self.grid_rowconfigure(1, weight=1)  # contenido central
        self.grid_rowconfigure(2, weight=0)  # panel de pruebas

        # ---------- Título ----------
        self._title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        self._title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        self._title_frame.grid_columnconfigure(0, weight=0)
        self._title_frame.grid_columnconfigure(1, weight=1)

        self.menu_superior = MenuSuperiorDesplegable(
            self._title_frame,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
            align_mode="corner",
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=20, pady=6)

        self._title_lbl = ctk.CTkLabel(
            self._title_frame,
            text="ONT TESTER - REPORTE GLOBAL",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        self._title_lbl.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # ---------- Contenido central ----------
        self._crear_contenido_central()

        # ---------- Panel de pruebas ----------
        self.panel_pruebas = PanelPruebasConexion(self, self.modelo)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        # Aplicar tema al entrar (si existe ThemeManager en root)
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            try:
                self.apply_theme(root.theme.palette())
            except Exception:
                pass

    # =========================================================
    #                 DAY PICKER (SCROLL)
    # =========================================================
    def _open_day_picker(self):
        """Popup con scroll para seleccionar día (1-31) sin desbordar."""
        if self._day_popup is not None and self._day_popup.winfo_exists():
            self._day_popup.lift()
            return

        root = self.winfo_toplevel()

        popup = ctk.CTkToplevel(self)
        self._day_popup = popup
        popup.title("Selecciona día")
        popup.transient(root)
        popup.resizable(False, False)

        # Tamaño fijo pequeño (con scroll)
        popup.geometry("180x260")

        # Posicionar cerca del botón día
        self.update_idletasks()
        try:
            bx = self.dia_btn.winfo_rootx()
            by = self.dia_btn.winfo_rooty()
            popup.geometry(f"+{bx}+{by + 35}")
        except Exception:
            pass

        # Contenedor
        frame = ctk.CTkFrame(popup, corner_radius=10)
        frame.pack(fill="both", expand=True, padx=10, pady=10)

        lbl = ctk.CTkLabel(frame, text="Día", font=ctk.CTkFont(size=14, weight="bold"))
        lbl.pack(anchor="w", pady=(0, 6))

        scroll = ctk.CTkScrollableFrame(frame, height=180)
        scroll.pack(fill="both", expand=True)

        def pick(d):
            self.dia_var.set(str(d))
            try:
                popup.destroy()
            except Exception:
                pass

        # Colores default (si no hay theme)
        btn_fg = "#E6EEF4"
        btn_hover = "#D7E6EF"
        btn_text = "#2C3E50"

        # Si hay theme, repinta el popup con los colores del theme
        if hasattr(root, "theme"):
            try:
                p = root.theme.palette()
                btn_fg = p.get("card", "#E6EEF4")
                btn_hover = p.get("panel", "#D7E6EF")
                btn_text = p.get("text", "#2C3E50")
                frame.configure(fg_color=p.get("bg", "#E8F4F8"))
                scroll.configure(fg_color=p.get("bg", "#E8F4F8"))
                lbl.configure(text_color=btn_text)
            except Exception:
                pass

        for d in range(1, 32):
            ctk.CTkButton(
                scroll,
                text=str(d),
                height=30,
                corner_radius=8,
                fg_color=btn_fg,
                hover_color=btn_hover,
                text_color=btn_text,
                command=lambda x=d: pick(x),
            ).pack(fill="x", pady=4)

    # =========================================================
    #                 THEME (CLARO / OSCURO)
    # =========================================================
    def apply_theme(self, p: dict):
        bg = p.get("bg", "#E8F4F8")
        panel = p.get("panel", "#C8D8E4")
        header = p.get("header", p.get("ok", "#6B9080"))
        text = p.get("text", "#2C3E50")
        border = p.get("border", "#8FA3B0")
        entry_bg = p.get("entry_bg", "white")
        muted = p.get("muted", "#37474F")
        primary = p.get("primary", "#6B9080")
        primary_hover = p.get("primary_hover", "#5A7A6A")

        # 1) Repintar la vista
        self.configure(fg_color=bg)

        # 2) repintar también master y root (evita herencia rara por transparent)
        root = self.winfo_toplevel()
        try:
            root.configure(fg_color=bg)
        except Exception:
            pass
        try:
            self.master.configure(fg_color=bg)
        except Exception:
            pass

        # Header
        if self._title_frame:
            self._title_frame.configure(fg_color=header)
        if self._title_lbl:
            self._title_lbl.configure(text_color="white")

        # Menú superior
        try:
            if hasattr(self.menu_superior, "apply_theme"):
                self.menu_superior.apply_theme(p)
        except Exception:
            pass

        # Central
        if self._central_frame:
            self._central_frame.configure(fg_color=bg)

        # Frames internos
        if self._controls_frame:
            self._controls_frame.configure(fg_color=bg)
        if self._date_frame:
            self._date_frame.configure(fg_color=bg)
        if self._search_frame:
            self._search_frame.configure(fg_color=bg)

        # Equipos frame
        if self._equipos_frame:
            mode = getattr(getattr(root, "theme", None), "mode", "light")
            if mode == "dark":
                equipos_bg = p.get("panel", "#111827")
                tc = text
            else:
                equipos_bg = "#90C695"
                tc = "#2C3E50"

            self._equipos_frame.configure(fg_color=equipos_bg, border_color=border)
            if self._equipos_lbl:
                self._equipos_lbl.configure(text_color=tc)
            if self.equipos_count_label:
                self.equipos_count_label.configure(text_color=tc)

        # Controls: labels + entry + buttons
        try:
            self.search_label.configure(text_color=text)
        except Exception:
            pass

        try:
            self.search_entry.configure(
                fg_color=entry_bg,
                border_color=border,
                text_color=text,
                placeholder_text_color=muted
            )
        except Exception:
            pass

        # mes/año combobox
        for cb in (self.mes_combo, self.anio_combo):
            try:
                cb.configure(
                    fg_color=entry_bg,
                    border_color=border,
                    text_color=text,
                    button_color=primary,
                    button_hover_color=primary_hover
                )
            except Exception:
                pass

        # ✅ día: MISMO formato que combobox (campo blanco + flecha primary)
        try:
            self.dia_btn.configure(
                fg_color=entry_bg,
                hover_color=p.get("card", "#E6EEF4"),
                text_color=text,
                border_color=border
            )
        except Exception:
            pass

        try:
            self.dia_arrow.configure(
                fg_color=primary,
                hover_color=primary_hover,
                text_color="white",
                border_color=border
            )
        except Exception:
            pass

        try:
            self.btn_cargar_dia.configure(fg_color=primary, hover_color=primary_hover, text_color="white")
        except Exception:
            pass

        try:
            self.btn_cargar_global.configure(fg_color=primary, hover_color=primary_hover, text_color="white")
        except Exception:
            pass

        try:
            self.btn_excel.configure(
                fg_color=p.get("primary2", "#457B9D"),
                hover_color=p.get("primary2_hover", "#1D3557"),
                text_color="white",
            )
        except Exception:
            pass

        # Table container + scroll/table
        if self._table_container:
            self._table_container.configure(fg_color=panel, border_color=border)

        try:
            self.table_scrollable.configure(
                fg_color=panel,
                scrollbar_button_color=header,
                scrollbar_button_hover_color=p.get("primary_hover", "#3B8CC2"),
            )
        except Exception:
            pass

        try:
            self.table_frame.configure(fg_color=panel)
        except Exception:
            pass

        # Header cells + body rows
        self._repaint_table(p)

        # Panel inferior
        try:
            if hasattr(self.panel_pruebas, "apply_theme"):
                self.panel_pruebas.apply_theme(p)
        except Exception:
            pass

    def _repaint_table(self, p: dict):
        text = p.get("text", "#2C3E50")
        root = self.winfo_toplevel()
        mode = getattr(getattr(root, "theme", None), "mode", "light")

        if mode == "dark":
            row_colors = ["#0F172A", "#111827"]
            header_bg = "#1F2937"
            cell_border = "#243244"
            header_border = p.get("border", "#243244")
        else:
            row_colors = ["#F0F4F8", "#E1E8ED"]
            header_bg = "#B0C4DE"
            cell_border = "#B8C5D0"
            header_border = p.get("border", "#8FA3B0")

        for cell_frame, lbl in self._header_cells:
            try:
                cell_frame.configure(fg_color=header_bg, border_color=header_border)
            except Exception:
                pass
            try:
                lbl.configure(text_color=text)
            except Exception:
                pass

        for idx, row_info in enumerate(self.row_widgets):
            base = row_colors[idx % 2]
            for frame in row_info["frames"]:
                try:
                    frame.configure(fg_color=base, border_color=cell_border)
                except Exception:
                    pass
            row_info["original_color"] = base

    # =========================================================
    # Helpers para la tabla
    # =========================================================
    def _clear_table(self):
        for row_info in self.row_widgets:
            for frame in row_info["frames"]:
                frame.destroy()

        self.row_widgets = []
        self.table_rows = []

    def _set_table_rows(self, rows):
        self._clear_table()

        self.table_rows = rows
        body_font = ctk.CTkFont(size=10)

        root = self.winfo_toplevel()
        mode = getattr(getattr(root, "theme", None), "mode", "light")

        if mode == "dark":
            row_colors = ["#0F172A", "#111827"]
            text_color = "#E5E7EB"
            border_color = "#243244"
        else:
            row_colors = ["#F0F4F8", "#E1E8ED"]
            text_color = "#2C3E50"
            border_color = "#B8C5D0"

        for row_idx, row_data in enumerate(rows, start=1):
            row_frames = []
            row_color = row_colors[(row_idx - 1) % 2]

            for col, value in enumerate(row_data):
                cell_frame = ctk.CTkFrame(
                    self.table_frame,
                    fg_color=row_color,
                    corner_radius=0,
                    border_width=1,
                    border_color=border_color
                )
                cell_frame.grid(row=row_idx, column=col, sticky="nsew")

                label = ctk.CTkLabel(
                    cell_frame,
                    text=str(value),
                    font=body_font,
                    text_color=text_color,
                    fg_color="transparent",
                )
                label.pack(padx=4, pady=3)

                row_frames.append(cell_frame)

            self.row_widgets.append({
                "frames": row_frames,
                "data": row_data,
                "original_color": row_color
            })

        if hasattr(root, "theme"):
            try:
                self._repaint_table(root.theme.palette())
            except Exception:
                pass

    # =========================================================
    #                NAVEGACIÓN (REDIRECCIÓN)
    # =========================================================
    def _swap_view(self, view_cls):
        parent = self.master
        root = parent.winfo_toplevel()  # ✅ tomar root antes de destruir

        try:
            self.destroy()
        except Exception:
            pass

        nueva = view_cls(parent, self.modelo)
        nueva.pack(fill="both", expand=True)

        if hasattr(parent, "dispatcher") and parent.dispatcher:
            parent.dispatcher.set_target(nueva)

        if hasattr(root, "theme") and hasattr(nueva, "apply_theme"):
            try:
                nueva.apply_theme(root.theme.palette())
            except Exception:
                pass

    def ir_a_ont_tester(self):
        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView)

    def ir_a_base_diaria(self):
        from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        self._swap_view(EscaneosDiaView)

    def ir_a_base_global(self):
        pass

    def ir_a_otros(self):
        from src.Frontend.ui.propiedades_view import TesterMainView
        self._swap_view(TesterMainView)

    # =========================================================
    #                UI CENTRAL
    # =========================================================
    def _crear_contenido_central(self):
        self._central_frame = ctk.CTkFrame(self, fg_color="#E8F4F8")
        self._central_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)

        self._central_frame.grid_columnconfigure(0, weight=1)
        self._central_frame.grid_rowconfigure(0, weight=0)  # equipos en base
        self._central_frame.grid_rowconfigure(1, weight=0)  # controles fecha
        self._central_frame.grid_rowconfigure(2, weight=1)  # tabla datos

        # ---------- EQUIPOS EN BASE ----------
        self._equipos_frame = ctk.CTkFrame(
            self._central_frame,
            fg_color="#90C695",
            corner_radius=8,
            border_width=2,
            border_color="#6B9080"
        )
        self._equipos_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self._equipos_lbl = ctk.CTkLabel(
            self._equipos_frame,
            text="EQUIPOS EN BASE:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        )
        self._equipos_lbl.pack(side="left", padx=20, pady=10)

        self.equipos_count_label = ctk.CTkLabel(
            self._equipos_frame,
            text="",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#2C3E50"
        )
        self.equipos_count_label.pack(side="left", padx=(0, 20), pady=10)

        # ---------- Controles ----------
        self._controls_frame = ctk.CTkFrame(self._central_frame, fg_color="#E8F4F8")
        self._controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        self._controls_frame.grid_columnconfigure(0, weight=0)
        self._controls_frame.grid_columnconfigure(1, weight=0)
        self._controls_frame.grid_columnconfigure(2, weight=0)
        self._controls_frame.grid_columnconfigure(3, weight=1)
        self._controls_frame.grid_columnconfigure(4, weight=0)
        self._controls_frame.grid_columnconfigure(5, weight=0)

        # Selectores de fecha
        self._date_frame = ctk.CTkFrame(self._controls_frame, fg_color="#E8F4F8")
        self._date_frame.grid(row=0, column=0, sticky="w", padx=(0, 20))

        ctk.CTkLabel(self._date_frame, text="día", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=5)

        # ✅ Día (look igual a ComboBox)
        self.dia_var = ctk.StringVar(value="22")

        # "campo" blanco como el combobox
        self.dia_btn = ctk.CTkButton(
            self._date_frame,
            textvariable=self.dia_var,
            width=90,
            height=32,
            corner_radius=6,
            fg_color="white",
            hover_color="#E6EEF4",
            text_color="#2C3E50",
            border_width=1,
            border_color="#8FA3B0",
            anchor="w",
            command=self._open_day_picker,
        )
        self.dia_btn.grid(row=1, column=0, padx=5)

        # flecha azul (igual al botón del combobox)
        self.dia_arrow = ctk.CTkButton(
            self._date_frame,
            text="▾",
            width=28,
            height=32,
            corner_radius=6,
            fg_color="#4EA5D9",
            hover_color="#3B8CC2",
            text_color="white",
            command=self._open_day_picker,
        )
        self.dia_arrow.grid(row=1, column=0, padx=5, sticky="e")

        ctk.CTkLabel(self._date_frame, text="mes", font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=5)
        self.mes_combo = ctk.CTkComboBox(
            self._date_frame,
            values=[str(i) for i in range(1, 13)],
            width=70,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.mes_combo.set("10")
        self.mes_combo.grid(row=1, column=1, padx=5)

        ctk.CTkLabel(self._date_frame, text="año", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=5)
        self.anio_combo = ctk.CTkComboBox(
            self._date_frame,
            values=["2024", "2025", "2026"],
            width=90,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.anio_combo.set("2025")
        self.anio_combo.grid(row=1, column=2, padx=5)

        # Botón CARGAR BASE DEL DÍA
        self.btn_cargar_dia = ctk.CTkButton(
            self._controls_frame,
            text="CARGAR BASE DEL DÍA",
            command=self.cargar_base_dia,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            height=40,
            width=200
        )
        self.btn_cargar_dia.grid(row=0, column=1, padx=10)

        # Búsqueda
        self._search_frame = ctk.CTkFrame(self._controls_frame, fg_color="#E8F4F8")
        self._search_frame.grid(row=0, column=2, padx=10)

        self.search_label = ctk.CTkLabel(
            self._search_frame,
            text="BUSCAR SERIE",
            font=ctk.CTkFont(size=11, weight="bold")
        )
        self.search_label.pack(anchor="w")

        self.search_entry = ctk.CTkEntry(
            self._search_frame,
            placeholder_text="Ingrese serie...",
            width=200,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.search_entry.pack()
        self.search_entry.bind("<KeyRelease>", self.buscar_serie)

        # Botón CARGAR BASE GLOBAL
        self.btn_cargar_global = ctk.CTkButton(
            self._controls_frame,
            text="CARGAR BASE GLOBAL",
            command=self.cargar_base_global,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            height=40,
            width=200
        )
        self.btn_cargar_global.grid(row=0, column=4, padx=10)

        # Botón Generar Excel
        self.btn_excel = ctk.CTkButton(
            self._controls_frame,
            text="Generar Excel",
            command=self.generar_excel,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#457B9D",
            hover_color="#1D3557",
            height=40,
            width=150
        )
        self.btn_excel.grid(row=0, column=5, padx=(10, 0))

        # ---------- Tabla ----------
        self._table_container = ctk.CTkFrame(
            self._central_frame,
            fg_color="#C8D8E4",
            corner_radius=8,
            border_width=2,
            border_color="#8FA3B0"
        )
        self._table_container.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        self._table_container.grid_rowconfigure(0, weight=1)
        self._table_container.grid_columnconfigure(0, weight=1)

        self.table_scrollable = ctk.CTkScrollableFrame(
            self._table_container,
            fg_color="#C8D8E4",
            corner_radius=0,
            scrollbar_button_color="#6B9080",
            scrollbar_button_hover_color="#5A7A6A",
        )
        self.table_scrollable.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        self.table_frame = ctk.CTkFrame(self.table_scrollable, fg_color="#C8D8E4")
        self.table_frame.pack(fill="both", expand=True)

        for col in range(len(self._headers)):
            self.table_frame.grid_columnconfigure(col, weight=1, minsize=100)

        header_font = ctk.CTkFont(size=11, weight="bold")
        for col, title in enumerate(self._headers):
            header_cell = ctk.CTkFrame(
                self.table_frame,
                fg_color="#B0C4DE",
                corner_radius=0,
                border_width=1,
                border_color="#8FA3B0"
            )
            header_cell.grid(row=0, column=col, sticky="nsew")

            label = ctk.CTkLabel(
                header_cell,
                text=title,
                font=header_font,
                text_color="#2C3E50",
                fg_color="transparent",
                justify="center"
            )
            label.pack(padx=4, pady=5)

            self._header_cells.append((header_cell, label))

        # Carga inicial
        self.cargar_base_global()

    # =========================================================
    #                 ACCIONES / DATA
    # =========================================================
    def buscar_serie(self, event=None):
        search_text = self.search_entry.get().strip().upper()

        # Reset a color base
        for row_info in self.row_widgets:
            for frame in row_info["frames"]:
                frame.configure(fg_color=row_info["original_color"])

        if not search_text:
            return

        root = self.winfo_toplevel()
        mode = getattr(getattr(root, "theme", None), "mode", "light")

        if mode == "light":
            highlight = "#FFE066"
        else:
            try:
                highlight = root.theme.palette().get("primary_hover", "#3B82F6")
            except Exception:
                highlight = "#3B82F6"

        for row_info in self.row_widgets:
            serie = str(row_info["data"][1]).upper()  # SERIE índice 1
            if search_text in serie:
                for frame in row_info["frames"]:
                    frame.configure(fg_color=highlight)

    def cargar_base_dia(self):
        """Carga la base de datos del día seleccionado."""
        dia = int(self.dia_var.get())
        mes = int(self.mes_combo.get())
        anio = int(self.anio_combo.get())

        d = date(anio, mes, dia)
        day = d.isoformat()

        from src.backend.sua_client.dao import get_baseGlobal_por_dia
        data = get_baseGlobal_por_dia(day)

        if not data:
            self._set_table_rows([])
            self.equipos_count_label.configure(text="0")
            return

        rows = []
        for r in data:
            status = "PASS" if int(r.get("valido") or 0) == 1 else "FAIL"
            fila = [
                r.get("id"),
                r.get("sn"),
                r.get("mac"),
                r.get("version_inicial") or "",
                r.get("version_final") or "",
                r.get("modelo") or "",
                r.get("fecha_test") or "",
                r.get("version_ont_tester") or "",
                r.get("ssid_24") or "",
                r.get("ssid_5") or "",
                r.get("password") or "",
                status,
            ]
            rows.append(fila)

        self._set_table_rows(rows)
        self.equipos_count_label.configure(text=str(len(rows)))

        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            try:
                self.apply_theme(root.theme.palette())
            except Exception:
                pass

    def cargar_base_global(self):
        """Carga la base de datos global."""
        from src.backend.sua_client.dao import get_baseGlobal_view
        data = get_baseGlobal_view()

        if not data:
            self._set_table_rows([])
            self.equipos_count_label.configure(text="0")
            return

        rows = []
        for r in data:
            status = "PASS" if int(r.get("valido") or 0) == 1 else "FAIL"
            fila = [
                r.get("id"),
                r.get("sn"),
                r.get("mac"),
                r.get("version_inicial") or "",
                r.get("version_final") or "",
                r.get("modelo") or "",
                r.get("fecha_test") or "",
                r.get("version_ont_tester") or "",
                r.get("ssid_24") or "",
                r.get("ssid_5") or "",
                r.get("password") or "",
                status,
            ]
            rows.append(fila)

        self._set_table_rows(rows)
        self.equipos_count_label.configure(text=str(len(rows)))

        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            try:
                self.apply_theme(root.theme.palette())
            except Exception:
                pass

    def generar_excel(self):
        print("Generando Excel...")
        if self.viewmodel:
            pass


# Test de la vista
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER - Reporte Global")
    app.geometry("1400x900")

    view = ReporteGlobalView(app, modelo=None)
    view.pack(fill="both", expand=True)

    app.mainloop()
