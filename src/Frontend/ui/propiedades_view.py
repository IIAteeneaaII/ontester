import customtkinter as ctk
import tkinter as tk
import sys
from pathlib import Path
from tkinter import messagebox

# Para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion
from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable

# =========================================================
#                     HELPERS (RECURSOS)
# =========================================================

def resource_path(relative_path: str) -> str:
    """
    Devuelve ruta absoluta a un recurso.
    Funciona en dev y en PyInstaller (onefile/onedir).
    """
    if hasattr(sys, "_MEIPASS"):
        return str(Path(sys._MEIPASS) / relative_path)
    return str(root_path / relative_path)


# Usado solo para el test al final del archivo
APP_ICON_REL = "src/Frontend/assets/icons/ont.ico"


class BaseDialog(ctk.CTkToplevel):
    """
    Base para TODOS los diálogos: aplica el mismo icono/logo que la app.
    """
    def __init__(self, parent, *args, **kwargs):
        master = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        super().__init__(master, *args, **kwargs)
        self._icon_img = None
        self._set_logo_icon()

    def _set_logo_icon(self):
        ico_path = resource_path(APP_ICON_REL)

        def apply_icon():
            try:
                self.wm_iconbitmap(ico_path)
            except Exception as e:
                print(f"[ICON] wm_iconbitmap dialog falló: {e}")

        self.after(0, apply_icon)


class CambiarEstacionDialog(BaseDialog):
    """
    Ventana emergente para cambiar el número de estación.
    """

    def __init__(self, parent, estacion_actual, userConsumible):
        super().__init__(parent)
        self.nuevo_numero = None

        self.title("Cambiar Estación")
        self.geometry("400x200")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        self.grid_columnconfigure(0, weight=1)

        titulo_label = ctk.CTkLabel(
            self,
            text="Ingrese el número de estación\na donde se hará el cambio",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50",
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
            border_width=2,
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
            height=35,
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
            height=35,
        )
        btn_cancelar.pack(side="left", padx=5)

        self.userConsumible = userConsumible
        self.cargarEstacion()

    def cargarEstacion(self):
        from src.backend.endpoints.conexion import cargarConfig

        config = cargarConfig()
        general = config.get("general", {}) or {}
        estacion = general.get("estacion")
        self.entry_estacion.delete(0, "end")
        self.entry_estacion.insert(0, estacion)

    def confirmar(self):
        valor = self.entry_estacion.get().strip()

        if not valor:
            messagebox.showwarning(
                "Advertencia",
                "Por favor ingrese un número de estación.",
                parent=self,
            )
            return

        if not valor.isdigit():
            messagebox.showerror(
                "Error",
                "El número de estación debe contener solo dígitos.",
                parent=self,
            )
            return

        from src.backend.endpoints.conexion import guardarConfig

        user_id = self.userConsumible
        guardarConfig(valor, "estacion", user_id)

        self.nuevo_numero = valor.zfill(2)
        self.destroy()

    def cancelar(self):
        self.nuevo_numero = None
        self.destroy()


class ModificarEtiquetadoDialog(BaseDialog):
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

        titulo_label = ctk.CTkLabel(
            self,
            text="CONFIGURACIÓN DE ETIQUETA",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50",
        )
        titulo_label.pack(pady=(20, 30), padx=20)

        opciones_label = ctk.CTkLabel(
            self,
            text="MODO DE ETIQUETA DE FIBERHOME",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#2C3E50",
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
            hover_color="#3B8CC2",
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
            hover_color="#3B8CC2",
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
            height=35,
        )
        btn_aceptar.pack(pady=(20, 15))

        self.userConsumible = userConsumible
        self.cargarEtiqueta()

    def cargarEtiqueta(self):
        from src.backend.endpoints.conexion import cargarConfig

        config = cargarConfig()
        general = config.get("general", {}) or {}
        etiqueta = general.get("etiqueta")
        etiqueta = "unica" if etiqueta == 1 else "doble"
        self.etiqueta_var.set(etiqueta)

    def confirmar(self):
        self.resultado = self.etiqueta_var.get()
        print(f"Modo de etiqueta seleccionado: {self.resultado}")

        etiq = 1 if self.resultado == "unica" else 2

        from src.backend.endpoints.conexion import guardarConfig

        user_id = self.userConsumible
        guardarConfig(etiq, "etiqueta", user_id)
        self.destroy()

    def cancelar(self):
        self.resultado = None
        self.destroy()


