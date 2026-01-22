import customtkinter as ctk
import sys
from pathlib import Path
from tkinter import messagebox

# Para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion
from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable


class CambiarEstacionDialog(ctk.CTkToplevel):
    """
    Ventana emergente para cambiar el número de estación.
    """

    def __init__(self, parent, estacion_actual, userConsumible):
        super().__init__(parent)
        self.nuevo_numero = None

        # Configuración de la ventana
        self.title("Cambiar Estación")
        self.geometry("400x200")
        self.resizable(False, False)

        # Centrar la ventana
        self.transient(parent)
        self.grab_set()

        # Configurar el grid
        self.grid_columnconfigure(0, weight=1)

        # ---------- Contenido ----------
        titulo_label = ctk.CTkLabel(
            self,
            text="Ingrese el número de estación\na donde se hará el cambio",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50"
        )
        titulo_label.grid(row=0, column=0, pady=(20, 10), padx=20)

        self.entry_estacion = ctk.CTkEntry(
            self,
            width=150,
            height=40,
            font=ctk.CTkFont(size=16),
            justify="center",
            fg_color="white",
            border_color="#6B9080",
            border_width=2
        )
        self.entry_estacion.grid(row=1, column=0, pady=10)
        self.entry_estacion.insert(0, estacion_actual)
        self.entry_estacion.focus()

        self.entry_estacion.bind("<Return>", lambda e: self.confirmar())

        botones_frame = ctk.CTkFrame(self, fg_color="transparent")
        botones_frame.grid(row=2, column=0, pady=20, padx=20)

        btn_aceptar = ctk.CTkButton(
            botones_frame,
            text="ACEPTAR",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            width=120,
            height=35
        )
        btn_aceptar.pack(side="left", padx=5)

        btn_cancelar = ctk.CTkButton(
            botones_frame,
            text="CANCELAR",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            width=120,
            height=35
        )
        btn_cancelar.pack(side="left", padx=5)
        self.userConsumible = userConsumible
        self.cargarEstacion()
    
    def cargarEstacion(self):
        # Modificar valor desde config
        from src.backend.endpoints.conexion import cargarConfig
        config = cargarConfig()
        general = config.get("general", {}) or {}
        estacion = general.get("estacion")
        self.entry_estacion.delete(0, "end")
        self.entry_estacion.insert(0, estacion)

    def confirmar(self):
        """Valida y guarda el nuevo número de estación."""
        valor = self.entry_estacion.get().strip()

        if not valor:
            messagebox.showwarning(
                "Advertencia",
                "Por favor ingrese un número de estación.",
                parent=self
            )
            return

        if not valor.isdigit():
            messagebox.showerror(
                "Error",
                "El número de estación debe contener solo dígitos.",
                parent=self
            )
            return
        from src.backend.endpoints.conexion import guardarConfig
        user_id = self.userConsumible
        guardarConfig(valor, "estacion", user_id)

        self.nuevo_numero = valor.zfill(2)  # 01, 02, etc.
        self.destroy()

    def cancelar(self):
        """Cancela el cambio."""
        self.nuevo_numero = None
        self.destroy()


