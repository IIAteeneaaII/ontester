# src/Frontend/ui/propiedades_view.py
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


APP_ICON_REL = "src/Frontend/assets/icons/ont.ico"


# =========================================================
#                     THEME HELPERS
# =========================================================
def _get_app_root(widget):
    # Si el widget ya guardó app_root, úsalo
    if hasattr(widget, "app_root") and widget.app_root is not None:
        return widget.app_root

    # Si no, intenta subir por master
    r = getattr(widget, "master", None)
    while r is not None:
        if hasattr(r, "theme"):
            return r
        r = getattr(r, "master", None)

    # fallback final
    return widget


def _palette(widget) -> dict:
    app_root = _get_app_root(widget)

    if hasattr(app_root, "theme"):
        try:
            return app_root.theme.palette()
        except Exception:
            pass

    # fallback claro
    return {
        "bg": "#E8F4F8",
        "panel": "#C8D8E4",
        "header": "#6B9080",
        "text": "#2C3E50",
        "muted": "#37474F",
        "border": "#8FA3B0",
        "entry_bg": "white",
        "primary": "#6B9080",
        "primary_hover": "#5A7A6A",
        "danger": "#A5343A",
        "danger_hover": "#A4161A",
        "primary2": "#457B9D",
        "primary2_hover": "#1D3557",
    }


def _mode(widget) -> str:
    app_root = _get_app_root(widget)
    return getattr(getattr(app_root, "theme", None), "mode", "light")



def _center_window(win: ctk.CTkToplevel, w: int, h: int):
    """Centra el Toplevel en la pantalla."""
    try:
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = int((sw - w) / 2)
        y = int((sh - h) / 2)
        win.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass


# =========================================================
#                         DIALOG BASE
# =========================================================
class BaseDialog(ctk.CTkToplevel):
    """
    Base para TODOS los diálogos:
    - icono
    - modal seguro
    - guarda app_root real (ventana principal)
    - aplica theme real al abrir
    """

    def __init__(self, parent, *args, **kwargs):
        # master REAL (tu ventana principal CTk)
        master = parent.winfo_toplevel() if hasattr(parent, "winfo_toplevel") else parent
        super().__init__(master, *args, **kwargs)

        # ✅ guarda referencia al root real
        self.app_root = master

        self._set_logo_icon()

        try:
            self.transient(master)
        except Exception:
            pass

        self.after(10, self._make_modal_safe)

    def _set_logo_icon(self):
        ico_path = resource_path(APP_ICON_REL)

        def apply_icon():
            try:
                self.wm_iconbitmap(ico_path)
            except Exception as e:
                print(f"[ICON] wm_iconbitmap dialog falló: {e}")

        self.after(0, apply_icon)

    def _make_modal_safe(self):
        try: self.lift()
        except Exception: pass
        try: self.focus_force()
        except Exception: pass
        try: self.grab_set()
        except Exception: pass

        # ✅ aplicar tema usando app_root REAL (NO winfo_toplevel())
        try:
            p = _palette(self)
            if hasattr(self, "apply_theme"):
                self.apply_theme(p)
        except Exception:
            pass

        # ✅ aplicar tema actual al abrir
        try:
            root = self.winfo_toplevel()
            if hasattr(root, "theme") and hasattr(self, "apply_theme"):
                self.apply_theme(root.theme.palette())
            else:
                # fallback
                if hasattr(self, "apply_theme"):
                    self.apply_theme(_palette(self))
        except Exception:
            pass


