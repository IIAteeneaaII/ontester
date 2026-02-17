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

        # ---------- Botón hamburguesa ----------
        self.boton_menu = ctk.CTkButton(
            self,
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
        self.boton_menu.pack(padx=4, pady=4)

        # ---------- Frame del menú desplegable ----------
        # (cuadrado como pediste)
        self.menu_frame = ctk.CTkFrame(
            self.root,
            fg_color="#FFFFFF",
            corner_radius=0,          # <- cuadrado
            border_width=2,
            border_color="#6B9080",
            width=220,
            height=230,
        )

        # Contenedor interno (para que no se vea “feo” el borde por dentro)
        botones_container = ctk.CTkFrame(
            self.menu_frame,
            fg_color="transparent",
            corner_radius=0
        )
        botones_container.pack(padx=12, pady=12, fill="both", expand=True)

        btn_tester = ctk.CTkButton(
            botones_container,
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
        btn_tester.pack(pady=5)

        btn_base_diaria = ctk.CTkButton(
            botones_container,
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
        btn_base_diaria.pack(pady=5)

        btn_base_global = ctk.CTkButton(
            botones_container,
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
        btn_base_global.pack(pady=5)

        btn_propiedades = ctk.CTkButton(
            botones_container,
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
        btn_propiedades.pack(pady=5)

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

        # Coordenadas del botón en pantalla
        bx = self.boton_menu.winfo_rootx()
        by = self.boton_menu.winfo_rooty()
        bh = self.boton_menu.winfo_height()

        # Coordenadas del root en pantalla
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()

        if self.align_mode == "below":
            # (ONT TESTER) lo dejas como tú lo quieres
            x_rel = bx - rx
            y_rel = (by - ry)  # <- tu comportamiento actual

        else:  # "corner" (Base diaria/global/propiedades)
            # Pegado a la izquierda, PERO debajo de la hamburguesa
            x_rel = 12
            y_rel = (by - ry) + bh + 6

        self.menu_frame.place(x=x_rel, y=y_rel)
        self.menu_frame.lift()
        self.menu_abierto = True

    def cerrar_menu(self):
        self.menu_frame.place_forget()
        self.menu_abierto = False

    # ================== Toplevel helper ==================

    def _abrir_en_toplevel(self, view_cls, titulo: str, geometry: str = "1400x800"):
        top = ctk.CTkToplevel(self.root)
        top.title(titulo)
        top.geometry(geometry)

        vista = view_cls(top)
        vista.pack(fill="both", expand=True)

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
