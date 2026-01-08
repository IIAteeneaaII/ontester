import customtkinter as ctk
import sys
import csv
from pathlib import Path
from tkinter import messagebox

# Para poder usar imports absolutos (igual que en tester_view)
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion
from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable
from src.Frontend.navigation.botones import boton_imprimir_etiqueta, boton_borrar


class EscaneosDiaView(ctk.CTkFrame):
    """
    Vista para 'Escaneos del día' - Estilo mejorado compacto con campos en línea.
    """

    def __init__(self, parent, modelo, q, viewmodel=None, **kwargs):
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)

        self.viewmodel = viewmodel
        self.modelo = modelo
        self.q = q
        # Para los tooltips
        self.tooltip_window = None
        self.tooltip_job = None

        # Datos de configuración de la tabla
        self.headers = [
            "ID",
            "SNN",
            "MAC",
            "SSID",
            "SSID-5G",
            "PASSWORD",
            "STATUS",
            "PRUEBA",
            "MODELO",
            "FECHA",
        ]

        # Mapeo para el panel derecho
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

        # Widgets por fila
        self.row_label_widgets = []
        self.highlighted_row = None

        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # título
        self.grid_rowconfigure(1, weight=1)  # contenido principal
        self.grid_rowconfigure(2, weight=0)  # panel de pruebas fijo

        # ---------- Título verde ----------
        title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        # Para poner menú a la izquierda y título al lado
        title_frame.grid_columnconfigure(0, weight=0)  # menú
        title_frame.grid_columnconfigure(1, weight=1)  # título

        # Menú desplegable (callbacks reales de navegación)
        self.menu_superior = MenuSuperiorDesplegable(
            title_frame,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=20, pady=6)

        titulo = ctk.CTkLabel(
            title_frame,
            text="ONT TESTER - VENTANA ESCANEOS DEL DÍA",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        titulo.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # ---------- Contenedor tabla + panel derecho ----------
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)

        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=7)  # tabla más ancha
        self.content_frame.grid_columnconfigure(1, weight=3)  # panel detalle

        # ---------- Tabla con scrollbar ----------
        table_container = ctk.CTkFrame(
            self.content_frame,
            fg_color="#C8D8E4",
            corner_radius=8,
            border_width=2,
            border_color="#8FA3B0"
        )
        table_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        # Scrollable frame para la tabla con mejor rendimiento
        self.table_scrollable = ctk.CTkScrollableFrame(
            table_container,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#6B9080",
            scrollbar_button_hover_color="#5A7A6A",
        )
        self.table_scrollable.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        # Configuración mejorada del scroll para evitar trabas
        try:
            self.table_scrollable._parent_canvas.configure(
                yscrollincrement=10,
                scrollregion=(0, 0, 0, 1000)
            )
        except Exception:
            pass

        # Frame para la tabla
        self.table_frame = ctk.CTkFrame(self.table_scrollable, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True)

        # Configurar columnas
        for col in range(len(self.headers)):
            self.table_frame.grid_columnconfigure(col, weight=1, minsize=80)

        # Encabezados
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

        # ---------- Panel derecho ----------
        detail_container = ctk.CTkFrame(
            self.content_frame,
            fg_color="#C8D8E4",
            corner_radius=8,
            border_width=2,
            border_color="#8FA3B0"
        )
        detail_container.grid(row=0, column=1, sticky="nsew")
        detail_container.grid_rowconfigure(0, weight=1)
        detail_container.grid_columnconfigure(0, weight=1)

        # Scrollable frame para detalles con mejor rendimiento
        self.detail_scrollable = ctk.CTkScrollableFrame(
            detail_container,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#6B9080",
            scrollbar_button_hover_color="#5A7A6A",
        )
        self.detail_scrollable.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        try:
            self.detail_scrollable._parent_canvas.configure(
                yscrollincrement=8,
                scrollregion=(0, 0, 0, 1000)
            )
        except Exception:
            pass

        self.detail_frame = ctk.CTkFrame(self.detail_scrollable, fg_color="transparent")
        self.detail_frame.pack(fill="both", expand=True, padx=10, pady=10)

        detail_font_label = ctk.CTkFont(size=11, weight="bold")
        detail_font_value = ctk.CTkFont(size=11)

        # Campo de búsqueda
        ctk.CTkLabel(
            self.detail_frame,
            text="BUSCAR SERIE",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        ).pack(pady=(0, 5))

        self.search_var = ctk.StringVar(value="")
        search_entry = ctk.CTkEntry(
            self.detail_frame,
            textvariable=self.search_var,
            font=detail_font_value,
            height=32,
            fg_color="white",
            border_color="#8FA3B0",
            border_width=2,
        )
        search_entry.pack(fill="x", pady=(0, 3))
        search_entry.bind("<Return>", self.search_by_sn)

        # Mensaje de estado
        self.detail_status_var = ctk.StringVar(value="")
        status_lbl = ctk.CTkLabel(
            self.detail_frame,
            textvariable=self.detail_status_var,
            font=ctk.CTkFont(size=10),
            text_color="#C0392B",
        )
        status_lbl.pack(pady=(0, 8))

        # Campos de detalle en línea
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

        # ---------- Botones ----------
        buttons_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", pady=(10, 5))

        # Botón IMPRIMIR
        btn_imprimir_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#A8DADC",
            corner_radius=8,
            border_width=2,
            border_color="#457B9D"
        )
        btn_imprimir_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(btn_imprimir_frame, text="🖨️", font=ctk.CTkFont(size=24)).pack(pady=(8, 3))

        self.btn_imprimir = ctk.CTkButton(
            btn_imprimir_frame,
            text="IMPRIMIR ETIQUETA",
            command=self.on_imprimir_etiqueta,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#457B9D",
            hover_color="#1D3557",
            height=35
        )
        self.btn_imprimir.pack(fill="x", padx=10, pady=(0, 8))

        # Botón BORRAR
        btn_borrar_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#F1B4BB",
            corner_radius=8,
            border_width=2,
            border_color="#C1666B"
        )
        btn_borrar_frame.pack(fill="x")

        ctk.CTkLabel(btn_borrar_frame, text="🗑️", font=ctk.CTkFont(size=24)).pack(pady=(8, 3))

        self.btn_borrar = ctk.CTkButton(
            btn_borrar_frame,
            text="BORRAR",
            command=self.on_borrar_registro,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            height=35
        )
        self.btn_borrar.pack(fill="x", padx=10, pady=(0, 8))

        # ---------- Panel de pruebas FIJO ----------
        self.panel_pruebas = PanelPruebasConexion(self, self.modelo, self.q)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        # Cargar registros
        self.load_daily_records()

    def load_daily_records(self):
        from src.backend.endpoints.conexion import get_daily_report_path
        ruta_csv = get_daily_report_path()

        if not ruta_csv.exists():
            # No hay archivo hoy → tabla vacía
            self.set_table_rows([])
            self.detail_status_var.set("No hay registros para el día de hoy.")
            return

        rows = []
        with ruta_csv.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # HEADERS del CSV (los que usaste en saveBDiaria):
                # "ID", "SN", "MAC", "SSID_24", "SSID_5", "PASSWORD",
                # "MODELO", "STATUS", "VERSION_INICIAL", "VERSION_FINAL",
                # "TIPO_PRUEBA", "FECHA", "VERSION_ONT_TESTER"

                fila = [
                    row.get("ID", ""),
                    row.get("SN", ""),          # se mostrará como "SNN" en la tabla
                    row.get("MAC", ""),
                    row.get("SSID_24", ""),
                    row.get("SSID_5", ""),
                    row.get("PASSWORD", ""),
                    row.get("STATUS", ""),
                    row.get("TIPO_PRUEBA", ""),
                    row.get("MODELO", ""),
                    row.get("FECHA", ""),
                ]
                rows.append(fila)

        self.set_table_rows(rows)
        self.detail_status_var.set(f"{len(rows)} registros cargados.")

    # =========================================================
    #                NAVEGACIÓN (REDIRECCIÓN)
    # =========================================================
    def _swap_view(self, view_cls):
        """
        Redirige dentro del MISMO contenedor (self.master).
        """
        parent = self.master
        try:
            self.destroy()
        except Exception:
            pass

        nueva = view_cls(parent, self.modelo, self.q)
        nueva.pack(fill="both", expand=True)

    def ir_a_ont_tester(self):
        print("Navegando a ONT TESTER")
        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView)

    def ir_a_base_diaria(self):
        print("Navegando a BASE DIARIA")
        self.load_daily_records()
        # Ya estás aquí. Si quieres "refresh", descomenta:
        # self._swap_view(EscaneosDiaView)
        pass

    def ir_a_base_global(self):
        print("Navegando a BASE GLOBAL")
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        print("Navegando a OTROS")
        from src.Frontend.ui.propiedades_view import TesterMainView
        self._swap_view(TesterMainView)

    # --------- Llenado de la tabla ---------
    def set_table_rows(self, rows):
        """Rellena la tabla con filas de datos."""
        self.all_rows = list(rows)
        self.table_rows_data = self.all_rows

        # Borrar filas anteriores
        for widget in self.table_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()

        self.row_label_widgets = []
        body_font = ctk.CTkFont(size=10)

        row_colors = ["#F0F4F8", "#E1E8ED"]

        for r_idx, row in enumerate(self.table_rows_data, start=1):
            row_widgets = []
            row_color = row_colors[(r_idx - 1) % 2]

            for c_idx, value in enumerate(row):
                cell_frame = ctk.CTkFrame(
                    self.table_frame,
                    fg_color=row_color,
                    corner_radius=0,
                    border_width=1,
                    border_color="#B8C5D0"
                )
                cell_frame.grid(row=r_idx, column=c_idx, sticky="nsew")

                display_text = str(value)
                if len(display_text) > 15:
                    display_text = display_text[:12] + "..."

                label = ctk.CTkLabel(
                    cell_frame,
                    text=display_text,
                    font=body_font,
                    text_color="#2C3E50",
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
        """Actualiza el panel derecho con los datos de la fila clickeada."""
        if not (0 <= row_index < len(self.table_rows_data)):
            return

        row = self.table_rows_data[row_index]

        for col_index, key in enumerate(self.headers):
            if col_index < len(row):
                self.detail_vars[key].set(str(row[col_index]))
            else:
                self.detail_vars[key].set("")

        self._highlight_row(row_index)
        self.detail_status_var.set("")

    def _clear_highlight(self):
        if self.highlighted_row is None:
            return
        if 0 <= self.highlighted_row < len(self.row_label_widgets):
            row_colors = ["#F0F4F8", "#E1E8ED"]
            row_color = row_colors[self.highlighted_row % 2]
            for cell_frame, label in self.row_label_widgets[self.highlighted_row]:
                cell_frame.configure(fg_color=row_color, border_color="#B8C5D0")
                label.configure(text_color="#2C3E50")
        self.highlighted_row = None

    def _highlight_row(self, index):
        self._clear_highlight()
        if not (0 <= index < len(self.row_label_widgets)):
            return
        for cell_frame, label in self.row_label_widgets[index]:
            cell_frame.configure(fg_color="#7FB3D5", border_color="#457B9D")
            label.configure(text_color="white")
        self.highlighted_row = index

    def search_by_sn(self, event=None):
        """Busca S/N (columna SNN - índice 1) en todas las filas."""
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
        """Acción del botón IMPRIMIR ETIQUETA."""
        if self.highlighted_row is None:
            self.detail_status_var.set("Selecciona un registro para imprimir.")
            return

        row_data = self.table_rows_data[self.highlighted_row]

        if self.viewmodel:
            try:
                print(f"Enviando a backend para imprimir: {row_data}")
                self.detail_status_var.set("Etiqueta enviada a impresión.")
            except Exception as e:
                self.detail_status_var.set(f"Error: {str(e)}")
        else:
            print(f"Imprimiendo etiqueta: {row_data}")
            self.detail_status_var.set("Etiqueta enviada a impresión.")

    def on_borrar_registro(self):
        """Acción del botón BORRAR."""
        if self.highlighted_row is None:
            self.detail_status_var.set("Selecciona un registro para borrar.")
            return

        row_data = self.table_rows_data[self.highlighted_row]

        respuesta = messagebox.askyesno(
            "Confirmar borrado",
            f"¿Borrar registro?\n\nID: {row_data[0]}\nSNN: {row_data[1]}\nMAC: {row_data[2]}",
            icon='warning'
        )

        if not respuesta:
            return

        try:
            if self.viewmodel:
                print(f"Llamando a backend para borrar registro ID: {row_data[0]}")

            index_to_remove = self.highlighted_row
            self.all_rows.pop(index_to_remove)

            for key in self.detail_vars:
                self.detail_vars[key].set("")

            self.set_table_rows(self.all_rows)
            self.detail_status_var.set("Registro borrado exitosamente.")

        except Exception as e:
            self.detail_status_var.set(f"Error al borrar: {str(e)}")
            messagebox.showerror("Error", f"No se pudo borrar:\n{str(e)}")

    # --------- Tooltips para mostrar texto completo ---------
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

        tooltip_frame = ctk.CTkFrame(
            self.tooltip_window,
            fg_color="#2C3E50",
            corner_radius=6,
            border_width=1,
            border_color="#6B9080"
        )
        tooltip_frame.pack(padx=2, pady=2)

        label = ctk.CTkLabel(
            tooltip_frame,
            text=text,
            font=ctk.CTkFont(size=11),
            text_color="white",
            fg_color="transparent"
        )
        label.pack(padx=8, pady=6)

    def _hide_tooltip(self):
        if self.tooltip_job:
            self.after_cancel(self.tooltip_job)
            self.tooltip_job = None

        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


# Test
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER")
    app.geometry("1400x800")

    view = EscaneosDiaView(app)
    view.pack(fill="both", expand=True)

    ejemplo_filas = [
        [1, "SNN001", "AA:BB:CC:DD:EE:01", "Totalplay-2.4G", "Totalplay-5G", "pass1234", "FUNCIONAL", "C001", "FIBERHOME", "22/10/2025"],
        [2, "SNN002", "AA:BB:CC:DD:EE:02", "Totalplay-2.4G", "Totalplay-5G", "pass5678", "FUNCIONAL", "C010", "FIBERHOME", "22/10/2025"],
        [3, "SNN003", "AA:BB:CC:DD:EE:03", "Totalplay-2.4G", "Totalplay-5G", "pass9999", "FUNCIONAL", "C020", "FIBERHOME", "22/10/2025"],
        [4, "SNN004", "AA:BB:CC:DD:EE:04", "Totalplay-2.4G", "Totalplay-5G", "pass1111", "FUNCIONAL", "C030", "FIBERHOME", "22/10/2025"],
        [5, "SNN005", "AA:BB:CC:DD:EE:05", "Totalplay-2.4G", "Totalplay-5G", "pass2222", "FUNCIONAL", "C040", "FIBERHOME", "22/10/2025"],
    ]
    view.set_table_rows(ejemplo_filas)

    app.mainloop()
