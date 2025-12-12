import customtkinter as ctk

class MenuSuperiorDesplegable(ctk.CTkFrame):
    """
    Menú desplegable superior VERTICAL.

    Muestra un botón tipo hamburguesa (☰) y, al hacer clic,
    despliega un panel VERTICALMENTE hacia abajo.

    Rutas:
    - ONT TESTER   -> tester_view.py (TesterView)
    - BASE DIARIA  -> escaneos_dia_view.py (EscaneosDiaView)
    - BASE GLOBAL  -> reporte_global_view.py (ReporteGlobalView)
    - OTROS        -> propiedades_view.py (TesterMainView)
    """

    def __init__(
        self,
        parent,
        on_open_tester=None,
        on_open_base_diaria=None,
        on_open_base_global=None,
        on_open_propiedades=None,
        on_open_otros=None,   # lo usas desde propiedades_view
    ):
        # ⚠️ NO pasar kwargs con callbacks a CTkFrame
        super().__init__(parent, fg_color="transparent")

        # Ventana raíz para poder abrir Toplevels y posicionar el menú
        self.root = self.winfo_toplevel()

        # Callbacks externos (opcionales)
        self.on_open_tester = on_open_tester
        self.on_open_base_diaria = on_open_base_diaria
        self.on_open_base_global = on_open_base_global
        # Aceptamos ambos nombres: on_open_propiedades / on_open_otros
        self.on_open_propiedades = on_open_propiedades or on_open_otros

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

        # ---------- Frame del menú desplegable VERTICAL ----------
        self.menu_frame = ctk.CTkFrame(
            self.root,
            fg_color="#FFFFFF",
            corner_radius=12,
            border_width=2,
            border_color="#6B9080",
            width=200,
            height=220,
        )

        # Contenedor interno para los botones en VERTICAL
        botones_container = ctk.CTkFrame(self.menu_frame, fg_color="transparent")
        botones_container.pack(padx=12, pady=12, fill="both", expand=True)

        # Botón: ONT TESTER
        btn_tester = ctk.CTkButton(
            botones_container,
            text="ONT TESTER",
            width=180,
            height=40,
            corner_radius=8,
            fg_color="#6B9080",
            hover_color="#5A7A6A",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_ont_tester,
        )
        btn_tester.pack(pady=5)

        # Botón: BASE DIARIA
        btn_base_diaria = ctk.CTkButton(
            botones_container,
            text="BASE DIARIA",
            width=180,
            height=40,
            corner_radius=8,
            fg_color="#A8DADC",
            hover_color="#8FC9CB",
            text_color="#2C3E50",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_base_diaria,
        )
        btn_base_diaria.pack(pady=5)

        # Botón: BASE GLOBAL
        btn_base_global = ctk.CTkButton(
            botones_container,
            text="BASE GLOBAL",
            width=180,
            height=40,
            corner_radius=8,
            fg_color="#F1B4BB",
            hover_color="#E89BA3",
            text_color="#2C3E50",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_base_global,
        )
        btn_base_global.pack(pady=5)

        # Botón: OTROS (PROPIEDADES)
        btn_propiedades = ctk.CTkButton(
            botones_container,
            text="OTROS",
            width=180,
            height=40,
            corner_radius=8,
            fg_color="#4EA5D9",
            hover_color="#3B8CC2",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_propiedades,
        )
        btn_propiedades.pack(pady=5)

    # =========================================================
    #               LÓGICA DE DESPLIEGUE DEL MENÚ
    # =========================================================

    def toggle_menu(self):
        if self.menu_abierto:
            self.cerrar_menu()
        else:
            self.abrir_menu()

    def abrir_menu(self):
        """Calcula posición del botón y muestra el menú VERTICALMENTE hacia abajo."""
        # Forzar actualización de geometría
        self.root.update_idletasks()
        self.update_idletasks()
        self.boton_menu.update_idletasks()

        # Coordenadas del botón en la pantalla
        bx = self.boton_menu.winfo_rootx()
        by = self.boton_menu.winfo_rooty()
        bw = self.boton_menu.winfo_width()
        bh = self.boton_menu.winfo_height()

        # Coordenadas de la ventana raíz
        rx = self.root.winfo_rootx()
        ry = self.root.winfo_rooty()

        # Coordenadas relativas a la ventana
        x_rel = bx - rx          # alineado a la izquierda del botón
        y_rel = by - ry + bh + 4 # justo debajo del botón

        self.menu_frame.place(x=x_rel, y=y_rel)
        self.menu_frame.lift()
        self.menu_abierto = True

    def cerrar_menu(self):
        self.menu_frame.place_forget()
        self.menu_abierto = False

    # =========================================================
    #     UTILIDAD: ABRIR UNA VISTA EN UNA NUEVA CTkToplevel
    # =========================================================

    def _abrir_en_toplevel(self, view_cls, titulo: str, geometry: str = "1400x800"):
        """
        Crea una nueva ventana CTkToplevel con la vista indicada.
        """
        top = ctk.CTkToplevel(self.root)
        top.title(titulo)
        top.geometry(geometry)

        vista = view_cls(top)
        vista.pack(fill="both", expand=True)

        top.focus()

    # =========================================================
    #          HANDLERS DE CADA OPCIÓN DEL MENÚ
    # =========================================================

    def _handle_ont_tester(self):
        """ONT TESTER -> tester_view.py"""
        if self.on_open_tester:
            # Usar callback si te lo pasan desde fuera
            self.on_open_tester()
        else:
            # Fallback: abrir ventana con TesterView
            from src.Frontend.ui.tester_view import TesterView
            self._abrir_en_toplevel(TesterView, "ONT TESTER", "1200x600")
        self.cerrar_menu()

    def _handle_base_diaria(self):
        """BASE DIARIA -> escaneos_dia_view.py"""
        if self.on_open_base_diaria:
            self.on_open_base_diaria()
        else:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
            self._abrir_en_toplevel(EscaneosDiaView, "BASE DIARIA - Escaneos del Día", "1400x800")
        self.cerrar_menu()

    def _handle_base_global(self):
        """BASE GLOBAL -> reporte_global_view.py"""
        if self.on_open_base_global:
            self.on_open_base_global()
        else:
            from src.Frontend.ui.reporte_global_view import ReporteGlobalView
            self._abrir_en_toplevel(ReporteGlobalView, "BASE GLOBAL - Reporte Global", "1400x900")
        self.cerrar_menu()

    def _handle_propiedades(self):
        """OTROS -> propiedades_view.py (TesterMainView)"""
        if self.on_open_propiedades:
            self.on_open_propiedades()
        else:
            from src.Frontend.ui.propiedades_view import TesterMainView
            self._abrir_en_toplevel(TesterMainView, "OTROS - Propiedades", "1400x700")
        self.cerrar_menu()
