# src/Frontend/ui/escaneos_dia_view.py
import customtkinter as ctk
import sys
from pathlib import Path
from tkinter import messagebox
import traceback

root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion
from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable



class EscaneosDiaView(ctk.CTkFrame):
    """
    Vista para 'Escaneos del día'
    """

    def __init__(self, parent, modelo=None, viewmodel=None, **kwargs):
        # transparente para que el theme pinte
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.viewmodel = viewmodel
        self.modelo = modelo
        app = self.winfo_toplevel()
        self.q = getattr(app, "event_q", None)

        self.tooltip_window = None
        self.tooltip_job = None

        self.headers = ["ID", "SNN", "MAC", "SSID", "SSID-5G", "PASSWORD", "STATUS", "PRUEBA", "MODELO", "FECHA"]

        self.detail_label_texts = {
            "ID": "ID:",
            "SNN": "SERIE:",
            "MAC": "MAC:",
            "SSID": "SSID:",
            "SSID-5G": "SSID 5G:",
            "PASSWORD": "PASSWORD:",
            "STATUS": "STATUS:",
            "PRUEBA": "PRUEBA:",
            "MODELO": "MODELO:",
            "FECHA": "FECHA:",
        }

        self.table_rows_data = []
        self.all_rows = []
        self.detail_vars = {}
        self.row_label_widgets = []
        self.highlighted_row = None

        # Paleta actual
        self._palette = {}

        # Layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        # ---------- Título ----------
        self.title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        self.title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)
        self.title_frame.grid_columnconfigure(0, weight=0)
        self.title_frame.grid_columnconfigure(1, weight=1)

        self.menu_superior = MenuSuperiorDesplegable(
            self.title_frame,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
            align_mode="corner",
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=20, pady=6)

        self.titulo_lbl = ctk.CTkLabel(
            self.title_frame,
            text="ONT TESTER - VENTANA ESCANEOS DEL DÍA",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        self.titulo_lbl.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # ---------- Contenido ----------
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=7)
        self.content_frame.grid_columnconfigure(1, weight=3)

        # Tabla container
        self.table_container = ctk.CTkFrame(
            self.content_frame,
            fg_color="#C8D8E4",
            corner_radius=8,
            border_width=2,
            border_color="#8FA3B0"
        )
        self.table_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=1)

        self.table_scrollable = ctk.CTkScrollableFrame(
            self.table_container,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#6B9080",
            scrollbar_button_hover_color="#5A7A6A",
        )
        self.table_scrollable.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        self.table_frame = ctk.CTkFrame(self.table_scrollable, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True)

        for col in range(len(self.headers)):
            self.table_frame.grid_columnconfigure(col, weight=1, minsize=80)

        # Encabezados
        self._header_cells = []
        self._header_labels = []
        header_font = ctk.CTkFont(size=11, weight="bold")
        for col, title in enumerate(self.headers):
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
            self._header_cells.append(header_cell)
            self._header_labels.append(label)

        # Panel derecho container
        self.detail_container = ctk.CTkFrame(
            self.content_frame,
            fg_color="#C8D8E4",
            corner_radius=8,
            border_width=2,
            border_color="#8FA3B0"
        )
        self.detail_container.grid(row=0, column=1, sticky="nsew")
        self.detail_container.grid_rowconfigure(0, weight=1)
        self.detail_container.grid_columnconfigure(0, weight=1)

        self.detail_scrollable = ctk.CTkScrollableFrame(
            self.detail_container,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#6B9080",
            scrollbar_button_hover_color="#5A7A6A",
        )
        self.detail_scrollable.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        self.detail_frame = ctk.CTkFrame(self.detail_scrollable, fg_color="transparent")
        self.detail_frame.pack(fill="x", expand=False, padx=10, pady=10)


        detail_font_label = ctk.CTkFont(size=11, weight="bold")
        detail_font_value = ctk.CTkFont(size=11)

        self.buscar_lbl = ctk.CTkLabel(
            self.detail_frame,
            text="BUSCAR SERIE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        )
        self.buscar_lbl.pack(pady=(0, 5))

        self.search_var = ctk.StringVar(value="")
        self.search_entry = ctk.CTkEntry(
            self.detail_frame,
            textvariable=self.search_var,
            font=detail_font_value,
            height=32,
            fg_color="white",
            border_color="#8FA3B0",
            border_width=2,
        )
        self.search_entry.pack(fill="x", pady=(0, 3))
        self.search_entry.bind("<Return>", self.search_by_sn)

        self.detail_status_var = ctk.StringVar(value="")
        self.status_lbl = ctk.CTkLabel(
            self.detail_frame,
            textvariable=self.detail_status_var,
            font=ctk.CTkFont(size=10),
            text_color="#C0392B",
        )
        self.status_lbl.pack(pady=(0, 8))

        self._detail_label_widgets = []
        self._detail_entry_widgets = []

        for key in self.headers:
            label_text = self.detail_label_texts.get(key, key)

            row_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
            row_frame.pack(fill="x", pady=2)

            row_frame.grid_columnconfigure(0, weight=0)
            row_frame.grid_columnconfigure(1, weight=1)

            lbl = ctk.CTkLabel(
                row_frame,
                text=label_text,
                font=detail_font_label,
                text_color="#2C3E50",
                anchor="w",
                width=90
            )
            lbl.grid(row=0, column=0, sticky="w", padx=(0, 5))

            var = ctk.StringVar(value="")
            self.detail_vars[key] = var

            entry = ctk.CTkEntry(
                row_frame,
                textvariable=var,
                font=detail_font_value,
                height=28,
                state="readonly",
                fg_color="white",
                border_color="#8FA3B0",
                border_width=1,
            )
            entry.grid(row=0, column=1, sticky="ew")

            self._detail_label_widgets.append(lbl)
            self._detail_entry_widgets.append(entry)

                # Botones (SOLO UNA VEZ, sin duplicar el frame)
        self.buttons_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        # baja un poco el espacio entre formulario y botones
        self.buttons_frame.pack(fill="x", pady=(6, 0))

        # ----- IMPRIMIR -----
        self.btn_imprimir_frame = ctk.CTkFrame(
            self.buttons_frame,
            fg_color="#A8DADC",
            corner_radius=8,
            border_width=2,
            border_color="#457B9D"
        )
        self.btn_imprimir_frame.pack(fill="x", pady=(0, 10))

        self.icon_print = ctk.CTkLabel(
            self.btn_imprimir_frame,
            text="🖨️",
            font=ctk.CTkFont(size=24)
        )
        self.icon_print.pack(pady=(8, 3))

        self.btn_imprimir = ctk.CTkButton(
            self.btn_imprimir_frame,
            text="IMPRIMIR ETIQUETA",
            command=self.on_imprimir_etiqueta,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#457B9D",
            hover_color="#1D3557",
            height=35
        )
        self.btn_imprimir.pack(fill="x", padx=10, pady=(0, 8))

        # ----- BORRAR -----
        self.btn_borrar_frame = ctk.CTkFrame(
            self.buttons_frame,
            fg_color="#F1B4BB",
            corner_radius=8,
            border_width=2,
            border_color="#C1666B"
        )
        self.btn_borrar_frame.pack(fill="x")

        self.icon_delete = ctk.CTkLabel(
            self.btn_borrar_frame,
            text="🗑️",
            font=ctk.CTkFont(size=24)
        )
        self.icon_delete.pack(pady=(8, 3))

        self.btn_borrar = ctk.CTkButton(
            self.btn_borrar_frame,
            text="BORRAR",
            command=self.on_borrar_registro,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            height=35
        )
        self.btn_borrar.pack(fill="x", padx=10, pady=(0, 8))



        # Panel de pruebas fijo
        self.panel_pruebas = PanelPruebasConexion(self, self.modelo)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        # Cargar registros
        self.load_daily_records()

        # Aplicar tema (si existe)
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            try:
                self.apply_theme(root.theme.palette())
            except Exception:
                pass

    # ------------------------------------------------------------
    # Helpers: modo real
    # ------------------------------------------------------------
    def _current_mode(self) -> str:
        try:
            return "dark" if ctk.get_appearance_mode().lower() == "dark" else "light"
        except Exception:
            return "light"

    # ------------------------------------------------------------
    # THEME (armónico + consistente)
    # ------------------------------------------------------------
    def apply_theme(self, p: dict):
        """
        Armoniza colores en dark y arregla el regreso a light.
        Usa el modo REAL de CustomTkinter.
        """
        self._palette = dict(p or {})
        mode = self._current_mode()

        if mode == "dark":
            bg = p.get("bg_dark", p.get("bg", "#0B1220"))
            panel = p.get("panel_dark", p.get("panel", "#0F172A"))
            card = p.get("card_dark", p.get("card", "#111827"))
            border = p.get("border_dark", p.get("border", "#243244"))
            text = p.get("text_dark", p.get("text", "#E5E7EB"))
            primary = p.get("primary_dark", p.get("primary", "#60A5FA"))
            primary_hover = p.get("primary_hover_dark", p.get("primary_hover", "#3B82F6"))
            err = p.get("error_dark", p.get("error", "#F87171"))
            topbar = p.get("topbar_dark", p.get("topbar", "#111827"))
            header_cell_bg = p.get("header_cell_dark", card)
            entry_bg = p.get("entry_bg_dark", "#0B1220")
            entry_border = p.get("entry_border_dark", border)
        else:
            bg = p.get("bg_light", p.get("bg", "#E8F4F8"))
            panel = p.get("panel_light", p.get("panel", "#D2E3EC"))
            card = p.get("card_light", p.get("card", "#FFFFFF"))
            border = p.get("border_light", p.get("border", "#8FA3B0"))
            text = p.get("text_light", p.get("text", "#0F172A"))
            primary = p.get("primary_light", p.get("primary", "#4EA5D9"))
            primary_hover = p.get("primary_hover_light", p.get("primary_hover", "#3B8CC2"))
            err = p.get("error_light", p.get("error", "#C1666B"))
            topbar = p.get("topbar_light", p.get("topbar", primary))
            header_cell_bg = p.get("header_cell_light", card)
            entry_bg = p.get("entry_bg_light", "#FFFFFF")
            entry_border = p.get("entry_border_light", border)

        # Fondo general
        self.configure(fg_color=bg)

        # Topbar
        self.title_frame.configure(fg_color=topbar)
        self.titulo_lbl.configure(text_color="white")

        # Scrollbars
        try:
            self.table_scrollable.configure(
                scrollbar_button_color=primary,
                scrollbar_button_hover_color=primary_hover
            )
        except Exception:
            pass
        try:
            self.detail_scrollable.configure(
                scrollbar_button_color=primary,
                scrollbar_button_hover_color=primary_hover
            )
        except Exception:
            pass

        # Containers
        self.content_frame.configure(fg_color="transparent")
        self.table_container.configure(fg_color=panel, border_color=border)
        self.detail_container.configure(fg_color=panel, border_color=border)

        # Evita “manchas” al cambiar de modo
        try:
            self.table_scrollable.configure(fg_color="transparent")
            self.detail_scrollable.configure(fg_color="transparent")
            self.table_frame.configure(fg_color="transparent")
            self.detail_frame.configure(fg_color="transparent")
        except Exception:
            pass

        # Headers tabla
        for cell, lbl in zip(self._header_cells, self._header_labels):
            cell.configure(fg_color=header_cell_bg, border_color=border)
            lbl.configure(text_color=text)

        # Panel derecho
        self.buscar_lbl.configure(text_color=text)
        self.status_lbl.configure(text_color=err)

        self.search_entry.configure(fg_color=entry_bg, border_color=entry_border, text_color=text)

        for lbl in self._detail_label_widgets:
            lbl.configure(text_color=text)
        for ent in self._detail_entry_widgets:
            ent.configure(fg_color=entry_bg, border_color=entry_border, text_color=text)

        # Botones
        try:
            self.btn_imprimir.configure(fg_color=primary, hover_color=primary_hover, text_color="white")
        except Exception:
            pass
        try:
            self.btn_borrar.configure(fg_color=err, hover_color=err, text_color="white")
        except Exception:
            pass

        # Menú superior
        if hasattr(self.menu_superior, "apply_theme"):
            try:
                self.menu_superior.apply_theme(p)
            except Exception:
                pass

        # Panel pruebas
        if hasattr(self.panel_pruebas, "apply_theme"):
            try:
                self.panel_pruebas.apply_theme(p)
            except Exception:
                pass

        # ✅ Refrescar filas para que cambie tabla/celdas al modo correcto
        self.set_table_rows(self.all_rows)

        # ---- Tarjetas de botones (imprimir / borrar)
        if hasattr(self, "btn_imprimir_frame"):
            self.btn_imprimir_frame.configure(fg_color=card, border_color=border)
        if hasattr(self, "btn_borrar_frame"):
            self.btn_borrar_frame.configure(fg_color=card, border_color=border)

        # ---- Botones
        if hasattr(self, "btn_imprimir"):
            self.btn_imprimir.configure(fg_color=primary, hover_color=primary_hover, text_color="white")
        if hasattr(self, "btn_borrar"):
            self.btn_borrar.configure(fg_color=err, hover_color=err, text_color="white")

        # ---- Íconos (si quieres que no se vean apagados en dark)
        if hasattr(self, "icon_print"):
            self.icon_print.configure(text_color=text)
        if hasattr(self, "icon_delete"):
            self.icon_delete.configure(text_color=text)


    # ------------------------------------------------------------
    # Data
    # ------------------------------------------------------------
    def load_daily_records(self):
        try:
            from datetime import datetime
            from src.backend.sua_client.dao import get_baseDiaria_view

            day = datetime.now().astimezone().date().isoformat()
            registros = get_baseDiaria_view(day)

            if not registros:
                self.set_table_rows([])
                self.detail_status_var.set("No hay registros para el día de hoy.")
                return

            rows = []
            for r in registros:
                status = "PASS" if int(r.get("valido") or 0) == 1 else "FAIL"
                fila = [
                    r.get("id"),
                    r.get("sn"),
                    r.get("mac"),
                    r.get("wifi24") or "",
                    r.get("wifi5") or "",
                    r.get("passWifi") or "",
                    status,
                    r.get("tipo") or "",
                    r.get("modelo") or "",
                    r.get("fecha_test") or "",
                ]
                rows.append(fila)

            self.set_table_rows(rows)
            self.detail_status_var.set(f"{len(rows)} registros cargados.")

        except Exception as e:
            self.set_table_rows([])
            self.detail_status_var.set(f"Error cargando base diaria: {e}")
            print("ERROR load_daily_records():\n", traceback.format_exc())

    # ------------------------------------------------------------
    # Navegación
    # ------------------------------------------------------------
    def _swap_view(self, view_cls):
        parent = self.master
        root = self.winfo_toplevel()

        try:
            self.destroy()
        except Exception:
            pass

        nueva = view_cls(parent, self.modelo)
        nueva.pack(fill="both", expand=True)

        if hasattr(parent, "dispatcher"):
            try:
                parent.dispatcher.set_target(nueva)
            except Exception:
                pass

        if hasattr(root, "theme") and hasattr(nueva, "apply_theme"):
            try:
                nueva.apply_theme(root.theme.palette())
            except Exception:
                pass

    def ir_a_ont_tester(self):
        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView)

    def ir_a_base_diaria(self):
        self.load_daily_records()

    def ir_a_base_global(self):
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        from src.Frontend.ui.propiedades_view import TesterMainView
        self._swap_view(TesterMainView)

    # ------------------------------------------------------------
    # Tabla
    # ------------------------------------------------------------
    def set_table_rows(self, rows):
        self.all_rows = list(rows)
        self.table_rows_data = self.all_rows

        # limpia celdas (no headers)
        for widget in self.table_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()

        self.row_label_widgets = []
        body_font = ctk.CTkFont(size=10)

        mode = self._current_mode()
        p = self._palette or {}

        if mode == "dark":
            row_colors = [
                p.get("panel_dark", p.get("panel", "#0F172A")),
                p.get("card_dark", p.get("card", "#111827")),
            ]
            txt = p.get("text_dark", p.get("text", "#E5E7EB"))
            border = p.get("border_dark", p.get("border", "#243244"))
            highlight_bg = p.get("primary_dark", p.get("primary", "#60A5FA"))
            highlight_border = p.get("primary_hover_dark", p.get("primary_hover", "#3B82F6"))
            highlight_txt = "white"
        else:
            # light armónico (para que no deslumbre, pero nunca negro)
            row_colors = ["#F8FAFC", "#EEF2F7"]
            txt = "#0F172A"
            border = "#CBD5E1"
            highlight_bg = p.get("primary_light", p.get("primary", "#4EA5D9"))
            highlight_border = p.get("primary_hover_light", p.get("primary_hover", "#3B8CC2"))
            highlight_txt = "white"

        self._row_style = {
            "row_colors": row_colors,
            "txt": txt,
            "border": border,
            "highlight_bg": highlight_bg,
            "highlight_border": highlight_border,
            "highlight_txt": highlight_txt,
        }

        for r_idx, row in enumerate(self.table_rows_data, start=1):
            row_widgets = []
            row_color = row_colors[(r_idx - 1) % 2]

            for c_idx, value in enumerate(row):
                cell_frame = ctk.CTkFrame(
                    self.table_frame,
                    fg_color=row_color,
                    corner_radius=0,
                    border_width=1,
                    border_color=border
                )
                cell_frame.grid(row=r_idx, column=c_idx, sticky="nsew")

                display_text = str(value)
                if len(display_text) > 15:
                    display_text = display_text[:12] + "..."

                label = ctk.CTkLabel(
                    cell_frame,
                    text=display_text,
                    font=body_font,
                    text_color=txt,
                    fg_color="transparent",
                )
                label.pack(padx=4, pady=3)

                cell_frame.bind("<Button-1>", lambda e, idx=r_idx - 1: self.on_row_click(idx))
                label.bind("<Button-1>", lambda e, idx=r_idx - 1: self.on_row_click(idx))

                full_text = str(value)
                self._bind_tooltip(label, full_text)
                self._bind_tooltip(cell_frame, full_text)

                row_widgets.append((cell_frame, label))

            self.row_label_widgets.append(row_widgets)

        self._clear_highlight()

    def on_row_click(self, row_index: int):
        if not (0 <= row_index < len(self.table_rows_data)):
            return

        row = self.table_rows_data[row_index]
        for col_index, key in enumerate(self.headers):
            self.detail_vars[key].set(str(row[col_index]) if col_index < len(row) else "")

        self._highlight_row(row_index)
        self.detail_status_var.set("")

    def _clear_highlight(self):
        if self.highlighted_row is None:
            return
        if 0 <= self.highlighted_row < len(self.row_label_widgets):
            st = getattr(self, "_row_style", None) or {}
            row_colors = st.get("row_colors", ["#F8FAFC", "#EEF2F7"])
            border = st.get("border", "#CBD5E1")
            txt = st.get("txt", "#0F172A")

            row_color = row_colors[self.highlighted_row % 2]
            for cell_frame, label in self.row_label_widgets[self.highlighted_row]:
                cell_frame.configure(fg_color=row_color, border_color=border)
                label.configure(text_color=txt)
        self.highlighted_row = None

    def _highlight_row(self, index):
        self._clear_highlight()
        if not (0 <= index < len(self.row_label_widgets)):
            return

        st = getattr(self, "_row_style", None) or {}
        bg = st.get("highlight_bg", "#4EA5D9")
        border = st.get("highlight_border", "#3B8CC2")
        txt = st.get("highlight_txt", "white")

        for cell_frame, label in self.row_label_widgets[index]:
            cell_frame.configure(fg_color=bg, border_color=border)
            label.configure(text_color=txt)
        self.highlighted_row = index

    # ------------------------------------------------------------
    # Buscar / Acciones
    # ------------------------------------------------------------
    def search_by_sn(self, event=None):
        query = self.search_var.get().strip()
        if not query:
            self.detail_status_var.set("")
            self._clear_highlight()
            return

        found_index = None
        for i, row in enumerate(self.all_rows):
            if len(row) > 1 and query.lower() in str(row[1]).lower():
                found_index = i
                break

        if found_index is None:
            self.detail_status_var.set("No se encontraron resultados.")
            self._clear_highlight()
            return

        self.on_row_click(found_index)
        self.detail_status_var.set("")

    def on_imprimir_etiqueta(self):
        if self.highlighted_row is None:
            self.detail_status_var.set("Selecciona un registro para imprimir.")
            return
        row_data = self.table_rows_data[self.highlighted_row]
        print(f"Imprimiendo etiqueta: {row_data}")
        self.detail_status_var.set("Etiqueta enviada a impresión.")

    def on_borrar_registro(self):
        if self.highlighted_row is None:
            self.detail_status_var.set("Selecciona un registro para borrar.")
            return

        row_data = self.table_rows_data[self.highlighted_row]
        respuesta = messagebox.askyesno(
            "Confirmar borrado",
            f"¿Borrar registro?\n\nID: {row_data[0]}\nSNN: {row_data[1]}\nMAC: {row_data[2]}",
            icon="warning",
        )
        if not respuesta:
            return

        try:
            index_to_remove = self.highlighted_row
            self.all_rows.pop(index_to_remove)

            for key in self.detail_vars:
                self.detail_vars[key].set("")

            self.set_table_rows(self.all_rows)
            self.detail_status_var.set("Registro borrado exitosamente.")
        except Exception as e:
            self.detail_status_var.set(f"Error al borrar: {str(e)}")
            messagebox.showerror("Error", f"No se pudo borrar:\n{str(e)}")

    # ------------------------------------------------------------
    # Tooltips
    # ------------------------------------------------------------
    def _bind_tooltip(self, widget, text):
        widget.bind("<Enter>", lambda e: self._show_tooltip(e, text))
        widget.bind("<Leave>", lambda e: self._hide_tooltip())
        widget.bind("<Button-1>", lambda e: self._hide_tooltip())

    def _show_tooltip(self, event, text):
        if self.tooltip_job:
            self.after_cancel(self.tooltip_job)
        self.tooltip_job = self.after(300, lambda: self._create_tooltip(event, text))

    def _create_tooltip(self, event, text):
        if self.tooltip_window:
            return

        x = event.widget.winfo_pointerx() + 10
        y = event.widget.winfo_pointery() + 10

        self.tooltip_window = ctk.CTkToplevel(self)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")

        p = self._palette or {}
        mode = self._current_mode()

        if mode == "dark":
            bg = p.get("card_dark", p.get("card", "#111827"))
            border = p.get("border_dark", p.get("border", "#243244"))
            txt = p.get("text_dark", p.get("text", "#E5E7EB"))
        else:
            bg = p.get("card_light", p.get("card", "#FFFFFF"))
            border = p.get("border_light", p.get("border", "#CBD5E1"))
            txt = p.get("text_light", p.get("text", "#0F172A"))

        tooltip_frame = ctk.CTkFrame(
            self.tooltip_window,
            fg_color=bg,
            corner_radius=6,
            border_width=1,
            border_color=border,
        )
        tooltip_frame.pack(padx=2, pady=2)

        label = ctk.CTkLabel(
            tooltip_frame,
            text=text,
            font=ctk.CTkFont(size=11),
            text_color=txt,
            fg_color="transparent",
        )
        label.pack(padx=8, pady=6)

    def _hide_tooltip(self):
        if self.tooltip_job:
            self.after_cancel(self.tooltip_job)
            self.tooltip_job = None
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER")
    app.geometry("1400x800")

    view = EscaneosDiaView(app)
    view.pack(fill="both", expand=True)
    app.mainloop()
