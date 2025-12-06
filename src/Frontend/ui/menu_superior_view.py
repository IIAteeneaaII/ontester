import customtkinter as ctk


class MenuSuperiorDesplegable(ctk.CTkFrame):
    """
    Menú desplegable superior VERTICAL.

    Muestra un botón tipo hamburguesa (☰) y, al hacer clic,
    despliega un panel VERTICALMENTE hacia abajo.
    """

    def __init__(
        self,
        parent,
        on_open_tester=None,
        on_open_base_diaria=None,
        on_open_base_global=None,
        on_open_otros=None,
        **kwargs
    ):
        super().__init__(parent, fg_color="transparent", **kwargs)

        # Ventana raíz para poder pintar el menú flotando
        self.root = self.winfo_toplevel()

        # Callbacks externos
        self.on_open_tester = on_open_tester
        self.on_open_base_diaria = on_open_base_diaria
        self.on_open_base_global = on_open_base_global
        self.on_open_otros = on_open_otros

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
            height=220
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

        # Botón: OTROS
        btn_otros = ctk.CTkButton(
            botones_container,
            text="OTROS",
            width=180,
            height=40,
            corner_radius=8,
            fg_color="#4EA5D9",
            hover_color="#3B8CC2",
            text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            command=self._handle_otros,
        )
        btn_otros.pack(pady=5)

    # ---------- Lógica de despliegue ----------

    def toggle_menu(self):
        print("🔘 Toggle menu llamado")
        if self.menu_abierto:
            self.cerrar_menu()
        else:
            self.abrir_menu()

    def abrir_menu(self):
        """Calcula posición del botón y muestra el menú VERTICALMENTE hacia abajo."""
        print("📂 Abriendo menú...")
        
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
        # Menú empieza justo debajo del botón (alineado a la izquierda)
        x_rel = bx - rx
        y_rel = by - ry + bh + 4

        print(f"📍 Posición del menú: x={x_rel}, y={y_rel}")

        self.menu_frame.place(x=x_rel, y=y_rel)
        self.menu_frame.lift()
        self.menu_abierto = True
        
        print("✅ Menú abierto")

    def cerrar_menu(self):
        print("❌ Cerrando menú...")
        self.menu_frame.place_forget()
        self.menu_abierto = False

    # ---------- Callbacks internos ----------

    def _handle_ont_tester(self):
        print("🔧 Handler ONT TESTER")
        if self.on_open_tester:
            self.on_open_tester()
        else:
            print("➡️  Click en ONT TESTER")
        self.cerrar_menu()

    def _handle_base_diaria(self):
        print("📅 Handler BASE DIARIA")
        if self.on_open_base_diaria:
            self.on_open_base_diaria()
        else:
            print("➡️  Click en BASE DIARIA")
        self.cerrar_menu()

    def _handle_base_global(self):
        print("🌍 Handler BASE GLOBAL")
        if self.on_open_base_global:
            self.on_open_base_global()
        else:
            print("➡️  Click en BASE GLOBAL")
        self.cerrar_menu()

    def _handle_otros(self):
        print("⚙️  Handler OTROS")
        if self.on_open_otros:
            self.on_open_otros()
        else:
            print("➡️  Click en OTROS")
        self.cerrar_menu()


# Test del menú
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Test Menú Desplegable Vertical")
    app.geometry("1200x700")

    # Frame verde superior
    header = ctk.CTkFrame(app, fg_color="#6B9080", height=70)
    header.pack(fill="x", side="top")
    header.pack_propagate(False)

    # Menú
    menu = MenuSuperiorDesplegable(
        header,
        on_open_tester=lambda: print("🔹 Navegar a ONT TESTER"),
        on_open_base_diaria=lambda: print("🔹 Navegar a BASE DIARIA"),
        on_open_base_global=lambda: print("🔹 Navegar a BASE GLOBAL"),
        on_open_otros=lambda: print("🔹 Navegar a OTROS")
    )
    menu.pack(side="left", padx=20, pady=10)

    # Título
    titulo = ctk.CTkLabel(
        header,
        text="ONT TESTER - REPARANDO EN ESTACIÓN 09",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="white"
    )
    titulo.pack(side="left", padx=20)

    # Contenido
    contenido = ctk.CTkFrame(app, fg_color="#E8F4F8")
    contenido.pack(fill="both", expand=True)

    label = ctk.CTkLabel(
        contenido,
        text="Haz clic en el menú hamburguesa ☰\nEl menú se desplegará verticalmente ↓",
        font=ctk.CTkFont(size=16),
        justify="center"
    )
    label.pack(pady=50)

    app.mainloop()