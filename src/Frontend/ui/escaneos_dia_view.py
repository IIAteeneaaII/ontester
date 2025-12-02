# src/Frontend/ui/escaneos_dia_view.py 

import customtkinter as ctk
import sys
from pathlib import Path

# Para poder usar imports absolutos (igual que en tester_view)
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion


class EscaneosDiaView(ctk.CTkFrame):
    """
    Vista para 'Escaneos del día'.

    Muestra:
      - Un título en la parte superior.
      - Una tabla con cabeceras:
        ID, SNN, MAC, SSID, SSID-5G, PASSWORD, STATUS, CÓDIGO, MODELO, FECHA
      - A la derecha de la tabla, un panel de detalle con campos para cada columna.
      - El panel de pruebas de conectividad (PanelPruebasConexion) en la parte inferior.
    """

    def __init__(self, parent, viewmodel=None, **kwargs):
        # Fondo azul claro, consistente con TesterView
        super().__init__(parent, fg_color="#E9F5FF", **kwargs)

        self.viewmodel = viewmodel

        # Datos de configuración de la tabla
        self.headers = [
            "ID",
            "SNN",
            "MAC",
            "SSID",
            "SSID-5G",
            "PASSWORD",
            "STATUS",
            "CÓDIGO",
            "MODELO",
            "FECHA",
        ]
        # Texto que se mostrará en el panel derecho (puede diferir del header)
        self.detail_label_texts = {
            "ID": "ID",
            "SNN": "SERIE",
            "MAC": "MAC",
            "SSID": "SSID",
            "SSID-5G": "SSID-5G",
            "PASSWORD": "PASSWORD",
            "STATUS": "STATUS",
            "CÓDIGO": "CÓDIGO",
            "MODELO": "MODELO",
            "FECHA": "FECHA DE TESTEO",
        }

        self.table_rows_data = []   # filas actualmente mostradas (se mantiene igual a all_rows)
        self.all_rows = []          # todas las filas originales (para búsquedas)
        self.detail_vars = {}       # StringVars de cada campo del panel derecho

        # Widgets por fila (lista de listas de CTkLabel) para poder resaltar
        self.row_label_widgets = []
        self.highlighted_row = None

        # Layout básico: un solo frame interno que contiene todo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        # reducir padding lateral/vertical para ganar espacio
        self.main_content.grid(row=0, column=0, sticky="nsew", padx=20, pady=16)

        # ---------- Título de la ventana ----------
        titulo = ctk.CTkLabel(
            self.main_content,
            text="Escaneos del día",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#2C3E50",
        )
        # menos espacio sobre y bajo el título
        titulo.pack(side="top", anchor="w", pady=(0, 8))

        # ---------- Contenedor tabla + panel derecho ----------
        self.table_container = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.table_container.pack(side="top", fill="both", expand=True, pady=(0, 4))

        self.table_container.grid_rowconfigure(0, weight=1)
        self.table_container.grid_columnconfigure(0, weight=3)  # tabla
        self.table_container.grid_columnconfigure(1, weight=2)  # panel detalle

        # ---------- Tabla de escaneos (lado izquierdo) ----------
        self.table_frame = ctk.CTkFrame(
            self.table_container,
            fg_color="#FFFFFF",
            corner_radius=8,
        )
        # reducir margen derecho de la tabla para dejar más espacio al panel de detalle
        self.table_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        # Configurar columnas de la tabla
        for col in range(len(self.headers)):
            self.table_frame.grid_columnconfigure(col, weight=1)

        # Fila de encabezados
        header_font = ctk.CTkFont(size=13, weight="bold")
        for col, title in enumerate(self.headers):
            label = ctk.CTkLabel(
                self.table_frame,
                text=title,
                font=header_font,
                text_color="#1B4F72",
            )
            # menos padding en encabezados
            label.grid(row=0, column=col, padx=3, pady=3, sticky="nsew")

        # ---------- Panel de detalle (lado derecho) ----------
        self.detail_frame = ctk.CTkFrame(
            self.table_container,
            fg_color="#F8F9F9",
            corner_radius=8,
        )
        self.detail_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
        )

        self.detail_frame.grid_columnconfigure(0, weight=0)
        self.detail_frame.grid_columnconfigure(1, weight=1)

        detail_font_label = ctk.CTkFont(size=12, weight="bold")
        detail_font_value = ctk.CTkFont(size=12)

        # --- Search by S/N (nuevo) ---
        search_frame = ctk.CTkFrame(self.detail_frame, fg_color="transparent")
        # reducir padding del buscador
        search_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=8, pady=(6, 2))

        lbl_search = ctk.CTkLabel(
            search_frame,
            text="Buscar S/N:",
            font=detail_font_label,
            text_color="#2C3E50",
        )
        lbl_search.pack(side="left", padx=(0, 6))

        self.search_var = ctk.StringVar(value="")
        search_entry = ctk.CTkEntry(
            search_frame,
            textvariable=self.search_var,
            font=detail_font_value,
            width=180,
        )
        search_entry.pack(side="left", padx=(0, 6))
        search_entry.bind("<Return>", self.search_by_sn)

        btn_search = ctk.CTkButton(search_frame, text="Buscar", command=self.search_by_sn, width=80)
        btn_search.pack(side="left")

        # Mensaje de estado de la búsqueda
        self.detail_status_var = ctk.StringVar(value="")
        status_lbl = ctk.CTkLabel(
            self.detail_frame,
            textvariable=self.detail_status_var,
            font=ctk.CTkFont(size=11),
            text_color="#C0392B",
        )
        # más espacio vertical para el label de estado/error
        status_lbl.grid(row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(4, 6))

        # Los campos de detalle comienzan a partir de la fila 2 (0=search, 1=status)
        for row_index, key in enumerate(self.headers, start=2):
            label_text = self.detail_label_texts.get(key, key)
            lbl = ctk.CTkLabel(
                self.detail_frame,
                text=f"{label_text}:",
                font=detail_font_label,
                text_color="#2C3E50",
                anchor="e",
            )
            lbl.grid(
                row=row_index,
                column=0,
                padx=(8, 4),
                pady=2,
                sticky="e",
            )

            var = ctk.StringVar(value="")  # valor inicial vacío
            self.detail_vars[key] = var

            # Rectángulo donde vendrán los datos (Entry de solo lectura)
            entry = ctk.CTkEntry(
                self.detail_frame,
                textvariable=var,
                font=detail_font_value,
                # ancho reducido para ganar espacio horizontal
                width=200,
                state="readonly",
            )
            entry.grid(
                row=row_index,
                column=1,
                padx=(0, 8),
                pady=2,
                sticky="w",
            )

        # ---------- Contenedor de pruebas (reutilizado) ----------
        self.panel_pruebas = PanelPruebasConexion(self.main_content)
        # reducir padding superior/inferior del panel de pruebas para que quepa mejor
        self.panel_pruebas.pack(side="bottom", fill="x", expand=False, padx=0, pady=(2, 0))
        # ------------------------------------------

    # --------- Llenado de la tabla y selección ---------

    def set_table_rows(self, rows):
        """
        Rellena la tabla con filas de datos.

        rows: iterable de filas; cada fila debe tener 10 valores en el
        mismo orden que las cabeceras:
        [ID, SNN, MAC, SSID, SSID-5G, PASSWORD, STATUS, CÓDIGO, MODELO, FECHA]

        Nota: ahora guardamos las filas originales en self.all_rows y las mostramos
        todas en la tabla (la búsqueda no filtra la tabla; sólo actualiza el panel derecho
        y resalta la fila encontrada).
        """
        # Guardar todas las filas originales
        self.all_rows = list(rows)
        # Actualmente mostramos todas las filas
        self.table_rows_data = self.all_rows

        # Borrar filas anteriores (mantener la fila 0 de encabezados)
        for widget in self.table_frame.grid_slaves():
            if int(widget.grid_info().get("row", 0)) > 0:
                widget.destroy()

        self.row_label_widgets = []
        body_font = ctk.CTkFont(size=12)

        for r_idx, row in enumerate(self.table_rows_data, start=1):
            row_widgets = []
            for c_idx, value in enumerate(row):
                # crear label con fondo transparente para poder resaltarlo luego
                label = ctk.CTkLabel(
                    self.table_frame,
                    text=str(value),
                    font=body_font,
                    text_color="#2C3E50",
                    fg_color="transparent",
                )
                # reducir padding de las celdas para compactar filas
                label.grid(row=r_idx, column=c_idx, padx=3, pady=1, sticky="nsew")

                # Al hacer click en cualquier celda de la fila,
                # se actualiza el panel derecho con los datos de esa fila.
                label.bind(
                    "<Button-1>",
                    lambda event, row_index=r_idx - 1: self.on_row_click(row_index),
                )
                row_widgets.append(label)

            self.row_label_widgets.append(row_widgets)

        # limpiar cualquier resaltado previo
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

    # --- Resaltar filas ---
    def _clear_highlight(self):
        if self.highlighted_row is None:
            return
        if 0 <= self.highlighted_row < len(self.row_label_widgets):
            for lbl in self.row_label_widgets[self.highlighted_row]:
                lbl.configure(fg_color="transparent", text_color="#2C3E50")
        self.highlighted_row = None

    def _highlight_row(self, index):
        # index se refiere al índice dentro de self.table_rows_data (orden mostrado)
        self._clear_highlight()
        if not (0 <= index < len(self.row_label_widgets)):
            return
        for lbl in self.row_label_widgets[index]:
            lbl.configure(fg_color="#2C7BE5", text_color="#FFFFFF")
        self.highlighted_row = index

    def search_by_sn(self, event=None):
        """Busca S/N en todas las filas; actualiza el panel derecho y resalta la fila encontrada."""
        query = self.search_var.get().strip()
        if not query:
            # limpiar estado y resaltado si se borra la búsqueda
            self.detail_status_var.set("")
            self._clear_highlight()
            return

        found_index = None
        for i, row in enumerate(self.all_rows):
            # proteger contra filas cortas
            if len(row) > 1 and query.lower() in str(row[1]).lower():
                found_index = i
                break

        if found_index is None:
            self.detail_status_var.set("No se encontraron resultados.")
            self._clear_highlight()
            return

        # Mostrar datos en panel derecho y resaltar la fila encontrada
        # (self.table_rows_data está en el mismo orden que self.all_rows)
        self.on_row_click(found_index)
        self._highlight_row(found_index)
        self.detail_status_var.set("")


# Para probar esta vista de forma independiente
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Escaneos del día")
    app.geometry("1300x650")

    view = EscaneosDiaView(app)
    view.pack(fill="both", expand=True)

    # Ejemplo de prueba de filas (puedes borrar esto cuando conectes con tu VM)
    ejemplo_filas = [
        [1, "SNN001", "AA:BB:CC:DD:EE:01", "Totalplay-2.4G", "Totalplay-5G",
         "pass1234", "FUNCIONAL", "C001", "FIBERHOME", "22/10/2025"],
        [2, "SNN002", "AA:BB:CC:DD:EE:02", "Totalplay-2.4G", "Totalplay-5G",
         "pass5678", "FUNCIONAL", "C010", "FIBERHOME", "22/10/2025"],
    ]
    view.set_table_rows(ejemplo_filas)

    app.mainloop()