class ModificarEtiquetadoDialog(ctk.CTkToplevel):
    """
    Ventana emergente para configurar el modo de etiqueta.
    """

    def __init__(self, parent, userConsumible):
        super().__init__(parent)

        self.resultado = None

        self.title("Configuración de Etiqueta")
        self.geometry("450x250")
        self.resizable(False, False)
        self.configure(fg_color="#E8E8E8")

        self.transient(parent)
        self.grab_set()

        close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            corner_radius=5,
            fg_color="#C1666B",
            hover_color="#A4161A",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.cancelar
        )
        close_btn.place(x=410, y=10)

        titulo_label = ctk.CTkLabel(
            self,
            text="CONFIGURACIÓN DE ETIQUETA",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        )
        titulo_label.pack(pady=(20, 30), padx=20)

        opciones_label = ctk.CTkLabel(
            self,
            text="MODO DE ETIQUETA DE FIBERHOME",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#2C3E50"
        )
        opciones_label.pack(pady=(0, 15))

        self.etiqueta_var = ctk.StringVar(value="unica")

        radio_unica = ctk.CTkRadioButton(
            self,
            text="ETIQUETA ÚNICA",
            variable=self.etiqueta_var,
            value="unica",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
            fg_color="#4EA5D9",
            hover_color="#3B8CC2"
        )
        radio_unica.pack(pady=5, padx=40, anchor="w")

        radio_doble = ctk.CTkRadioButton(
            self,
            text="ETIQUETA DOBLE",
            variable=self.etiqueta_var,
            value="doble",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
            fg_color="#4EA5D9",
            hover_color="#3B8CC2"
        )
        radio_doble.pack(pady=5, padx=40, anchor="w")

        btn_aceptar = ctk.CTkButton(
            self,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            width=120,
            height=35
        )
        btn_aceptar.pack(pady=(20, 15))
        self.userConsumible = userConsumible
        self.cargarEtiqueta()
    
    def cargarEtiqueta(self):
        from src.backend.endpoints.conexion import cargarConfig
        config = cargarConfig()
        general = config.get("general", {}) or {}
        etiqueta = general.get("etiqueta")
        if etiqueta == 1:
            etiqueta = "unica"
        else:
            etiqueta = "doble"
        self.etiqueta_var.set(etiqueta)

    def confirmar(self):
        self.resultado = self.etiqueta_var.get()
        print(f"Modo de etiqueta seleccionado: {self.resultado}")
        if(self.resultado == "unica"):
            etiq = 1
        else:
            etiq = 2
        from src.backend.endpoints.conexion import guardarConfig
        user_id = self.userConsumible
        guardarConfig(etiq, "etiqueta", user_id)
        self.destroy()

    def cancelar(self):
        self.resultado = None
        self.destroy()