# =========================================================
#                         DIALOGS
# =========================================================
class CambiarEstacionDialog(BaseDialog):
    """
    Ventana emergente para cambiar el número de estación.
    """

    def __init__(self, parent, estacion_actual, userConsumible):
        super().__init__(parent)
        self.nuevo_numero = None
        self.userConsumible = userConsumible

        self.title("Cambiar Estación")
        self.resizable(False, False)
        _center_window(self, 420, 220)

        self.grid_columnconfigure(0, weight=1)

        self.titulo_label = ctk.CTkLabel(
            self,
            text="Ingrese el número de estación\na donde se hará el cambio",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.titulo_label.grid(row=0, column=0, pady=(20, 10), padx=20)

        self.entry_estacion = ctk.CTkEntry(
            self,
            width=150,
            height=40,
            font=ctk.CTkFont(size=16),
            justify="center",
        )
        self.entry_estacion.grid(row=1, column=0, pady=10)
        self.entry_estacion.insert(0, estacion_actual)
        self.entry_estacion.focus()
        self.entry_estacion.bind("<Return>", lambda e: self.confirmar())

        self.botones_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.botones_frame.grid(row=2, column=0, pady=20, padx=20)

        self.btn_aceptar = ctk.CTkButton(
            self.botones_frame,
            text="ACEPTAR",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=140,
            height=38,
        )
        self.btn_aceptar.pack(side="left", padx=8)

        self.btn_cancelar = ctk.CTkButton(
            self.botones_frame,
            text="CANCELAR",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=140,
            height=38,
        )
        self.btn_cancelar.pack(side="left", padx=8)

        self.cargarEstacion()
        self.apply_theme(_palette(self))

    def apply_theme(self, p: dict):
        mode = _mode(self)

        bg = p.get("bg", "#E8F4F8")
        text = p.get("text", "#2C3E50")
        muted = p.get("muted", "#37474F")
        border = p.get("border", "#8FA3B0")
        entry_bg = p.get("entry_bg", "white")
        primary = p.get("primary", "#6B9080")
        primary_hover = p.get("primary_hover", "#5A7A6A")
        danger = p.get("danger", "#C1666B")
        danger_hover = p.get("danger_hover", "#A4161A")

        if mode == "dark":
            bg = p.get("panel", "#111827")
            entry_bg = "#0F172A"
            text = "#E5E7EB"
            muted = "#9CA3AF"
            border = "#243244"

        self.configure(fg_color=bg)
        
        self.titulo_label.configure(text_color=text)

        self.entry_estacion.configure(
            fg_color=entry_bg,
            border_color=border,
            text_color=text,
            placeholder_text_color=muted,
        )

        self.botones_frame.configure(fg_color=bg)
        self.btn_aceptar.configure(
            fg_color=primary, hover_color=primary_hover, text_color="white"
        )
        self.btn_cancelar.configure(
            fg_color=danger, hover_color=danger_hover, text_color="white"
        )

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

        guardarConfig(valor, "estacion", self.userConsumible)

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
        self.userConsumible = userConsumible

        self.title("Configuración de Etiqueta")
        self.resizable(False, False)
        _center_window(self, 520, 280)

        self.titulo_label = ctk.CTkLabel(
            self,
            text="CONFIGURACIÓN DE ETIQUETA",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.titulo_label.pack(pady=(20, 20), padx=20)

        self.opciones_label = ctk.CTkLabel(
            self,
            text="MODO DE ETIQUETA DE FIBERHOME",
            font=ctk.CTkFont(size=13, weight="bold"),
        )
        self.opciones_label.pack(pady=(0, 15))

        self.etiqueta_var = ctk.StringVar(value="unica")

        self.radio_unica = ctk.CTkRadioButton(
            self,
            text="ETIQUETA ÚNICA",
            variable=self.etiqueta_var,
            value="unica",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.radio_unica.pack(pady=6, padx=40, anchor="w")

        self.radio_doble = ctk.CTkRadioButton(
            self,
            text="ETIQUETA DOBLE",
            variable=self.etiqueta_var,
            value="doble",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.radio_doble.pack(pady=6, padx=40, anchor="w")

        self.btn_aceptar = ctk.CTkButton(
            self,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=160,
            height=38,
        )
        self.btn_aceptar.pack(pady=(18, 15))

        self.cargarEtiqueta()
        self.apply_theme(_palette(self))

    def apply_theme(self, p: dict):
        mode = _mode(self)

        bg = p.get("bg", "#E8F4F8")
        text = p.get("text", "#2C3E50")
        border = p.get("border", "#8FA3B0")
        primary = p.get("primary", "#6B9080")
        primary_hover = p.get("primary_hover", "#5A7A6A")
        radio_on = p.get("primary_hover", "#3B8CC2")

        if mode == "dark":
            bg = p.get("panel", "#111827")
            text = "#E5E7EB"
            border = "#243244"

        self.configure(fg_color=bg)
        self.titulo_label.configure(text_color=text)
        self.opciones_label.configure(text_color=text)

        self.radio_unica.configure(
            text_color=text,
            border_color=border,
            fg_color=radio_on,
            hover_color=radio_on,
        )
        self.radio_doble.configure(
            text_color=text,
            border_color=border,
            fg_color=radio_on,
            hover_color=radio_on,
        )

        self.btn_aceptar.configure(
            fg_color=primary, hover_color=primary_hover, text_color="white"
        )

    def cargarEtiqueta(self):
        from src.backend.endpoints.conexion import cargarConfig

        config = cargarConfig()
        general = config.get("general", {}) or {}
        etiqueta = general.get("etiqueta")
        etiqueta = "unica" if etiqueta == 1 else "doble"
        self.etiqueta_var.set(etiqueta)

    def confirmar(self):
        self.resultado = self.etiqueta_var.get()
        etiq = 1 if self.resultado == "unica" else 2

        from src.backend.endpoints.conexion import guardarConfig
        guardarConfig(etiq, "etiqueta", self.userConsumible)
        self.destroy()

    def cancelar(self):
        self.resultado = None
        self.destroy()


class ModificarParametrosDialog(BaseDialog):
    """
    Ventana emergente para configurar los parámetros del ONT TESTER.
    - Canvas + Scrollbar
    - área scrollable limitada (MAX_SCROLL_HEIGHT)
    """

    MAX_SCROLL_HEIGHT = 520
    MIN_DIALOG_W = 560
    MIN_DIALOG_H = 520

    def __init__(self, parent, userConsumible):
        super().__init__(parent)

        self.resultado = None
        self.userConsumible = userConsumible
        self._range_labels = []  # (titulo_label, a_label)

        self.title("Parámetros de ONT Tester")
        self.minsize(self.MIN_DIALOG_W, self.MIN_DIALOG_H)
        self.resizable(True, True)
        _center_window(self, 650, 760)

        # layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0)
        self.grid_rowconfigure(1, weight=1)

        self.titulo_label = ctk.CTkLabel(
            self,
            text="PARÁMETROS DE ONT TESTER",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        self.titulo_label.grid(row=0, column=0, pady=(20, 12), padx=20, sticky="n")

        self.scroll_host = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0)
        self.scroll_host.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 18))
        self.scroll_host.grid_columnconfigure(0, weight=1)
        self.scroll_host.grid_columnconfigure(1, weight=0)
        self.scroll_host.grid_rowconfigure(0, weight=1)

        # Canvas tk + Scrollbar
        self._canvas = tk.Canvas(self.scroll_host, highlightthickness=0, bd=0)
        self._canvas.grid(row=0, column=0, sticky="nsew")

        self._vscroll = ctk.CTkScrollbar(
            self.scroll_host, orientation="vertical", command=self._canvas.yview
        )
        self._vscroll.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self._canvas.configure(yscrollcommand=self._vscroll.set)

        # contenido
        self.content = ctk.CTkFrame(self._canvas, fg_color="transparent", corner_radius=0)
        self._content_window = self._canvas.create_window((0, 0), window=self.content, anchor="nw")

        def _on_canvas_configure(event):
            self._canvas.itemconfig(self._content_window, width=event.width)

        self._canvas.bind("<Configure>", _on_canvas_configure)

        def _on_content_configure(_event=None):
            self._canvas.configure(scrollregion=self._canvas.bbox("all"))

        self.content.bind("<Configure>", _on_content_configure)

        def _limit_scroll_area(_event=None):
            try:
                total_h = self.winfo_height()
                top_used = 20 + 12 + 30
                available = max(260, total_h - top_used)
                target = min(self.MAX_SCROLL_HEIGHT, available)
                self._canvas.configure(height=target)
            except Exception:
                pass

        self.bind("<Configure>", _limit_scroll_area)
        self.after(80, _limit_scroll_area)

        self._bind_mousewheel()

        # ---------------- CONTENIDO ----------------
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
            default_min="-19.00",
            default_max="-13.00",
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

        self.busquedas_frame = ctk.CTkFrame(self.content, fg_color="transparent", corner_radius=0)
        self.busquedas_frame.pack(fill="x", pady=(20, 10))

        self.busquedas_label = ctk.CTkLabel(
            self.busquedas_frame,
            text="PORCENTAJE DE POTENCIA DE SEÑALES WIFI",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.busquedas_label.pack(anchor="w", pady=(0, 10))

        self.busquedas_combo = ctk.CTkComboBox(
            self.busquedas_frame,
            values=["50", "60", "70", "80", "90", "100"],
            width=240,
            height=32,
        )
        self.busquedas_combo.set("60")
        self.busquedas_combo.pack(anchor="w", pady=(0, 10))

        self.botones_frame = ctk.CTkFrame(self.content, fg_color="transparent", corner_radius=0)
        self.botones_frame.pack(fill="x", pady=(30, 10))
        self.botones_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.btn_aceptar = ctk.CTkButton(
            self.botones_frame,
            text="Aceptar",
            command=self.confirmar,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=35,
        )
        self.btn_aceptar.grid(row=0, column=0, padx=8, pady=(0, 10), sticky="e")

        self.btn_restaurar = ctk.CTkButton(
            self.botones_frame,
            text="Restaurar",
            command=self.restaurar,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=35,
        )
        self.btn_restaurar.grid(row=0, column=1, padx=8, pady=(0, 10))

        self.btn_cancelar = ctk.CTkButton(
            self.botones_frame,
            text="Cancelar",
            command=self.cancelar,
            font=ctk.CTkFont(size=12, weight="bold"),
            width=120,
            height=35,
        )
        self.btn_cancelar.grid(row=0, column=2, padx=8, pady=(0, 10), sticky="w")

        self._bottom_spacer = ctk.CTkFrame(self.content, height=60, fg_color="transparent")
        self._bottom_spacer.pack(fill="x")


        self.cargar_desdeJSON()
        self.after(120, lambda: self._canvas.configure(scrollregion=self._canvas.bbox("all")))

        self.apply_theme(_palette(self))

    def apply_theme(self, p: dict):
        mode = _mode(self)

        bg = p.get("bg", "#E8F4F8")
        text = p.get("text", "#2C3E50")
        muted = p.get("muted", "#37474F")
        border = p.get("border", "#8FA3B0")
        entry_bg = p.get("entry_bg", "white")
        primary = p.get("primary", "#6B9080")
        primary_hover = p.get("primary_hover", "#5A7A6A")
        danger = p.get("danger", "#C1666B")
        danger_hover = p.get("danger_hover", "#A4161A")
        primary2 = p.get("primary2", "#457B9D")
        primary2_hover = p.get("primary2_hover", "#1D3557")

        if mode == "dark":
            bg = p.get("panel", "#111827")
            text = "#E5E7EB"
            muted = "#9CA3AF"
            border = "#243244"
            entry_bg = "#0F172A"

        self.configure(fg_color=bg)
        self.titulo_label.configure(text_color=text)

        for fr in (self.scroll_host, self.content, self.busquedas_frame, self.botones_frame):
            try:
                fr.configure(fg_color=bg)
            except Exception:
                pass
            
        # ✅ tk.Canvas background (cubrir TODO, incluyendo bordes)
            try:
                self._canvas.configure(
                    background=bg,
                    bg=bg,
                    highlightthickness=0,
                    bd=0,
                    relief="flat"
                )
                # a veces Tk deja el "highlightbackground" en blanco:
                self._canvas.config(highlightbackground=bg)
            except Exception:
                pass

            # ✅ pintar el spacer final para que NO asome blanco
            try:
                if hasattr(self, "_bottom_spacer"):
                    self._bottom_spacer.configure(fg_color=bg)
            except Exception:
                pass


        self.busquedas_label.configure(text_color=text)

        combos = []
        for name in (
            "tx_min", "tx_max",
            "rx_min", "rx_max",
            "rssi24_min", "rssi24_max",
            "rssi50_min", "rssi50_max",
        ):
            cb = getattr(self, name, None)
            if cb:
                combos.append(cb)
        combos.append(self.busquedas_combo)

        for cb in combos:
            try:
                cb.configure(
                    fg_color=entry_bg,
                    border_color=border,
                    text_color=text,
                    button_color=primary,
                    button_hover_color=primary_hover,
                )
            except Exception:
                pass

        self.btn_aceptar.configure(fg_color=primary2, hover_color=primary2_hover, text_color="white")
        self.btn_restaurar.configure(fg_color=primary, hover_color=primary_hover, text_color="white")
        self.btn_cancelar.configure(fg_color=danger, hover_color=danger_hover, text_color="white")

        # D) Fuerza scrollregion al final (evita huecos blancos al fondo)
        try:
            self.after(10, lambda: self._canvas.configure(scrollregion=self._canvas.bbox("all")))
        except Exception:
            pass


    def _bind_mousewheel(self):
        def _on_mousewheel(event):
            try:
                self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass

        self._canvas.bind("<MouseWheel>", _on_mousewheel)
        self.bind("<MouseWheel>", _on_mousewheel)

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
        seccion_frame = ctk.CTkFrame(parent, fg_color="transparent", corner_radius=0)
        seccion_frame.pack(fill="x", pady=(15, 10))

        title_lbl = ctk.CTkLabel(
            seccion_frame,
            text=titulo,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        title_lbl.pack(anchor="w", pady=(0, 10))

        combos_frame = ctk.CTkFrame(seccion_frame, fg_color="transparent", corner_radius=0)
        combos_frame.pack(anchor="w")

        combo_min = ctk.CTkComboBox(
            combos_frame,
            values=valores_min,
            width=140,
            height=32,
        )
        combo_min.set(default_min)
        combo_min.pack(side="left", padx=(0, 10))
        setattr(self, var_min_name, combo_min)

        a_lbl = ctk.CTkLabel(
            combos_frame,
            text="a",
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        a_lbl.pack(side="left", padx=10)

        combo_max = ctk.CTkComboBox(
            combos_frame,
            values=valores_max,
            width=140,
            height=32,
        )
        combo_max.set(default_max)
        combo_max.pack(side="left", padx=(10, 0))
        setattr(self, var_max_name, combo_max)

        self._range_labels.append((title_lbl, a_lbl))

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


# =========================================================
#                         VIEW PRINCIPAL
# =========================================================
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

        self.titulo = ctk.CTkLabel(
            self.title_frame,
            text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="white",
        )
        self.titulo.grid(row=0, column=1, sticky="w", padx=20, pady=10)

        self.buttons_container = ctk.CTkFrame(self, fg_color="#E8F4F8")
        self.buttons_container.grid(row=1, column=0, sticky="nsew", padx=20, pady=20)
        self.buttons_container.grid_columnconfigure(0, weight=1)
        self.buttons_container.grid_rowconfigure(0, weight=1)

        self.buttons_frame = ctk.CTkFrame(self.buttons_container, fg_color="#E8F4F8")
        self.buttons_frame.grid(row=0, column=0)

        for col in range(4):
            self.buttons_frame.grid_columnconfigure(col, weight=0, minsize=250)

        self.btn1_frame = ctk.CTkFrame(self.buttons_frame, fg_color="#B8B8B8", corner_radius=15, width=250, height=180)
        self.btn1_frame.grid(row=0, column=0, padx=15, pady=10, sticky="nsew")
        self.btn1_frame.grid_propagate(False)
        ctk.CTkLabel(self.btn1_frame, text="👤", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))
        self.btn1 = ctk.CTkButton(
            self.btn1_frame,
            text="CAMBIAR ESTACIÓN",
            command=self.on_cambiar_estacion,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#A0A0A0",
            text_color="#2C3E50",
            height=40,
        )
        self.btn1.pack(fill="x", padx=15, pady=(0, 20))

        self.btn2_frame = ctk.CTkFrame(self.buttons_frame, fg_color="#F1B4BB", corner_radius=15, width=250, height=180)
        self.btn2_frame.grid(row=0, column=1, padx=15, pady=10, sticky="nsew")
        self.btn2_frame.grid_propagate(False)
        ctk.CTkLabel(self.btn2_frame, text="🏷️", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))
        self.btn2 = ctk.CTkButton(
            self.btn2_frame,
            text="MODIFICAR ETIQUETADO",
            command=self.on_modificar_etiquetado,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            height=40,
        )
        self.btn2.pack(fill="x", padx=15, pady=(0, 20))

        self.btn3_frame = ctk.CTkFrame(self.buttons_frame, fg_color="#A8DADC", corner_radius=15, width=250, height=180)
        self.btn3_frame.grid(row=0, column=2, padx=15, pady=10, sticky="nsew")
        self.btn3_frame.grid_propagate(False)
        ctk.CTkLabel(self.btn3_frame, text="⚙️", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))
        self.btn3 = ctk.CTkButton(
            self.btn3_frame,
            text="MODIFICAR PARÁMETROS",
            command=self.on_modificar_parametros,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            height=40,
        )
        self.btn3.pack(fill="x", padx=15, pady=(0, 20))

        self.btn4_frame = ctk.CTkFrame(self.buttons_frame, fg_color="#F1B4BB", corner_radius=15, width=250, height=180)
        self.btn4_frame.grid(row=0, column=3, padx=15, pady=10, sticky="nsew")
        self.btn4_frame.grid_propagate(False)
        ctk.CTkLabel(self.btn4_frame, text="🔧", font=ctk.CTkFont(size=50)).pack(pady=(20, 10))
        self.btn4 = ctk.CTkButton(
            self.btn4_frame,
            text="PRUEBA",
            command=self.on_prueba,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="transparent",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            height=40,
        )
        self.btn4.pack(fill="x", padx=15, pady=(0, 20))

        self.panel_pruebas = PanelPruebasConexion(self, self.modelo)
        self.panel_pruebas.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))

        root = self.winfo_toplevel()
        user_id = int(getattr(root, "current_user_id", 0) or 0)
        self.userConsumible = user_id

        self.apply_theme(_palette(self))

    def apply_theme(self, p: dict):
        bg = p.get("bg", "#E8F4F8")
        header = p.get("header", "#6B9080")

        root = self.winfo_toplevel()
        try:
            root.configure(fg_color=bg)
        except Exception:
            pass
        try:
            self.master.configure(fg_color=bg)
        except Exception:
            pass

        self.configure(fg_color=bg)
        self.title_frame.configure(fg_color=header)
        self.titulo.configure(text_color="white")

        try:
            if hasattr(self.menu_superior, "apply_theme"):
                self.menu_superior.apply_theme(p)
        except Exception:
            pass

        # cards
        if _mode(self) == "dark":
            card1 = "#1F2937"
            card2 = "#111827"
            card3 = "#0F172A"
            btn_txt = "#E5E7EB"
            hover1 = "#334155"
            hover2 = "#1F2937"
        else:
            card1 = "#B8B8B8"
            card2 = "#A4C4D3"
            card3 = "#A8DADC"
            btn_txt = "#2C3E50"
            hover1 = "#728F9B"
            hover2 = "#AEDFDF"

        self.buttons_container.configure(fg_color=bg)
        self.buttons_frame.configure(fg_color=bg)
        self.btn1_frame.configure(fg_color=card2)
        self.btn2_frame.configure(fg_color=card2)
        self.btn3_frame.configure(fg_color=card2)
        self.btn4_frame.configure(fg_color=card2)

        self.btn1.configure(text_color=btn_txt, hover_color=hover1)
        self.btn2.configure(text_color=btn_txt, hover_color=hover1)
        self.btn3.configure(text_color=btn_txt, hover_color=hover1)
        self.btn4.configure(text_color=btn_txt, hover_color=hover1)

        try:
            if hasattr(self.panel_pruebas, "apply_theme"):
                self.panel_pruebas.apply_theme(p)
        except Exception:
            pass

    # =========================================================
    #                NAVEGACIÓN
    # =========================================================
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

        root = parent.winfo_toplevel()
        if hasattr(root, "theme"):
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
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        pass

    # =========================================================
    #                     ACCIONES
    # =========================================================
    def on_cambiar_estacion(self):
        dialog = CambiarEstacionDialog(self, self.numero_estacion, self.userConsumible)
        self.wait_window(dialog)

        if dialog.nuevo_numero is not None:
            self.numero_estacion = dialog.nuevo_numero
            self.actualizar_titulo()

    def actualizar_titulo(self):
        self.titulo.configure(text=f"ONT TESTER - REPARANDO EN ESTACIÓN {self.numero_estacion}")

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
