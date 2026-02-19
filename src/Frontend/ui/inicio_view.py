# src/Frontend/ui/inicio_view.py
import customtkinter as ctk
import sys
from pathlib import Path
from PIL import Image
import queue

# Para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

# importar helper de conexion
from src.backend.endpoints.conexion import load_default_users
from src.Frontend.telemetry.dispatcher import EventDispatcher
from src.Frontend.theme_manager import ThemeManager  # ✅ Theme persistente


class InicioView(ctk.CTkFrame):
    """
    Pantalla de inicio / login.
    - UI inicio + teclado numérico
    - Botón toggle para cambiar claro/oscuro (persistente vía ThemeManager)
    """

    USERS_MOCK = load_default_users()  # parte de conexion.py

    def __init__(self, parent, modelo=None, viewmodel=None, **kwargs):
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)
        self.viewmodel = viewmodel
        self.modelo = modelo

        # Paleta (default = light, pero apply_theme() la reemplaza)
        self.COL_BG = "#E8F4F8"
        self.COL_VERDE = "#6B9080"
        self.COL_AZUL_SUAVE = "#A8DADC"
        self.COL_AZUL = "#4EA5D9"
        self.COL_AZUL_HOVER = "#3B8CC2"
        self.COL_TEXTO = "#2C3E50"
        self.COL_ERROR = "#C1666B"
        self.COL_OK = "#2E7D32"

        self.usuario_id = None
        self.usuario_nombre = None

        # Para recolorear botones del teclado
        self.keypad_buttons = []

        # Layout base
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ------------------------------
        # Fondo decorativo
        # ------------------------------
        self.bg = ctk.CTkFrame(self, fg_color=self.COL_BG, corner_radius=0)
        self.bg.grid(row=0, column=0, sticky="nsew")

        # "manchas" / formas
        self.deco1 = ctk.CTkFrame(self.bg, fg_color=self.COL_AZUL_SUAVE, corner_radius=140, width=320, height=320)
        self.deco1.place(x=-80, y=-70)

        self.deco2 = ctk.CTkFrame(self.bg, fg_color=self.COL_VERDE, corner_radius=180, width=420, height=420)
        self.deco2.place(relx=1.0, rely=1.0, x=-260, y=-240)

        self.deco3 = ctk.CTkFrame(self.bg, fg_color="#DFF1F2", corner_radius=120, width=240, height=240)
        self.deco3.place(relx=1.0, y=40, x=-180)

        # ------------------------------
        # Tarjeta central (con "sombra")
        # ------------------------------
        self.card_shadow = ctk.CTkFrame(self.bg, fg_color="#BFD3DD", corner_radius=22, width=520, height=520)
        self.card_shadow.place(relx=0.5, rely=0.45, anchor="center", x=6, y=8)

        self.card = ctk.CTkFrame(
            self.bg,
            fg_color="white",
            corner_radius=22,
            border_width=2,
            border_color="#8FA3B0",
            width=520,
            height=520,
        )
        self.card.place(relx=0.5, rely=0.45, anchor="center")

        # Encabezado superior simple sin esquinas redondeadas
        self.header = ctk.CTkFrame(self.card, fg_color=self.COL_VERDE, corner_radius=0, width=520, height=70)
        self.header.place(x=0, y=0, relwidth=1.0)

        self.lbl_title = ctk.CTkLabel(
            self.header,
            text="ONT TESTER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white",
        )
        self.lbl_title.place(relx=0.5, rely=0.5, anchor="center")

        # ✅ Botón toggle tema
        self.btn_theme = ctk.CTkButton(
            self.header,
            text="🌙",
            width=44,
            height=30,
            corner_radius=8,
            fg_color="#2C3E50",
            hover_color="#1f2a36",
            text_color="white",
            command=self._toggle_theme,
        )
        self.btn_theme.place(relx=1.0, rely=0.5, x=-12, anchor="e")

        # ------------------------------
        # Logo centrado
        # ------------------------------
        self.logo_frame = ctk.CTkFrame(
            self.card,
            fg_color="#F7FBFD",
            corner_radius=18,
            border_width=1,
            border_color="#D0DCE3",
            width=210,
            height=210,
        )
        self.logo_frame.place(relx=0.5, y=110, anchor="n")

        self._logo_label = ctk.CTkLabel(self.logo_frame, text="")
        self._logo_label.place(relx=0.5, rely=0.5, anchor="center")
        self._cargar_logo()

        # Texto "bienvenido"
        self.lbl_welcome = ctk.CTkLabel(
            self.card,
            text="BIENVENIDO\nINGRESA TU ID",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COL_TEXTO,
            justify="center",
        )
        self.lbl_welcome.place(relx=0.5, y=330, anchor="center")

        # Input ID
        self.id_var = ctk.StringVar(value="")
        self.id_entry = ctk.CTkEntry(
            self.card,
            textvariable=self.id_var,
            width=320,
            height=44,
            corner_radius=10,
            fg_color="white",
            border_width=2,
            border_color="#2C3E50",
            font=ctk.CTkFont(size=16, weight="bold"),
            justify="center",
        )
        self.id_entry.place(relx=0.5, y=390, anchor="center")
        self.id_entry.focus()

        # Panel numérico
        self._crear_teclado_numerico(self.bg)

        # Mensaje de validación
        self.status_var = ctk.StringVar(value="")
        self.status_label = ctk.CTkLabel(
            self.card,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COL_TEXTO,
        )
        self.status_label.place(relx=0.5, y=435, anchor="center")

        # Botón COMENZAR (inicia deshabilitado)
        self.btn_comenzar = ctk.CTkButton(
            self.card,
            text="COMENZAR",
            width=160,
            height=44,
            corner_radius=10,
            fg_color=self.COL_AZUL,
            hover_color=self.COL_AZUL_HOVER,
            text_color="white",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_comenzar,
            state="disabled",
        )
        self.btn_comenzar.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")

        # Bindings para validar
        self.id_entry.bind("<KeyRelease>", lambda e: self._validar_id())
        self.id_entry.bind("<Return>", lambda e: self._enter_accion())

        # ✅ Aplicar tema actual al arrancar
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            self.apply_theme(root.theme.palette())

    # =========================================================
    #                    THEME / TOGGLE
    # =========================================================
    def _toggle_theme(self):
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            root.theme.toggle()
            if hasattr(root, "refresh_theme"):
                root.refresh_theme()
            else:
                self.apply_theme(root.theme.palette())

    def apply_theme(self, p: dict):
        """Recolorea esta vista según paleta p (ThemeManager.palette())."""

        mode = getattr(getattr(self.winfo_toplevel(), "theme", None), "mode", "light")

        # Actualizar "constantes" internas
        self.COL_BG = p.get("bg", "#E8F4F8")
        self.COL_TEXTO = p.get("text", "#2C3E50")
        self.COL_ERROR = p.get("danger", "#C1666B")
        self.COL_OK = p.get("ok", "#2E7D32")
        self.COL_AZUL = p.get("primary", "#4EA5D9")
        self.COL_AZUL_HOVER = p.get("primary_hover", "#3B8CC2")
        self.COL_VERDE = p.get("header", "#6B9080")
        self.COL_AZUL_SUAVE = p.get("deco1", "#A8DADC")

        # Fondo general
        self.configure(fg_color=self.COL_BG)
        self.bg.configure(fg_color=self.COL_BG)

        # Decoraciones
        self.deco1.configure(fg_color=p.get("deco1", self.COL_AZUL_SUAVE))
        self.deco2.configure(fg_color=p.get("header", self.COL_VERDE))
        self.deco3.configure(fg_color=p.get("deco3", "#DFF1F2"))

        # Card y sombra
        self.card_shadow.configure(fg_color=p.get("card_shadow", "#BFD3DD"))
        self.card.configure(fg_color=p.get("card", "white"), border_color=p.get("border", "#8FA3B0"))

        # Header
        self.header.configure(fg_color=p.get("header", self.COL_VERDE))
        self.lbl_title.configure(text_color="white")

        # Botón toggle (color + icono)
        self.btn_theme.configure(
            text=("☀️" if mode == "dark" else "🌙"),
            fg_color=("#111827" if mode == "dark" else "#2C3E50"),
            hover_color=("#0B1220" if mode == "dark" else "#1f2a36"),
            text_color="white",
        )

        # Logo frame
        self.logo_frame.configure(fg_color=p.get("card", "white"), border_color=p.get("border", "#8FA3B0"))

        # Textos
        self.lbl_welcome.configure(text_color=p.get("text", self.COL_TEXTO))

        # Entry
        self.id_entry.configure(
            fg_color=p.get("entry_bg", "white"),
            border_color=p.get("entry_border", p.get("border", "#8FA3B0")),
            text_color=p.get("text", self.COL_TEXTO),
        )

        # Status label: si está en verde/rojo por validación, no lo pisamos
        cur_color = self.status_label.cget("text_color")
        if cur_color in (None, "", self.COL_TEXTO, p.get("text", self.COL_TEXTO)):
            self.status_label.configure(text_color=p.get("text", self.COL_TEXTO))

        # Botón comenzar
        self.btn_comenzar.configure(
            fg_color=p.get("primary", self.COL_AZUL),
            hover_color=p.get("primary_hover", self.COL_AZUL_HOVER),
            text_color="white",
        )

        # Keypad contenedor
        if hasattr(self, "keypad_shadow"):
            self.keypad_shadow.configure(fg_color=p.get("card_shadow", "#BFD3DD"))
        if hasattr(self, "keypad"):
            self.keypad.configure(fg_color=p.get("card", "white"), border_color=p.get("border", "#8FA3B0"))
        if hasattr(self, "keypad_title"):
            self.keypad_title.configure(text_color=p.get("text", self.COL_TEXTO))

        # Botones del teclado
        for b, meta in getattr(self, "keypad_buttons", []):
            kind = meta.get("kind", "num")
            if kind == "num":
                b.configure(
                    fg_color=p.get("card", "white"),
                    hover_color=p.get("deco3", "#DFF1F2"),
                    text_color=p.get("text", self.COL_TEXTO),
                    border_color=p.get("border", "#8FA3B0"),
                )
            elif kind == "ok":
                b.configure(
                    fg_color=p.get("primary", self.COL_AZUL),
                    hover_color=p.get("primary_hover", self.COL_AZUL_HOVER),
                    text_color="white",
                    border_color=p.get("border", "#8FA3B0"),
                )
            elif kind == "clear":
                b.configure(
                    fg_color=("#3a1f22" if mode == "dark" else "#FCEDEE"),
                    hover_color=("#512a2f" if mode == "dark" else "#F9D7DA"),
                    text_color=p.get("danger", self.COL_ERROR),
                    border_color=p.get("border", "#8FA3B0"),
                )
            elif kind == "back":
                b.configure(
                    fg_color=p.get("deco3", "#DFF1F2"),
                    hover_color=p.get("deco1", self.COL_AZUL_SUAVE),
                    text_color=p.get("text", self.COL_TEXTO),
                    border_color=p.get("border", "#8FA3B0"),
                )

    # =========================================================
    #                    PANEL NUMÉRICO
    # =========================================================
    def _crear_teclado_numerico(self, parent_bg):
        """Crea un panel numérico para ingresar el ID con mouse."""
        self.PAD_MAX_LEN = 12  # ajusta si tu ID tiene otra longitud

        # Sombra
        self.keypad_shadow = ctk.CTkFrame(
            parent_bg, fg_color="#BFD3DD", corner_radius=22, width=220, height=320
        )
        self.keypad_shadow.place(relx=0.5, rely=0.45, anchor="w", x=280, y=8)

        # Panel
        self.keypad = ctk.CTkFrame(
            parent_bg,
            fg_color="white",
            corner_radius=22,
            border_width=2,
            border_color="#8FA3B0",
            width=220,
            height=320,
        )
        self.keypad.place(relx=0.5, rely=0.45, anchor="w", x=280, y=0)

        self.keypad_title = ctk.CTkLabel(
            self.keypad,
            text="TECLADO",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COL_TEXTO,
        )
        self.keypad_title.grid(row=0, column=0, columnspan=3, pady=(14, 10))

        # Grid uniforme
        for r in range(1, 6):
            self.keypad.grid_rowconfigure(r, weight=1)
        for c in range(3):
            self.keypad.grid_columnconfigure(c, weight=1)

        def mkbtn(txt, cmd, r, c, colspan=1, fg="#F7FBFD", hover="#EAF4FA", tc=None, kind="num"):
            b = ctk.CTkButton(
                self.keypad,
                text=txt,
                command=cmd,
                width=60,
                height=44,
                corner_radius=10,
                fg_color=fg,
                hover_color=hover,
                text_color=(tc if tc else self.COL_TEXTO),
                font=ctk.CTkFont(size=14, weight="bold"),
                border_width=1,
                border_color="#D0DCE3",
            )
            b.grid(row=r, column=c, columnspan=colspan, padx=8, pady=6, sticky="nsew")
            self.keypad_buttons.append((b, {"kind": kind}))
            return b

        nums = [
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2),
        ]
        for d, r, c in nums:
            mkbtn(d, lambda x=d: self._pad_append(x), r, c, kind="num")

        mkbtn("C", self._pad_clear, 4, 0, fg="#FCEDEE", hover="#F9D7DA", tc=self.COL_ERROR, kind="clear")
        mkbtn("0", lambda: self._pad_append("0"), 4, 1, kind="num")
        mkbtn("⌫", self._pad_backspace, 4, 2, fg="#EAF4FA", hover="#DCECF8", tc=self.COL_TEXTO, kind="back")

        mkbtn("OK", self._pad_ok, 5, 0, colspan=3, fg=self.COL_AZUL, hover=self.COL_AZUL_HOVER, tc="white", kind="ok")

    def _pad_append(self, ch: str):
        cur = self.id_var.get()
        if len(cur) >= getattr(self, "PAD_MAX_LEN", 12):
            return
        self.id_var.set(cur + ch)
        self._validar_id()
        self.id_entry.focus()
        try:
            self.id_entry.icursor("end")
        except Exception:
            pass

    def _pad_backspace(self):
        cur = self.id_var.get()
        if not cur:
            return
        self.id_var.set(cur[:-1])
        self._validar_id()
        self.id_entry.focus()
        try:
            self.id_entry.icursor("end")
        except Exception:
            pass

    def _pad_clear(self):
        self.id_var.set("")
        self._validar_id()
        self.id_entry.focus()
        try:
            self.id_entry.icursor("end")
        except Exception:
            pass

    def _pad_ok(self):
        self._enter_accion()

    # =========================================================
    #                    LOGO
    # =========================================================
    def _cargar_logo(self):
        """Carga logo desde assets/icons/logo_tester.png (si existe)."""
        try:
            assets_dir = Path(__file__).parent.parent / "assets" / "icons"
            logo_path = assets_dir / "logo_tester.png"
            img = Image.open(logo_path)
            self.logo_image = ctk.CTkImage(light_image=img, dark_image=img, size=(150, 150))
            self._logo_label.configure(image=self.logo_image)
        except Exception:
            self._logo_label.configure(text="")

    # =========================================================
    #                VALIDACIÓN DE ID
    # =========================================================
    def _lookup_user(self, id_str: str):
        """Devuelve (ok: bool, nombre: str|None)"""
        try:
            id_int = int(id_str)
        except Exception:
            return (False, None)

        if self.viewmodel:
            if hasattr(self.viewmodel, "obtener_usuario_por_id"):
                try:
                    nombre = self.viewmodel.obtener_usuario_por_id(id_int)
                    return (bool(nombre), nombre)
                except Exception:
                    pass

            if hasattr(self.viewmodel, "validar_id"):
                try:
                    ok, nombre = self.viewmodel.validar_id(id_int)
                    return (bool(ok), nombre)
                except Exception:
                    pass

        nombre = self.USERS_MOCK.get(id_int)
        return (nombre is not None, nombre)

    def _validar_id(self):
        text = self.id_var.get().strip()

        if not text:
            self.status_var.set("")
            self.status_label.configure(text_color=self.COL_TEXTO)
            self.btn_comenzar.configure(state="disabled")
            self.usuario_id = None
            self.usuario_nombre = None
            return

        ok, nombre = self._lookup_user(text)

        if ok:
            self.usuario_id = text
            self.usuario_nombre = nombre or ""
            self.status_var.set(f"Bienvenido, {self.usuario_nombre}")
            self.status_label.configure(text_color=self.COL_OK)
            self.btn_comenzar.configure(state="normal")
        else:
            self.usuario_id = None
            self.usuario_nombre = None
            self.status_var.set("ID no válido")
            self.status_label.configure(text_color=self.COL_ERROR)
            self.btn_comenzar.configure(state="disabled")

    def _enter_accion(self):
        self._validar_id()
        if self.btn_comenzar.cget("state") == "normal":
            self._on_comenzar()

    # =========================================================
    #                ACCIÓN COMENZAR
    # =========================================================
    def _swap_view(self, view_cls, **init_kwargs):
        parent = self.master
        # ✅ tomar root ANTES de destruir (self puede quedar inválido)
        root = parent.winfo_toplevel()

        try:
            self.destroy()
        except Exception:
            pass

        # ✅ compatibilidad con constructores de otras vistas
        nueva = None
        try:
            # patrón común de tus vistas: (parent, modelo, viewmodel=None)
            nueva = view_cls(parent, self.modelo, **init_kwargs)
        except TypeError:
            try:
                nueva = view_cls(parent, modelo=self.modelo, **init_kwargs)
            except TypeError:
                nueva = view_cls(parent, **init_kwargs)

        nueva.pack(fill="both", expand=True)

        # El dispatcher del parent ahora apunta a la nueva vista
        if hasattr(parent, "dispatcher") and parent.dispatcher:
            parent.dispatcher.set_target(nueva)

        # ✅ si la nueva vista soporta tema, aplícalo (usa root, no self)
        if hasattr(root, "theme") and hasattr(nueva, "apply_theme"):
            try:
                nueva.apply_theme(root.theme.palette())
            except Exception:
                pass

    def _on_comenzar(self):
        if not self.usuario_id:
            return

        print(f"[LOGIN] ID válido: {self.usuario_id} -> {self.usuario_nombre}")

        # Guardar sesión en la ventana root
        root = self.winfo_toplevel()
        root.current_user_id = str(self.usuario_id)
        root.current_user_name = str(self.usuario_nombre)

        # Almacenar en user_station
        from src.backend.endpoints.conexion import inicializaruserStation
        inicializaruserStation(int(self.usuario_id))

        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView, viewmodel=self.viewmodel)