class ModificarParametrosDialog(ctk.CTkToplevel):
    """
    Ventana emergente para configurar los parámetros del ONT TESTER.
    """

    def __init__(self, parent, userConsumible):
        super().__init__(parent)

        self.resultado = None

        self.title("Parámetros de ONT Tester")
        self.geometry("550x700")
        self.resizable(False, False)
        self.configure(fg_color="#E8E8E8")

        self.transient(parent)
        self.grab_set()

        close_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            corner_radius=5,
            fg_color="#C1666B",
            hover_color="#A4161A",
            font=ctk.CTkFont(size=16, weight="bold"),
            command=self.cancelar
        )
        close_btn.place(x=510, y=10)

        titulo_label = ctk.CTkLabel(
            self,
            text="PARÁMETROS DE ONT TESTER",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50"
        )
        titulo_label.pack(pady=(20, 25), padx=20)

        main_scrollable = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            width=500,
            height=500
        )
        main_scrollable.pack(fill="both", expand=True, padx=20, pady=(0, 10))

        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES EN TX",
            "tx_min", "tx_max",
            valores_min=["1.00", "2.00", "3.00", "4.00", "5.00"],
            valores_max=["3.00", "4.00", "5.00", "6.00"],
            default_min="1.00",
            default_max="5.00"
        )

        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES EN RX",
            "rx_min", "rx_max",
            valores_min=["-30.00", "-25.00", "-20.00", "-15.00", "-10.00"],
            valores_max=["-13.00", "-12.00", "-11.00", "-10.00"],
            default_min="-20.00",
            default_max="-12.00"
        )

        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES RSSI 2.4 GHz",
            "rssi24_min", "rssi24_max",
            valores_min=["-80", "-70", "-60", "-50"],
            valores_max=["-10", "-5", "0"],
            default_min="-80",
            default_max="-5"
        )

        self._crear_seccion_rango(
            main_scrollable,
            "RANGO DE VALORES RSSI 5.0 GHz",
            "rssi50_min", "rssi50_max",
            valores_min=["-80", "-70", "-60", "-50"],
            valores_max=["-10", "-5", "0"],
            default_min="-80",
            default_max="-5"
        )

        busquedas_frame = ctk.CTkFrame(main_scrollable, fg_color="transparent")
        busquedas_frame.pack(fill="x", pady=(20, 10))

        busquedas_label = ctk.CTkLabel(
            busquedas_frame,
            text="PORCENTAJE DE POTENCIA DE SEÑALES WIFI",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        )
        busquedas_label.pack(anchor="w", pady=(0, 10))

        self.busquedas_combo = ctk.CTkComboBox(
            busquedas_frame,
            values=["60", "70", "80", "90", "100"],
            width=200,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        self.busquedas_combo.set("60")
        self.busquedas_combo.pack(anchor="w", pady=(0, 10))

        botones_frame = ctk.CTkFrame(self, fg_color="transparent")
        botones_frame.pack(pady=(5, 20))

        btn_aceptar = ctk.CTkButton(
            botones_frame,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D4AF37",
            hover_color="#C19B2B",
            text_color="#2C3E50",
            width=120,
            height=35
        )
        btn_aceptar.pack(side="left", padx=5)

        btn_restaurar = ctk.CTkButton(
            botones_frame,
            text="Restaurar",
            command=self.restaurar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#A8DADC",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            width=120,
            height=35
        )
        btn_restaurar.pack(side="left", padx=5)

        btn_cancelar = ctk.CTkButton(
            botones_frame,
            text="Cancelar",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            text_color="white",
            width=120,
            height=35
        )
        btn_cancelar.pack(side="left", padx=5)

        # cargar config
        self.userConsumible = userConsumible
        self.cargar_desdeJSON()
    
    def cargar_desdeJSON(self):
        from src.backend.endpoints.conexion import cargarConfig
        config = cargarConfig()

        wifi = config.get("wifi", {}) or {}
        fibra = config.get("fibra", {}) or {}

        # ---- Fibra: tx / rx ----
        mintx = fibra.get("mintx")
        if mintx is not None:
            # formateo para que coincida con las opciones del ComboBox
            self.tx_min.set(f"{mintx:.2f}")

        maxtx = fibra.get("maxtx")
        if maxtx is not None:
            self.tx_max.set(f"{maxtx:.2f}")

        minrx = fibra.get("minrx")
        if minrx is not None:
            self.rx_min.set(f"{minrx:.2f}")

        maxrx = fibra.get("maxrx")
        if maxrx is not None:
            self.rx_max.set(f"{maxrx:.2f}")

        # ---- WiFi: RSSI ----
        r24_min = wifi.get("rssi24_min")
        if r24_min is not None:
            self.rssi24_min.set(str(int(r24_min)))

        r24_max = wifi.get("rssi24_max")
        if r24_max is not None:
            self.rssi24_max.set(str(int(r24_max)))

        r5_min = wifi.get("rssi5_min") or wifi.get("rssi50_min")
        if r5_min is not None:
            self.rssi50_min.set(str(int(r5_min)))

        r5_max = wifi.get("rssi5_max") or wifi.get("rssi50_max")
        if r5_max is not None:
            self.rssi50_max.set(str(int(r5_max)))

        # ---- Porcentaje de potencia ----
        min_pct = wifi.get("min24percent") or wifi.get("min5percent")
        if min_pct is not None:
            self.busquedas_combo.set(str(int(min_pct)))

    def _crear_seccion_rango(self, parent, titulo, var_min_name, var_max_name,
                            valores_min, valores_max, default_min, default_max):
        seccion_frame = ctk.CTkFrame(parent, fg_color="transparent")
        seccion_frame.pack(fill="x", pady=(15, 10))

        label = ctk.CTkLabel(
            seccion_frame,
            text=titulo,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        )
        label.pack(anchor="w", pady=(0, 10))

        combos_frame = ctk.CTkFrame(seccion_frame, fg_color="transparent")
        combos_frame.pack(anchor="w")

        combo_min = ctk.CTkComboBox(
            combos_frame,
            values=valores_min,
            width=140,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        combo_min.set(default_min)
        combo_min.pack(side="left", padx=(0, 10))
        setattr(self, var_min_name, combo_min)

        ctk.CTkLabel(
            combos_frame,
            text="a",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50"
        ).pack(side="left", padx=10)

        combo_max = ctk.CTkComboBox(
            combos_frame,
            values=valores_max,
            width=140,
            height=32,
            fg_color="white",
            border_color="#8FA3B0"
        )
        combo_max.set(default_max)
        combo_max.pack(side="left", padx=(10, 0))
        setattr(self, var_max_name, combo_max)

    def confirmar(self):
        self.resultado = {
            'tx_min': float(self.tx_min.get()),
            'tx_max': float(self.tx_max.get()),
            'rx_min': float(self.rx_min.get()),
            'rx_max': float(self.rx_max.get()),
            'rssi24_min': float(self.rssi24_min.get()),
            'rssi24_max': float(self.rssi24_max.get()),
            'rssi50_min': float(self.rssi50_min.get()),
            'rssi50_max': float(self.rssi50_max.get()),
            'busquedas': int(self.busquedas_combo.get())
        }
        print(f"Parámetros guardados: {self.resultado}")
        # guardar en el archivo de configuraciones
        from src.backend.endpoints.conexion import guardarConfig
        user_id = self.userConsumible
        guardarConfig(self.resultado, "valores", user_id)
        self.destroy()

    def restaurar(self):
        self.tx_min.set("1.0")
        self.tx_max.set("5.0")
        self.rx_min.set("-19.00")
        self.rx_max.set("-13.00")
        self.rssi24_min.set("-80")
        self.rssi24_max.set("-5")
        self.rssi50_min.set("-80")
        self.rssi50_max.set("-5")
        self.busquedas_combo.set("60")
        print("Valores restaurados a los valores por defecto")

    def cancelar(self):
        self.resultado = None
        self.destroy()


class TesterMainView(ctk.CTkFrame):
    """
    Vista principal del ONT TESTER con botones superiores y panel de pruebas.
    """

    def __init__(self, parent, modelo, viewmodel=None, **kwargs):
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)

        self.viewmodel = viewmodel
        from src.backend.endpoints.conexion import cargarConfig
        config = cargarConfig()
        general = config.get("general", {}) or {}
        estacion = general.get("estacion")
        self.numero_estacion = str(estacion) # Número de estación por defecto
        self.modelo = modelo
        app = self.winfo_toplevel()
        self.q = app.event_q
        # Layout principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # título
        self.grid_rowconfigure(1, weight=1)  # botones superiores
        self.grid_rowconfigure(2, weight=0)  # panel de pruebas

        # ---------- Título verde ----------
        title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

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

        self.titulo = ctk.CTkLabel(
            title_frame,
            text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        self.titulo.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        # ---------- Contenedor de botones superiores ----------
        buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        buttons_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        buttons_container.grid_columnconfigure(0, weight=1)
        buttons_container.grid_rowconfigure(0, weight=1)

        buttons_frame = ctk.CTkFrame(buttons_container, fg_color="transparent")
        buttons_frame.grid(row=0, column=0)

        for col in range(4):
            buttons_frame.grid_columnconfigure(col, weight=0, minsize=250)

        # ---------- Botones superiores ----------
        btn1_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#B8B8B8",
            corner_radius=15,
            width=250,
            height=180
        )
        btn1_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        btn1_frame.grid_propagate(False)

        ctk.CTkLabel(btn1_frame, text="👤", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))

        btn1 = ctk.CTkButton(
            btn1_frame,
            text="CAMBIAR ESTACIÓN",
            command=self.on_cambiar_estacion,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#A0A0A0",
            text_color="#2C3E50",
            height=40
        )
        btn1.pack(fill="x", padx=15, pady=(0, 20))

        btn2_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#F1B4BB",
            corner_radius=15,
            width=250,
            height=180
        )
        btn2_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")
        btn2_frame.grid_propagate(False)

        ctk.CTkLabel(btn2_frame, text="🏷️", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))

        btn2 = ctk.CTkButton(
            btn2_frame,
            text="MODIFICAR ETIQUETADO",
            command=self.on_modificar_etiquetado,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            height=40
        )
        btn2.pack(fill="x", padx=15, pady=(0, 20))

        btn3_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#A8DADC",
            corner_radius=15,
            width=250,
            height=180
        )
        btn3_frame.grid(row=0, column=2, padx=15, pady=10, sticky="nsew")
        btn3_frame.grid_propagate(False)

        ctk.CTkLabel(btn3_frame, text="⚙️", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))

        btn3 = ctk.CTkButton(
            btn3_frame,
            text="MODIFICAR PARÁMETROS",
            command=self.on_modificar_parametros,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            height=40
        )
        btn3.pack(fill="x", padx=15, pady=(0, 20))

        btn4_frame = ctk.CTkFrame(
            buttons_frame,
            fg_color="#F1B4BB",
            corner_radius=15,
            width=250,
            height=180
        )
        btn4_frame.grid(row=0, column=3, padx=15, pady=10, sticky="nsew")
        btn4_frame.grid_propagate(False)

        ctk.CTkLabel(btn4_frame, text="🔧", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))

        btn4 = ctk.CTkButton(
            btn4_frame,
            text="PRUEBA",
            command=self.on_prueba,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            height=40
        )
        btn4.pack(fill="x", padx=15, pady=(0, 20))

        # ---------- Panel de pruebas ----------
        self.panel_pruebas = PanelPruebasConexion(self, self.modelo)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        root = self.winfo_toplevel()
        user_id = int(getattr(root, "current_user_id", None))
        self.userConsumible = user_id

    # =========================================================
    #                NAVEGACIÓN (REDIRECCIÓN)
    # =========================================================

    def _swap_view(self, view_cls):
        """
        Redirige dentro del MISMO contenedor (self.master).
        - Evita abrir nuevas ventanas.
        - Evita depender del viewmodel.
        """
        parent = self.master
        try:
            self.destroy()
        except Exception:
            pass

        nueva = view_cls(parent, self.modelo)
        nueva.pack(fill="both", expand=True)

        # El dispatcher del parent ahora apunta a la nueva vista
        parent.dispatcher.set_target(nueva)

    # ---------- Callbacks de navegación del menú superior ----------

    def ir_a_ont_tester(self):
        print("Navegando a ONT TESTER")
        # Import local para evitar imports circulares
        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView)

    def ir_a_base_diaria(self):
        print("Navegando a BASE DIARIA")
        # Soporta escaneos_dia_view.py o escaneos_dia__view.py
        try:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        except ImportError:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView

        self._swap_view(EscaneosDiaView)

    def ir_a_base_global(self):
        print("Navegando a BASE GLOBAL")
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        print("Navegando a OTROS")
        # Ya estás aquí. Si quieres forzar "refresh", descomenta:
        # self._swap_view(TesterMainView)
        pass

    # =========================================================
    #                ACCIONES DE BOTONES
    # =========================================================

    def on_cambiar_estacion(self):
        dialog = CambiarEstacionDialog(self, self.numero_estacion, self.userConsumible)
        self.wait_window(dialog)

        if dialog.nuevo_numero is not None:
            self.numero_estacion = dialog.nuevo_numero
            self.actualizar_titulo()

    def actualizar_titulo(self):
        self.titulo.configure(
            text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}"
        )

    def on_modificar_etiquetado(self):
        dialog = ModificarEtiquetadoDialog(self, self.userConsumible)
        self.wait_window(dialog)

        if dialog.resultado is not None:
            print(f"Configuración de etiqueta guardada: {dialog.resultado}")

    def on_modificar_parametros(self):
        dialog = ModificarParametrosDialog(self, self.userConsumible)
        self.wait_window(dialog)

        if dialog.resultado is not None:
            print(f"Parámetros guardados: {dialog.resultado}")

    def on_prueba(self):
        # Aqui voy a habilitar la opción para leer la bd
        # Validar si se tiene los permisos suficientes
        root = self.winfo_toplevel()
        user_id = int(getattr(root, "current_user_id", None))
        print("El usuario es: "+str(user_id))
        if (user_id == 27 or user_id == 121):
            # Permisos ok
            self._generarBDVista()
        else:
            print("Sin permisos")

    def _generarBDVista(self):
        # Ventana hija
        win = ctk.CTkToplevel(self)
        win.title("Consulta de base de datos")
        win.geometry("900x500")
        win.grab_set()
        win.focus_set()

        # --------- PANEL SUPERIOR (combo de tablas + botón) ----------
        top_frame = ctk.CTkFrame(win)
        top_frame.pack(side="top", fill="x", padx=10, pady=10)

        lbl_tabla = ctk.CTkLabel(top_frame, text="Tabla:")
        lbl_tabla.pack(side="left", padx=(0, 10))

        win.selected_table = ctk.StringVar()

        combo_tablas = ctk.CTkComboBox(
            top_frame,
            width=250,
            state="readonly",
            variable=win.selected_table,
            values=[],
        )
        combo_tablas.pack(side="left")

        btn_cargar = ctk.CTkButton(
            top_frame,
            text="Cargar",
            command=lambda: self._cargar_tabla_en_vista(win),
        )
        btn_cargar.pack(side="left", padx=10)

        win.combo_tablas = combo_tablas

        # --------- PANEL INFERIOR (encabezados + filas scrollables) ----------
        table_frame = ctk.CTkFrame(win)
        table_frame.pack(side="top", fill="both", expand=True, padx=10, pady=(0, 10))

        # Encabezados (no scroll)
        header_frame = ctk.CTkFrame(table_frame)
        header_frame.pack(side="top", fill="x")
        win.header_frame = header_frame

        # Filas con scroll vertical
        scroll_frame = ctk.CTkScrollableFrame(
            table_frame,
            orientation="vertical",
            fg_color="transparent",   # opcional, para que se funda con el fondo
        )
        scroll_frame.pack(side="top", fill="both", expand=True)
        win.table_scroll = scroll_frame

        # Cargar lista de tablas al abrir
        self._cargar_lista_tablas(win)
    
    def _cargar_lista_tablas(self, win):
        """Llena el combo con las tablas disponibles de la BD."""
        try:
            from src.backend.sua_client.dao import obtenerTablas
            tablas = obtenerTablas()  # adapta el nombre de tu cliente
        except Exception as e:
            print(f"[BD] Error listando tablas: {e}")
            tablas = []

        if not tablas:
            win.combo_tablas.configure(values=["<sin tablas>"])
            win.combo_tablas.set("<sin tablas>")
            return

        win.combo_tablas.configure(values=tablas)
        win.combo_tablas.set(tablas[0])  # seleccionar la primera por defecto

        # Cargar la primera tabla de inmediato
        self._cargar_tabla_en_vista(win)

    def _cargar_tabla_en_vista(self, win):
        tabla = win.combo_tablas.get()
        if not tabla or tabla == "<sin tablas>":
            return

        try:
            from src.backend.sua_client.dao import fetch_table
            columnas, filas = fetch_table(tabla)
            # columnas: list[str]
            # filas: list[tuple] o list[dict]
        except Exception as e:
            print(f"[BD] Error obteniendo datos de '{tabla}': {e}")
            columnas, filas = [], []

        header_frame = win.header_frame
        scroll_frame = win.table_scroll

        # ----- LIMPIAR CONTENIDO ANTERIOR -----
        for w in header_frame.winfo_children():
            w.destroy()
        for w in scroll_frame.winfo_children():
            w.destroy()

        # Si no hay columnas, no seguimos
        if not columnas:
            lbl_empty = ctk.CTkLabel(scroll_frame, text="(Sin datos)")
            lbl_empty.grid(row=0, column=0, padx=5, pady=5, sticky="w")
            return

        # Configurar pesos de columnas para que se repartan el ancho
        for i in range(len(columnas)):
            header_frame.grid_columnconfigure(i, weight=1)
            scroll_frame.grid_columnconfigure(i, weight=1)

        # ----- ENCABEZADOS -----
        for col_idx, col_name in enumerate(columnas):
            lbl = ctk.CTkLabel(
                header_frame,
                text=col_name,
                font=ctk.CTkFont(weight="bold"),
                anchor="w",
            )
            lbl.grid(row=0, column=col_idx, padx=3, pady=3, sticky="ew")

        # ----- FILAS -----
        for r_idx, row in enumerate(filas):
            # Row como dict o tupla
            if isinstance(row, dict):
                valores = [row.get(c, "") for c in columnas]
            else:
                valores = list(row)

            for c_idx, value in enumerate(valores):
                cell = ctk.CTkLabel(
                    scroll_frame,
                    text=str(value),
                    anchor="w",
                )
                cell.grid(row=r_idx, column=c_idx, padx=3, pady=1, sticky="ew")

# Test de la vista
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER - Vista Principal")
    app.geometry("1400x700")

    view = TesterMainView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()
