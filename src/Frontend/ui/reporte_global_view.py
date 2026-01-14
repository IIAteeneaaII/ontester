import customtkinter as ctk
import sys
import csv
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

    def __init__(self, parent, modelo, q, viewmodel=None, **kwargs):
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)

        self.viewmodel = viewmodel

        self.modelo = modelo
        self.q = q
        # Para almacenar los datos y referencias de las filas
        self.table_rows = []
        self.row_widgets = []

        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # título
        self.grid_rowconfigure(1, weight=1)  # contenido central
        self.grid_rowconfigure(2, weight=0)  # panel de pruebas

        # ---------- Título verde ----------
        title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        # Menú a la izquierda, título a la derecha
        title_frame.grid_columnconfigure(0, weight=0)
        title_frame.grid_columnconfigure(1, weight=1)

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
            text="ONT TESTER - REPORTE GLOBAL",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        titulo.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # ---------- Contenido central ----------
        self._crear_contenido_central()

        # ---------- Panel de pruebas ----------
        self.panel_pruebas = PanelPruebasConexion(self, self.modelo, self.q)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

    # Helpers para la tabla
    def _clear_table(self):
        """Elimina todas las filas actuales de la tabla (deja solo encabezados)."""
        for row_info in self.row_widgets:
            for frame in row_info['frames']:
                frame.destroy()

        self.row_widgets = []
        self.table_rows = []

    def _set_table_rows(self, rows):
        """
        Recibe una lista de filas (listas de valores) y las pinta en la tabla.
        El orden de las columnas debe coincidir con 'headers' definidos en _crear_contenido_central.
        """
        self._clear_table()

        self.table_rows = rows
        body_font = ctk.CTkFont(size=10)

        for row_idx, row_data in enumerate(rows, start=1):
            row_frames = []
            row_color = "#F0F4F8" if row_idx % 2 == 1 else "#E1E8ED"

            for col, value in enumerate(row_data):
                cell_frame = ctk.CTkFrame(
                    self.table_frame,
                    fg_color=row_color,
                    corner_radius=0,
                    border_width=1,
                    border_color="#B8C5D0"
                )
                cell_frame.grid(row=row_idx, column=col, sticky="nsew")

                label = ctk.CTkLabel(
                    cell_frame,
                    text=str(value),
                    font=body_font,
                    text_color="#2C3E50",
                    fg_color="transparent",
                )
                label.pack(padx=4, pady=3)

                row_frames.append(cell_frame)

            self.row_widgets.append({
                'frames': row_frames,
                'data': row_data,
                'original_color': row_color
            })
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
        try:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        except ImportError:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        self._swap_view(EscaneosDiaView)

    def ir_a_base_global(self):
        print("Navegando a BASE GLOBAL")
        # Ya estás aquí. Si quieres "refresh", descomenta:
        # self._swap_view(ReporteGlobalView)
        pass

    def ir_a_otros(self):
        print("Navegando a OTROS")
        from src.Frontend.ui.propiedades_view import TesterMainView
        self._swap_view(TesterMainView)

    # =========================================================
    #                UI CENTRAL
    # =========================================================
    def _crear_contenido_central(self):
        """Crea el contenido central basado en la primera imagen."""
        central_frame = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        central_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)

        central_frame.grid_columnconfigure(0, weight=1)
        central_frame.grid_rowconfigure(0, weight=0)  # equipos en base
        central_frame.grid_rowconfigure(1, weight=0)  # controles fecha
        central_frame.grid_rowconfigure(2, weight=1)  # tabla datos

        # ---------- EQUIPOS EN BASE ----------
        equipos_frame = ctk.CTkFrame(
            central_frame,
            fg_color="#90C695",
            corner_radius=8,
            border_width=2,
            border_color="#6B9080"
        )
        equipos_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            equipos_frame,
            text="EQUIPOS EN BASE:",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        ).pack(side="left", padx=20, pady=10)

        self.equipos_count_label = ctk.CTkLabel(
            equipos_frame,
            text="",
            font=ctk.CTkFont(size=32, weight="bold"),
            text_color="#2C3E50"
        )
        self.equipos_count_label.pack(side="left", padx=(0, 20), pady=10)

        # ---------- Controles de fecha y botones ----------
        controls_frame = ctk.CTkFrame(central_frame, fg_color="transparent")
        controls_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        controls_frame.grid_columnconfigure(0, weight=0)
        controls_frame.grid_columnconfigure(1, weight=0)
        controls_frame.grid_columnconfigure(2, weight=0)
        controls_frame.grid_columnconfigure(3, weight=1)
        controls_frame.grid_columnconfigure(4, weight=0)
        controls_frame.grid_columnconfigure(5, weight=0)

        # Selectores de fecha
        date_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        date_frame.grid(row=0, column=0, sticky="w", padx=(0, 20))

        ctk.CTkLabel(date_frame, text="día", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=5)

        self.dia_combo = ctk.CTkComboBox(
            date_frame,
            values=[str(i) for i in range(1, 32)],
            width=70,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.dia_combo.set("22")
        self.dia_combo.grid(row=1, column=0, padx=5)

        ctk.CTkLabel(date_frame, text="mes", font=ctk.CTkFont(size=11)).grid(row=0, column=1, padx=5)

        self.mes_combo = ctk.CTkComboBox(
            date_frame,
            values=[str(i) for i in range(1, 13)],
            width=70,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.mes_combo.set("10")
        self.mes_combo.grid(row=1, column=1, padx=5)

        ctk.CTkLabel(date_frame, text="año", font=ctk.CTkFont(size=11)).grid(row=0, column=2, padx=5)

        self.anio_combo = ctk.CTkComboBox(
            date_frame,
            values=["2024", "2025", "2026"],
            width=90,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.anio_combo.set("2025")
        self.anio_combo.grid(row=1, column=2, padx=5)

        # Botón CARGAR BASE DEL DÍA
        btn_cargar_dia = ctk.CTkButton(
            controls_frame,
            text="CARGAR BASE DEL DÍA",
            command=self.cargar_base_dia,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            height=40,
            width=200
        )
        btn_cargar_dia.grid(row=0, column=1, padx=10)

        # Búsqueda
        search_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        search_frame.grid(row=0, column=2, padx=10)

        ctk.CTkLabel(
            search_frame,
            text="BUSCAR SERIE",
            font=ctk.CTkFont(size=11, weight="bold")
        ).pack(anchor="w")

        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="Ingrese serie...",
            width=200,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.search_entry.pack()
        self.search_entry.bind("<KeyRelease>", self.buscar_serie)

        # Botón CARGAR BASE GLOBAL
        btn_cargar_global = ctk.CTkButton(
            controls_frame,
            text="CARGAR BASE GLOBAL",
            command=self.cargar_base_global,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            height=40,
            width=200
        )
        btn_cargar_global.grid(row=0, column=4, padx=10)

        # Botón Generar Excel
        btn_excel = ctk.CTkButton(
            controls_frame,
            text="Generar Excel",
            command=self.generar_excel,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#457B9D",
            hover_color="#1D3557",
            height=40,
            width=150
        )
        btn_excel.grid(row=0, column=5, padx=(10, 0))

        # ---------- Tabla de datos ----------
        table_container = ctk.CTkFrame(
            central_frame,
            fg_color="#C8D8E4",
            corner_radius=8,
            border_width=2,
            border_color="#8FA3B0"
        )
        table_container.grid(row=2, column=0, sticky="nsew", pady=(0, 10))
        table_container.grid_rowconfigure(0, weight=1)
        table_container.grid_columnconfigure(0, weight=1)

        self.table_scrollable = ctk.CTkScrollableFrame(
            table_container,
            fg_color="transparent",
            corner_radius=0,
            scrollbar_button_color="#6B9080",
            scrollbar_button_hover_color="#5A7A6A",
        )
        self.table_scrollable.grid(row=0, column=0, sticky="nsew", padx=3, pady=3)

        headers = [
            "ID", "SERIE", "MAC", "VERSION_INICIAL", "VERSION_FINAL", "MODELO",
            "FECHA_DE_PRUEBA", "VERSION_DE_ONT_TES",
            "SSID", "SSID5", "CONTRASEÑA", "STATUS"
        ]

        self.table_frame = ctk.CTkFrame(self.table_scrollable, fg_color="transparent")
        self.table_frame.pack(fill="both", expand=True)

        for col in range(len(headers)):
            self.table_frame.grid_columnconfigure(col, weight=1, minsize=100)

        header_font = ctk.CTkFont(size=11, weight="bold")
        for col, title in enumerate(headers):
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

        # self._agregar_filas_ejemplo()
        self.cargar_base_global()

    def _agregar_filas_ejemplo(self):
        """Agrega múltiples filas de ejemplo a la tabla."""
        ejemplo_datos = [
            ["1", "CXABA4EABAGEO", "D4D0689E0B8D", "RP4375", "RP4375", "FIBERHOME H", "22/10/2025 08:11", "21.5.612", "DESCONECTADO", "DESCONECTADO", "DESCONECTADO", "CONECTADO"],
            ["2", "FHTT2AB5C9876", "A1B2C3D4E5F6", "RP4380", "RP4385", "FIBERHOME AN5506-04", "22/10/2025 09:15", "21.6.001", "CONECTADO", "CONECTADO", "DESCONECTADO", "CONECTADO"],
            ["3", "HWTT56789ABCD", "11:22:33:44:55:66", "V5.2.0", "V5.2.1", "HUAWEI HG8546M", "22/10/2025 10:22", "21.5.700", "CONECTADO", "DESCONECTADO", "CONECTADO", "CONECTADO"],
            ["4", "FHTT9XYZ12345", "AA:BB:CC:DD:EE:FF", "RP4370", "RP4375", "FIBERHOME AN5506-01", "22/10/2025 11:30", "21.5.612", "CONECTADO", "CONECTADO", "CONECTADO", "CONECTADO"],
            ["5", "HWTT7KLMN8901", "12:34:56:78:9A:BC", "V5.1.5", "V5.2.0", "HUAWEI EG8145V5", "22/10/2025 12:45", "21.6.100", "DESCONECTADO", "CONECTADO", "CONECTADO", "DESCONECTADO"],
            ["6", "CXDEF2GHIJK34", "DE:AD:BE:EF:CA:FE", "RP4375", "RP4380", "FIBERHOME H", "22/10/2025 13:50", "21.5.800", "CONECTADO", "CONECTADO", "DESCONECTADO", "CONECTADO"],
            ["7", "HWTT3PQRS5678", "98:76:54:32:10:FE", "V5.2.1", "V5.2.2", "HUAWEI HG8245H", "22/10/2025 14:15", "21.6.200", "CONECTADO", "DESCONECTADO", "CONECTADO", "CONECTADO"],
            ["8", "FHTT4UVWX9012", "BA:DC:0F:FE:E0:0D", "RP4380", "RP4385", "FIBERHOME AN5506-02", "22/10/2025 15:20", "21.5.900", "CONECTADO", "CONECTADO", "CONECTADO", "CONECTADO"],
            ["9", "HWTT8YZAB3456", "00:11:22:33:44:55", "V5.1.8", "V5.2.1", "HUAWEI EG8247H5", "22/10/2025 16:30", "21.6.050", "DESCONECTADO", "DESCONECTADO", "CONECTADO", "DESCONECTADO"],
            ["10", "CXCDE3FGHI789", "FF:EE:DD:CC:BB:AA", "RP4375", "RP4380", "FIBERHOME H", "22/10/2025 17:40", "21.5.750", "CONECTADO", "CONECTADO", "CONECTADO", "CONECTADO"],
        ]

        self.table_rows = ejemplo_datos
        body_font = ctk.CTkFont(size=10)

        for row_idx, row_data in enumerate(ejemplo_datos, start=1):
            row_frames = []
            row_color = "#F0F4F8" if row_idx % 2 == 1 else "#E1E8ED"

            for col, value in enumerate(row_data):
                cell_frame = ctk.CTkFrame(
                    self.table_frame,
                    fg_color=row_color,
                    corner_radius=0,
                    border_width=1,
                    border_color="#B8C5D0"
                )
                cell_frame.grid(row=row_idx, column=col, sticky="nsew")

                label = ctk.CTkLabel(
                    cell_frame,
                    text=str(value),
                    font=body_font,
                    text_color="#2C3E50",
                    fg_color="transparent",
                )
                label.pack(padx=4, pady=3)

                row_frames.append(cell_frame)

            self.row_widgets.append({
                'frames': row_frames,
                'data': row_data,
                'original_color': row_color
            })

    def buscar_serie(self, event=None):
        """Busca el número de serie y resalta la fila que coincida."""
        search_text = self.search_entry.get().strip().upper()

        for row_info in self.row_widgets:
            for frame in row_info['frames']:
                frame.configure(fg_color=row_info['original_color'])

        if not search_text:
            return

        for row_info in self.row_widgets:
            serie = row_info['data'][1].upper()  # SERIE en índice 1
            if search_text in serie:
                for frame in row_info['frames']:
                    frame.configure(fg_color="#FFE066")

    def cargar_base_dia(self):
        """Carga la base de datos del día seleccionado."""
        dia = self.dia_combo.get()
        mes = self.mes_combo.get()
        anio = self.anio_combo.get()
        print(f"Cargando base del día: {dia}/{mes}/{anio}")
        dia = int(dia)
        mes = int(mes)
        anio = int(anio)
        d = date(anio, mes, dia)
        from src.backend.endpoints.conexion import _get_report_path_for
        ruta_csv = _get_report_path_for(d)

        if not ruta_csv.exists():
            print("No existe archivo para esa fecha.")
            self._set_table_rows([])
            self.equipos_count_label.configure(text="0")
            return

        rows = []
        with ruta_csv.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                # HEADERS en tu CSV:
                # "ID", "SN", "MAC", "SSID_24", "SSID_5", "PASSWORD",
                # "MODELO", "STATUS", "VERSION_INICIAL", "VERSION_FINAL",
                # "TIPO_PRUEBA", "FECHA", "VERSION_ONT_TESTER"

                fila = [
                    row.get("ID", ""),
                    row.get("SN", ""),                 # SERIE
                    row.get("MAC", ""),
                    row.get("VERSION_INICIAL", ""),
                    row.get("VERSION_FINAL", ""),
                    row.get("MODELO", ""),
                    row.get("FECHA", ""),              # FECHA_DE_PRUEBA
                    row.get("VERSION_ONT_TESTER", ""), # VERSION_DE_ONT_TES
                    row.get("SSID_24", ""),            # SSID
                    row.get("SSID_5", ""),             # SSID5
                    row.get("PASSWORD", ""),           # CONTRASEÑA
                    row.get("STATUS", ""),
                ]
                rows.append(fila)

        self._set_table_rows(rows)
        self.equipos_count_label.configure(text=str(len(rows)))

    def cargar_base_global(self):
        """Carga la base de datos global."""
        print("Cargando base global...")
        base_dir = Path(r"C:\ONT")
        reports_dir = base_dir / "Reportes diarios"

        if not reports_dir.exists():
            print("No existe la carpeta de reportes.")
            # Limpia tabla
            self._set_table_rows([])
            self.equipos_count_label.configure(text="0")
            return

        # Buscar todos los archivos reportes_YYYY-MM-DD.csv
        files = sorted(reports_dir.glob("reportes_*.csv"))  # ordenados por nombre (fecha)
        if not files:
            print("No hay archivos CSV en la carpeta de reportes.")
            self._set_table_rows([])
            self.equipos_count_label.configure(text="0")
            return

        rows = []

        for fpath in files:
            with fpath.open(newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)

                for row in reader:
                    # Mapeo CSV -> columnas de la tabla:
                    # headers = [
                    #   "ID", "SERIE", "MAC", "VERSION_INICIAL", "VERSION_FINAL",
                    #   "MODELO", "FECHA_DE_PRUEBA", "VERSION_DE_ONT_TES",
                    #   "SSID", "SSID5", "CONTRASEÑA", "STATUS"
                    # ]
                    fila = [
                        row.get("ID", ""),
                        row.get("SN", ""),                 # SERIE
                        row.get("MAC", ""),
                        row.get("VERSION_INICIAL", ""),
                        row.get("VERSION_FINAL", ""),
                        row.get("MODELO", ""),
                        row.get("FECHA", ""),              # FECHA_DE_PRUEBA
                        row.get("VERSION_ONT_TESTER", ""), # VERSION_DE_ONT_TES
                        row.get("SSID_24", ""),            # SSID
                        row.get("SSID_5", ""),             # SSID5
                        row.get("PASSWORD", ""),           # CONTRASEÑA
                        row.get("STATUS", ""),
                    ]
                    rows.append(fila)

        # Pintar todo en la tabla
        self._set_table_rows(rows)
        self.equipos_count_label.configure(text=str(len(rows)))

    def generar_excel(self):
        """Genera archivo Excel con los datos."""
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

    view = ReporteGlobalView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()
