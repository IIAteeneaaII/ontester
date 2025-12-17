import customtkinter as ctk
import sys
from pathlib import Path
from PIL import Image
# Importar la queue
import queue
#importar helper de conexion
from src.backend.endpoints.conexion import *
# Para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))


class InicioView(ctk.CTkFrame):
    """
    Pantalla de inicio / login.
    - Logo centrado
    - Input ID
    - Validación: Bienvenido + nombre / ID no válido
    - Botón COMENZAR (se habilita solo con ID válido)

    Hook opcional:
    - Si pasas viewmodel con método:
        * obtener_usuario_por_id(id_str) -> str|None
      o
        * validar_id(id_str) -> (bool, str|None)
    - Si no, usa un diccionario local (USERS_MOCK).
    """
    # --- Mock local (cámbialo por tus IDs reales o conecta a tu viewmodel) ---
    USERS_MOCK = load_default_users() # parte de conexion.py
    # USERS_MOCK = {
    #     "09": "Ram",
    #     "10": "Alex",
    #     "11": "Karen",
    #     "12": "Luis",
    #     "99": "Admin",
    # }

    def __init__(self, parent, viewmodel=None, **kwargs):
        # Crear el parámetro de la queue
        self.bus_q = queue.Queue()
        super().__init__(parent, fg_color="#E8F4F8", **kwargs)
        self.viewmodel = viewmodel

        # Paleta (misma línea que has usado)
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

        # Layout base
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # ------------------------------
        # Fondo decorativo
        # ------------------------------
        bg = ctk.CTkFrame(self, fg_color=self.COL_BG)
        bg.grid(row=0, column=0, sticky="nsew")

        # "manchas" / formas con esquinas redondeadas
        deco1 = ctk.CTkFrame(bg, fg_color=self.COL_AZUL_SUAVE, corner_radius=140, width=320, height=320)
        deco1.place(x=-80, y=-70)

        deco2 = ctk.CTkFrame(bg, fg_color=self.COL_VERDE, corner_radius=180, width=420, height=420)
        deco2.place(relx=1.0, rely=1.0, x=-260, y=-240)

        deco3 = ctk.CTkFrame(bg, fg_color="#DFF1F2", corner_radius=120, width=240, height=240)
        deco3.place(relx=1.0, y=40, x=-180)

        # ------------------------------
        # Tarjeta central (con "sombra")
        # ------------------------------
        card_shadow = ctk.CTkFrame(bg, fg_color="#BFD3DD", corner_radius=22, width=520, height=520)
        card_shadow.place(relx=0.5, rely=0.45, anchor="center", x=6, y=8)

        card = ctk.CTkFrame(
            bg,
            fg_color="white",
            corner_radius=22,
            border_width=2,
            border_color="#8FA3B0",
            width=520,
            height=520
        )
        card.place(relx=0.5, rely=0.45, anchor="center")

        # Encabezado superior simple sin esquinas redondeadas
        header = ctk.CTkFrame(card, fg_color=self.COL_VERDE, corner_radius=0, width=520, height=70)
        header.place(x=0, y=0, relwidth=1.0)

        ctk.CTkLabel(
            header,
            text="ONT TESTER",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="white"
        ).place(relx=0.5, rely=0.5, anchor="center")

        # ------------------------------
        # Logo centrado
        # ------------------------------
        logo_frame = ctk.CTkFrame(
            card,
            fg_color="#F7FBFD",
            corner_radius=18,
            border_width=1,
            border_color="#D0DCE3",
            width=210,
            height=210
        )
        logo_frame.place(relx=0.5, y=110, anchor="n")

        self._logo_label = ctk.CTkLabel(logo_frame, text="")
        self._logo_label.place(relx=0.5, rely=0.5, anchor="center")

        self._cargar_logo()  # intenta cargar el logo (no truena si no existe)

        # Texto "bienvenido"
        ctk.CTkLabel(
            card,
            text="BIENVENIDO\nINGRESA TU ID",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COL_TEXTO,
            justify="center"
        ).place(relx=0.5, y=330, anchor="center")

        # Input ID
        self.id_var = ctk.StringVar(value="")
        self.id_entry = ctk.CTkEntry(
            card,
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
        self._crear_teclado_numerico(bg) # Panel numérico

        # Mensaje de validación
        self.status_var = ctk.StringVar(value="")
        self.status_label = ctk.CTkLabel(
            card,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COL_TEXTO
        )
        self.status_label.place(relx=0.5, y=435, anchor="center")

        # Botón COMENZAR (inicia deshabilitado) - colocado sobre el card para evitar esquinas blancas
        self.btn_comenzar = ctk.CTkButton(
            card,
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
            height=320
        )
        self.keypad.place(relx=0.5, rely=0.45, anchor="w", x=280, y=0)

        ctk.CTkLabel(
            self.keypad,
            text="TECLADO",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COL_TEXTO
        ).grid(row=0, column=0, columnspan=3, pady=(14, 10))

        # Grid uniforme
        for r in range(1, 6):
            self.keypad.grid_rowconfigure(r, weight=1)
        for c in range(3):
            self.keypad.grid_columnconfigure(c, weight=1)

        def mkbtn(txt, cmd, r, c, colspan=1, fg="#F7FBFD", hover="#EAF4FA", tc=None):
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
            return b

        # Layout:
        # 7 8 9
        # 4 5 6
        # 1 2 3
        # C 0 ⌫
        nums = [
            ("7", 1, 0), ("8", 1, 1), ("9", 1, 2),
            ("4", 2, 0), ("5", 2, 1), ("6", 2, 2),
            ("1", 3, 0), ("2", 3, 1), ("3", 3, 2),
        ]
        for d, r, c in nums:
            mkbtn(d, lambda x=d: self._pad_append(x), r, c)

        mkbtn("C", self._pad_clear, 4, 0, fg="#FCEDEE", hover="#F9D7DA", tc=self.COL_ERROR)
        mkbtn("0", lambda: self._pad_append("0"), 4, 1)
        mkbtn("⌫", self._pad_backspace, 4, 2, fg="#EAF4FA", hover="#DCECF8", tc=self.COL_TEXTO)

        # OK (inicia como Enter)
        mkbtn("OK", self._pad_ok, 5, 0, colspan=3, fg=self.COL_AZUL, hover=self.COL_AZUL_HOVER, tc="white")


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
        # Se comporta como presionar Enter
        self._enter_accion()
    # =========================================================
    #                    LOGO
    # =========================================================
    def _cargar_logo(self):
        """
        Intenta cargar logo desde assets/icons/logo_tester.png (como lo usas en tester_view).
        Si no existe, no rompe la UI.
        """
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
        """
        Devuelve (ok: bool, nombre: str|None)
        """
        id_str = (id_str or "").strip()

        # 1) Si tu viewmodel trae un método real:
        if self.viewmodel:
            if hasattr(self.viewmodel, "obtener_usuario_por_id"):
                try:
                    nombre = self.viewmodel.obtener_usuario_por_id(id_str)
                    return (bool(nombre), nombre)
                except Exception:
                    pass

            if hasattr(self.viewmodel, "validar_id"):
                try:
                    ok, nombre = self.viewmodel.validar_id(id_str)
                    return (bool(ok), nombre)
                except Exception:
                    pass

        # 2) Fallback: diccionario local
        nombre = self.USERS_MOCK.get(id_str)
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
        try:
            self.destroy()
        except Exception:
            pass
        nueva = view_cls(parent, event_q=self.bus_q, **init_kwargs,)
        nueva.pack(fill="both", expand=True)

    def _on_comenzar(self):
        if not self.usuario_id:
            return

        print(f"[LOGIN] ID válido: {self.usuario_id} -> {self.usuario_nombre}")

        # ✅ GUARDAR SESIÓN EN LA VENTANA ROOT (para que TesterView la lea)
        root = self.winfo_toplevel()
        root.current_user_id = str(self.usuario_id)
        root.current_user_name = str(self.usuario_nombre)

        from src.Frontend.ui.tester_view import TesterView
        self._swap_view(TesterView, viewmodel=self.viewmodel)


# Test rápido
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("ONT TESTER - Inicio")
    app.geometry("1200x650")
    app.minsize(900, 550)

    view = InicioView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()