# =========================================================
#                      RUN APP
# =========================================================
def run_app():
    # ✅ Theme manager global + persistencia
    theme = ThemeManager(config_path="config_ui.json")
    theme.apply()

    app = ctk.CTk()
    app.theme = theme

    def refresh_theme():
        p = app.theme.palette()
        try:
            app.configure(fg_color=p["bg"])
        except Exception:
            pass

        # refrescar vista activa (dispatcher target)
        view = getattr(app.dispatcher, "_target", None)
        if view and hasattr(view, "apply_theme"):
            try:
                view.apply_theme(p)
            except Exception:
                pass

    app.refresh_theme = refresh_theme

    app.title("ONT TESTER - Inicio")
    app.geometry("1200x650")
    app.minsize(900, 550)

    # Crear dispatcher + queue
    app.event_q = queue.Queue()
    app.aws_bridge = None
    app.dispatcher = EventDispatcher(
        root=app,
        event_q=app.event_q,
        aws_bridge=app.aws_bridge,
        interval_ms=20,
        max_per_tick=200,
    )
    app.dispatcher.start()

    view = InicioView(app)
    view.pack(fill="both", expand=True)

    # ✅ aplicar tema al primer render
    try:
        view.apply_theme(app.theme.palette())
    except Exception:
        pass

    icon_path = Path(__file__).resolve().parent.parent / "assets" / "icons" / "ont.ico"
    try:
        app.iconbitmap(str(icon_path))
    except Exception:
        pass

    # Poner target en el dispatcher
    app.dispatcher.set_target(view)

    def on_close():
        try:
            app.dispatcher.stop()
        except Exception:
            pass
        try:
            if app.aws_bridge:
                app.aws_bridge.stop()
        except Exception:
            pass
        try:
            from src.backend.sua_client.dao import clear_user_station
            clear_user_station()
        except Exception:
            pass
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_close)
    app.mainloop()


if __name__ == "__main__":
    run_app()
