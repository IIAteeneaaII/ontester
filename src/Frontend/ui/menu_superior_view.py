# src/Frontend/ui/menu_superior_view.py
import customtkinter as ctk


class MenuSuperiorDesplegable(ctk.CTkFrame):
    """
    Menú desplegable superior VERTICAL.

    align_mode:
      - "below"  -> (ONT TESTER) lo pones como tú ya lo tienes/quieres
      - "corner" -> (Base diaria/global/propiedades) pegado a la izquierda,
                    PERO siempre debajo de la hamburguesa (para que no se encime)
    """

    def __init__(
        self,
        parent,
        on_open_tester=None,
        on_open_base_diaria=None,
        on_open_base_global=None,
        on_open_propiedades=None,
        on_open_otros=None,      # alias
        align_mode="below",
    ):
        super().__init__(parent, fg_color="transparent")

        self.root = self.winfo_toplevel()
        

        self.on_open_tester = on_open_tester
        self.on_open_base_diaria = on_open_base_diaria
        self.on_open_base_global = on_open_base_global
        self.on_open_propiedades = on_open_propiedades or on_open_otros

        self.align_mode = align_mode
        self.menu_abierto = False

        # Guardar refs de botones para theme
        self._btns_menu = {}

        # ---------- Barra superior (hamburguesa + toggle) ----------
        self.topbar = ctk.CTkFrame(self, fg_color="transparent")
        self.topbar.pack(padx=4, pady=4)

        self.boton_menu = ctk.CTkButton(
            self.topbar,
            text="☰",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="#2C3E50",
            hover_color="#1F2A36",
            text_color="white",
            font=ctk.CTkFont(size=20, weight="bold"),
            command=self.toggle_menu,
        )
        self.boton_menu.pack(side="left")

        # ✅ Botón Toggle tema (global)
        self.boton_theme = ctk.CTkButton(
            self.topbar,
            text="🌙",
            width=40,
            height=40,
            corner_radius=8,
            fg_color="#2C3E50",
            hover_color="#1F2A36",
            text_color="white",
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self._toggle_theme,
        )
        self.boton_theme.pack(side="left", padx=(6, 0))

        # ---------- Frame del menú desplegable ----------
        self.menu_frame = ctk.CTkFrame(
            self.root,
            fg_color="#FFFFFF",
            corner_radius=0,
            border_width=2,
            border_color="#6B9080",
            width=220,
            height=250,  # + espacio por el toggle si lo quieres también dentro
        )

        # Contenedor interno
        self.botones_container = ctk.CTkFrame(
            self.menu_frame,
            fg_color="transparent",
            corner_radius=0
        )
        self.botones_container.pack(padx=12, pady=12, fill="both", expand=True)

        self._btns_menu["tester"] = ctk.CTkButton(
            self.botones_container,
            text="ONT TESTER",
            width=190,
            height=40,
            corner_radius=8,
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_tester,
        )
        self._btns_menu["tester"].pack(pady=5)

        self._btns_menu["base_diaria"] = ctk.CTkButton(
            self.botones_container,
            text="BASE DIARIA",
            width=190,
            height=40,
            corner_radius=8,
            fg_color="#A8DADC",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_base_diaria,
        )
        self._btns_menu["base_diaria"].pack(pady=5)

        self._btns_menu["base_global"] = ctk.CTkButton(
            self.botones_container,
            text="BASE GLOBAL",
            width=190,
            height=40,
            corner_radius=8,
            fg_color="#F1B4BB",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_base_global,
        )
        self._btns_menu["base_global"].pack(pady=5)

        self._btns_menu["otros"] = ctk.CTkButton(
            self.botones_container,
            text="OTROS",
            width=190,
            height=40,
            corner_radius=8,
            fg_color="#4EA5D9",
            hover_color="#3B8CC2",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._go_propiedades,
        )
        self._btns_menu["otros"].pack(pady=5)

        # ✅ Aplicar tema actual si el root ya tiene theme
        if hasattr(self.root, "theme"):
            self.apply_theme(self.root.theme.palette())

    # ================== Theme ==================

    def _toggle_theme(self):
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            root.theme.toggle()
            if hasattr(root, "refresh_theme"):
                root.refresh_theme()
            else:
                self.apply_theme(root.theme.palette())

        # si el menú está abierto, recolorea el menú también
        if hasattr(root, "theme"):
            self.apply_theme(root.theme.palette())

    def apply_theme(self, p: dict):
        """
        Aplica tema a:
        - botón hamburguesa
        - botón theme
        - menu_frame + botones
        """
        root = self.winfo_toplevel()
        mode = getattr(getattr(root, "theme", None), "mode", "light")

        # Icono botón theme
        self.boton_theme.configure(text=("☀️" if mode == "dark" else "🌙"))

        # Botones superiores (mantener consistencia)
        btn_bg = "#2C3E50" if mode == "light" else "#111827"
        btn_hover = "#1F2A36" if mode == "light" else "#0F172A"

        self.boton_menu.configure(fg_color=btn_bg, hover_color=btn_hover, text_color="white")
        self.boton_theme.configure(fg_color=btn_bg, hover_color=btn_hover, text_color="white")

        # Menú desplegable
        self.menu_frame.configure(
            fg_color=p.get("card", "#FFFFFF"),
            border_color=p.get("border", "#6B9080"),
        )

        # Botones del menú (si quieres que cambien “inteligente” en dark)
        # En dark hacemos fondos más sobrios pero respetando tu paleta.
        if mode == "dark":
            # Base
            t_text = p.get("text", "#E5E7EB")
            # ONT TESTER (verde oscuro)
            self._btns_menu["tester"].configure(
                fg_color="#1F3A2E",
                hover_color="#234235",
                text_color="white",
            )
            # Base diaria (aqua oscuro)
            self._btns_menu["base_diaria"].configure(
                fg_color="#163C44",
                hover_color="#1A4650",
                text_color=t_text,
            )
            # Base global (rosa oscuro)
            self._btns_menu["base_global"].configure(
                fg_color="#40212A",
                hover_color="#4A2530",
                text_color=t_text,
            )
            # Otros (azul)
            self._btns_menu["otros"].configure(
                fg_color=p.get("primary", "#60A5FA"),
                hover_color=p.get("primary_hover", "#3B82F6"),
                text_color="white",
            )
        else:
            # Volver a tus colores originales
            self._btns_menu["tester"].configure(
                fg_color="#6B9080", hover_color="#5A7A6A", text_color="white"
            )
            self._btns_menu["base_diaria"].configure(
                fg_color="#A8DADC", hover_color="#8FC9CB", text_color="#2C3E50"
            )
            self._btns_menu["base_global"].configure(
                fg_color="#F1B4BB", hover_color="#E89BA3", text_color="#2C3E50"
            )
            self._btns_menu["otros"].configure(
                fg_color="#4EA5D9", hover_color="#3B8CC2", text_color="white"
            )

    # ================== Menú ==================

    def toggle_menu(self):
        if self.menu_abierto:
            self.cerrar_menu()
        else:
            self.abrir_menu()

    def abrir_menu(self):
        self.root.update_idletasks()
        self.update_idletasks()
        self.boton_menu.update_idletasks()

        bx = self.boton_menu.winfo_rootx()
        by = self.boton_menu.winfo_rooty()
        bh = self.boton_menu.winfo_height()

        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()

        if self.align_mode == "below":
            x_rel = bx - rx
            y_rel = (by - ry) + bh
        else:
            x_rel = 12
            y_rel = (by - ry) + bh + 6

        self.menu_frame.place(x=x_rel, y=y_rel)
        self.menu_frame.lift()
        self.menu_abierto = True

        # Aplicar tema al abrir (por si cambió)
        if hasattr(self.root, "theme"):
            self.apply_theme(self.root.theme.palette())

    def cerrar_menu(self):
        self.menu_frame.place_forget()
        self.menu_abierto = False

    # ================== Toplevel helper ==================

    def _abrir_en_toplevel(self, view_cls, titulo: str, geometry: str = "1400x800"):
        top = ctk.CTkToplevel(self.root)
        top.title(titulo)
        top.geometry(geometry)

        # ✅ Heredar theme del root
        if hasattr(self.root, "theme"):
            top.theme = self.root.theme
            # aplica modo global (CTk)
            top.theme.apply()

        vista = view_cls(top)
        vista.pack(fill="both", expand=True)

        # ✅ si la vista soporta apply_theme, aplícalo
        if hasattr(top, "theme") and hasattr(vista, "apply_theme"):
            vista.apply_theme(top.theme.palette())

        top.focus()

    # ================== GO methods ==================

    def _go_tester(self):
        try:
            if callable(self.on_open_tester):
                self.on_open_tester()
            else:
                from src.Frontend.ui.tester_view import TesterView
                self._abrir_en_toplevel(TesterView, "ONT TESTER", "1200x600")
        finally:
            self.cerrar_menu()

    def _go_base_diaria(self):
        try:
            if callable(self.on_open_base_diaria):
                self.on_open_base_diaria()
            else:
                from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
                self._abrir_en_toplevel(EscaneosDiaView, "BASE DIARIA - Escaneos del Día", "1400x800")
        finally:
            self.cerrar_menu()

    def _go_base_global(self):
        try:
            if callable(self.on_open_base_global):
                self.on_open_base_global()
            else:
                from src.Frontend.ui.reporte_global_view import ReporteGlobalView
                self._abrir_en_toplevel(ReporteGlobalView, "BASE GLOBAL - Reporte Global", "1400x900")
        finally:
            self.cerrar_menu()

    def _go_propiedades(self):
        try:
            if callable(self.on_open_propiedades):
                self.on_open_propiedades()
            else:
                from src.Frontend.ui.propiedades_view import TesterMainView
                self._abrir_en_toplevel(TesterMainView, "OTROS - Propiedades", "1400x700")
        finally:
            self.cerrar_menu()