class ModificarParametrosDialog(BaseDialog):
    """
    Ventana emergente para configurar los parámetros del ONT TESTER.
    - Scroll siempre usable (Canvas + Scrollbar)
    - El área scrollable tiene un MAX_HEIGHT, aunque la pantalla sea grande
    - Los botones quedan dentro del scroll (al final)
    """

    MAX_SCROLL_HEIGHT = 520   # <-- ajusta si quieres (500-580 suele quedar bien)
    MIN_DIALOG_W = 560
    MIN_DIALOG_H = 520

    def __init__(self, parent, userConsumible):
        super().__init__(parent)

        self.resultado = None
        self.userConsumible = userConsumible

        self.title("Parámetros de ONT Tester")
        self.geometry("600x700")
        self.minsize(self.MIN_DIALOG_W, self.MIN_DIALOG_H)

        # Puedes redimensionar, pero el scroll NO se vuelve infinito
        self.resizable(True, True)
        self.configure(fg_color="#E8E8E8")

        # Modal suave
        self.transient(parent)
        self.after(50, lambda: (self.grab_set(), self.focus_force()))

        # ---------------- Layout principal ----------------
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)  # título
        self.grid_rowconfigure(1, weight=1)  # contenedor scroll

        titulo_label = ctk.CTkLabel(
            self,
            text="PARÁMETROS DE ONT TESTER",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#2C3E50",
        )
        titulo_label.grid(row=0, column=0, pady=(20, 12), padx=20, sticky="n")

        # Contenedor del scroll (su altura se controla)
        self.scroll_host = ctk.CTkFrame(self, fg_color="transparent")
        self.scroll_host.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
        self.scroll_host.grid_columnconfigure(0, weight=1)
        self.scroll_host.grid_columnconfigure(1, weight=0)
        self.scroll_host.grid_rowconfigure(0, weight=1)

        # Canvas (tk) + Scrollbar (ctk)
        self._canvas = tk.Canvas(self.scroll_host, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._vscroll = ctk.CTkScrollbar(
            self.scroll_host, orientation="vertical", command=self._canvas.yview
        )
        self._vscroll.grid(row=0, column=1, sticky="ns", padx=(8, 0))

        self._canvas.configure(yscrollcommand=self._vscroll.set)

        # Frame interno real (contenido)
        self.content = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._content_window = self._canvas.create_window((0, 0), window=self.content, anchor="nw")

        # Mantener el contenido al ancho del canvas
        def _on_canvas_configure(event):
            self._canvas.itemconfig(self._content_window, width=event.width)

        self._canvas.bind("<Configure>", _on_canvas_configure)

        # Actualizar scrollregion cuando el contenido cambie
        def _on_content_configure(_event=None):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        self.content.bind("<Configure>", _on_content_configure)

        # ✅ Limitar altura del área scrollable aunque la ventana sea grande
        def _limit_scroll_area(_event=None):
            try:
                total_h = self.winfo_height()
                top_used = 20 + 12 + 30  # aproximación del espacio del título/paddings
                available = max(260, total_h - top_used)  # mínimo usable
                target = min(self.MAX_SCROLL_HEIGHT, available)
                self._canvas.configure(height=target)
            except Exception:
                pass

        # Se recalcula al abrir y al redimensionar
        self.bind("<Configure>", _limit_scroll_area)
        self.after(80, _limit_scroll_area)

        # Mousewheel (Windows)
        self._bind_mousewheel()

        # ---------------- CONTENIDO (dentro de self.content) ----------------
        self._crear_seccion_rango(
            self.content,
            "RANGO DE VALORES EN TX",
            "tx_min",
            "tx_max",
            valores_min=["1.00", "2.00", "3.00", "4.00", "5.00"],
            valores_max=["3.00", "4.00", "5.00", "6.00"],
            default_min="1.00",
            default_max="5.00",
        )

        self._crear_seccion_rango(
            self.content,
            "RANGO DE VALORES EN RX",
            "rx_min",
            "rx_max",
            valores_min=["-30.00", "-25.00", "-20.00", "-15.00", "-10.00"],
            valores_max=["-13.00", "-12.00", "-11.00", "-10.00"],
            default_min="-20.00",
            default_max="-12.00",
        )

        self._crear_seccion_rango(
            self.content,
            "RANGO DE VALORES RSSI 2.4 GHz",
            "rssi24_min",
            "rssi24_max",
            valores_min=["-80", "-70", "-60", "-50"],
            valores_max=["-10", "-5", "0"],
            default_min="-80",
            default_max="-5",
        )

        self._crear_seccion_rango(
            self.content,
            "RANGO DE VALORES RSSI 5.0 GHz",
            "rssi50_min",
            "rssi50_max",
            valores_min=["-80", "-70", "-60", "-50"],
            valores_max=["-10", "-5", "0"],
            default_min="-80",
            default_max="-5",
        )

        busquedas_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        busquedas_frame.pack(fill="x", pady=(20, 10))

        busquedas_label = ctk.CTkLabel(
            busquedas_frame,
            text="PORCENTAJE DE POTENCIA DE SEÑALES WIFI",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
        )
        busquedas_label.pack(anchor="w", pady=(0, 10))

        self.busquedas_combo = ctk.CTkComboBox(
            busquedas_frame,
            values=["50", "60", "70", "80", "90", "100"],
            width=240,
            height=32,
            fg_color="white",
            border_color="#8FA3B0",
        )
        self.busquedas_combo.set("60")
        self.busquedas_combo.pack(anchor="w", pady=(0, 10))

        # ---------------- BOTONES (al final, dentro del scroll) ----------------
        botones_frame = ctk.CTkFrame(self.content, fg_color="transparent")
        botones_frame.pack(fill="x", pady=(30, 10))

        botones_frame.grid_columnconfigure((0, 1, 2), weight=1)

        btn_aceptar = ctk.CTkButton(
            botones_frame,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#D4AF37",
            hover_color="#C19B2B",
            text_color="#2C3E50",
            width=120,
            height=35,
        )
        btn_aceptar.grid(row=0, column=0, padx=8, pady=(0, 10), sticky="e")

        btn_restaurar = ctk.CTkButton(
            botones_frame,
            text="Restaurar",
            command=self.restaurar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#A8DADC",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            width=120,
            height=35,
        )
        btn_restaurar.grid(row=0, column=1, padx=8, pady=(0, 10))

        btn_cancelar = ctk.CTkButton(
            botones_frame,
            text="Cancelar",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#C1666B",
            hover_color="#A4161A",
            text_color="white",
            width=120,
            height=35,
        )
        btn_cancelar.grid(row=0, column=2, padx=8, pady=(0, 10), sticky="w")

        # Spacer final para que se sienta bien al bajar
        ctk.CTkFrame(self.content, height=40, fg_color="transparent").pack()

        # Cargar config
        self.cargar_desdeJSON()

        # Forzar scrollregion al inicio
        self.after(120, lambda: self._canvas.configure(scrollregion=self._canvas.bbox("all")))

    # -------------------------
    # Mouse wheel (Windows)
    # -------------------------
    def _bind_mousewheel(self):
        def _on_mousewheel(event):
            try:
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        # bind solo a este dialog
        self._canvas.bind("<MouseWheel>", _on_mousewheel)
        self.bind("<MouseWheel>", _on_mousewheel)

    # -------------------------
    # Carga/guardado
    # -------------------------
    def cargar_desdeJSON(self):
        from src.backend.endpoints.conexion import cargarConfig

        config = cargarConfig()
        wifi = config.get("wifi", {}) or {}
        fibra = config.get("fibra", {}) or {}

        mintx = fibra.get("mintx")
        if mintx is not None:
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

        min_pct = wifi.get("min24percent") or wifi.get("min5percent")
        if min_pct is not None:
            self.busquedas_combo.set(str(int(min_pct)))

    def _crear_seccion_rango(
        self,
        parent,
        titulo,
        var_min_name,
        var_max_name,
        valores_min,
        valores_max,
        default_min,
        default_max,
    ):
        seccion_frame = ctk.CTkFrame(parent, fg_color="transparent")
        seccion_frame.pack(fill="x", pady=(15, 10))

        label = ctk.CTkLabel(
            seccion_frame,
            text=titulo,
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
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
            border_color="#8FA3B0",
        )
        combo_min.set(default_min)
        combo_min.pack(side="left", padx=(0, 10))
        setattr(self, var_min_name, combo_min)

        ctk.CTkLabel(
            combos_frame,
            text="a",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#2C3E50",
        ).pack(side="left", padx=10)

        combo_max = ctk.CTkComboBox(
            combos_frame,
            values=valores_max,
            width=140,
            height=32,
            fg_color="white",
            border_color="#8FA3B0",
        )
        combo_max.set(default_max)
        combo_max.pack(side="left", padx=(10, 0))
        setattr(self, var_max_name, combo_max)

    def confirmar(self):
        self.resultado = {
            "tx_min": float(self.tx_min.get()),
            "tx_max": float(self.tx_max.get()),
            "rx_min": float(self.rx_min.get()),
            "rx_max": float(self.rx_max.get()),
            "rssi24_min": float(self.rssi24_min.get()),
            "rssi24_max": float(self.rssi24_max.get()),
            "rssi50_min": float(self.rssi50_min.get()),
            "rssi50_max": float(self.rssi50_max.get()),
            "busquedas": int(self.busquedas_combo.get()),
        }

        from src.backend.endpoints.conexion import guardarConfig
        guardarConfig(self.resultado, "valores", self.userConsumible)
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
        self.numero_estacion = str(estacion)
        self.modelo = modelo
        app = self.winfo_toplevel()
        self.q = getattr(app, "event_q", None)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=0)

        title_frame = ctk.CTkFrame(self, fg_color="#6B9080", corner_radius=0)
        title_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=0)

        title_frame.grid_columnconfigure(0, weight=0)
        title_frame.grid_columnconfigure(1, weight=1)

        self.menu_superior = MenuSuperiorDesplegable(
            title_frame,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
            align_mode="corner",
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=20, pady=6)

        self.titulo = ctk.CTkLabel(
            title_frame,
            text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        self.titulo.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        buttons_container = ctk.CTkFrame(self, fg_color="transparent")
        buttons_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)

        buttons_container.grid_columnconfigure(0, weight=1)
        buttons_container.grid_rowconfigure(0, weight=1)

        buttons_frame = ctk.CTkFrame(buttons_container, fg_color="transparent")
        buttons_frame.grid(row=0, column=0)

        for col in range(4):
            buttons_frame.grid_columnconfigure(col, weight=0, minsize=250)

        btn1_frame = ctk.CTkFrame(
            buttons_frame, fg_color="#B8B8B8", corner_radius=15, width=250, height=180
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
            height=40,
        )
        btn1.pack(fill="x", padx=15, pady=(0, 20))

        btn2_frame = ctk.CTkFrame(
            buttons_frame, fg_color="#F1B4BB", corner_radius=15, width=250, height=180
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
            height=40,
        )
        btn2.pack(fill="x", padx=15, pady=(0, 20))

        btn3_frame = ctk.CTkFrame(
            buttons_frame, fg_color="#A8DADC", corner_radius=15, width=250, height=180
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
            height=40,
        )
        btn3.pack(fill="x", padx=15, pady=(0, 20))

        btn4_frame = ctk.CTkFrame(
            buttons_frame, fg_color="#F1B4BB", corner_radius=15, width=250, height=180
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
            height=40,
        )
        btn4.pack(fill="x", padx=15, pady=(0, 20))

        self.panel_pruebas = PanelPruebasConexion(self, self.modelo)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        root = self.winfo_toplevel()
        user_id = int(getattr(root, "current_user_id", 0) or 0)
        self.userConsumible = user_id

    def _swap_view(self, view_cls):
        parent = self.master
        try:
            self.destroy()
        except Exception:
            pass

        nueva = view_cls(parent, self.modelo)
        nueva.pack(fill="both", expand=True)

        if hasattr(parent, "dispatcher") and parent.dispatcher:
            parent.dispatcher.set_target(nueva)

    def ir_a_ont_tester(self):
        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView)

    def ir_a_base_diaria(self):
        from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        self._swap_view(EscaneosDiaView)

    def ir_a_base_global(self):
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        pass

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
        root = self.winfo_toplevel()
        user_id = int(getattr(root, "current_user_id", 0) or 0)
        print("El usuario es: " + str(user_id))
        if user_id in (27, 121):
            self._generarBDVista()
        else:
            print("Sin permisos")

    def _generarBDVista(self):
        win = ctk.CTkToplevel(self)
        win.title("Consulta de base de datos")
        win.geometry("900x500")
        win.grab_set()
        win.focus_set()


# =========================================================
#                         TEST
# =========================================================
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER - Vista Principal")
    app.geometry("1400x700")

    try:
        app.iconbitmap(resource_path(APP_ICON_REL))
    except Exception as e:
        print(f"[ICON] No se pudo aplicar icono en app: {e}")

    modelo_placeholder = "HG8145V5"
    view = TesterMainView(app, modelo_placeholder)
    view.pack(fill="both", expand=True)

    app.mainloop()
