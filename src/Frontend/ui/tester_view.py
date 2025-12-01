import customtkinter as ctk
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion

# Agregar la raíz del proyecto al path
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.navigation.botones import (
    boton_OMITIR,
    boton_Ethernet,
    boton_Conectividad,
    boton_Otrospuertos,
    boton_señaleswifi,
)


class TesterView(ctk.CTkFrame):
    def __init__(self, parent, viewmodel=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Referencia opcional al ViewModel
        self.viewmodel = viewmodel
        self._last_result_ok = False         # para pruebas sin VM
        self.pruebas_realizadas = 0          # contador de pruebas

        # Colores para los estados de los botones
        self.color_neutro_fg = "#3498db"     # azul
        self.color_neutro_hover = "#2980b9"
        self.color_activo_fg = "#27ae60"     # verde
        self.color_activo_hover = "#1e8449"
        self.color_inactivo_fg = "#e74c3c"   # rojo
        self.color_inactivo_hover = "#c0392b"

        # Configurar grid general
        self.grid_columnconfigure(0, weight=0)  # sidebar
        self.grid_columnconfigure(1, weight=1)  # contenido
        self.grid_rowconfigure(0, weight=1)

        # ========= ASSETS =========
        assets_dir = Path(__file__).parent.parent / "assets" / "icons"
        logo_path = assets_dir / "logo_tester.png"
        # ==========================

        # ======= SIDEBAR CON SCROLL =======
        self.left_scroll = ctk.CTkScrollableFrame(
            self,
            width=280,          # ancho del sidebar
            corner_radius=0
        )
        self.left_scroll.grid(row=0, column=0, sticky="nsw", padx=0, pady=0)

        # Alias para usarlo como contenedor de los controles
        left_frame = self.left_scroll
        # ==================================

        # ===== Logo circular en la parte superior izquierda =====
        self.logo_image = ctk.CTkImage(
            light_image=Image.open(logo_path),
            dark_image=Image.open(logo_path),
            size=(48, 48)  # tamaño del logo
        )

        logo_frame = ctk.CTkFrame(
            left_frame,
            width=70,
            height=70,
            corner_radius=35,     # círculo
            fg_color="#FFFFFF"
        )
        logo_frame.pack(pady=(15, 5))
        logo_frame.pack_propagate(False)

        logo_label = ctk.CTkLabel(logo_frame, text="", image=self.logo_image)
        logo_label.pack(expand=True)
        # =========================================================

        # ===== Menú desplegable "Escoge el modo" =====
        self.modo_var = ctk.StringVar(value="Escoge el modo")

        self.modo_menu = ctk.CTkOptionMenu(
            left_frame,
            variable=self.modo_var,
            values=["Testeo", "Retesteo", "Etiqueta"],
            command=self.cambiar_modo,
            font=ctk.CTkFont(size=16, weight="bold"),

            height=36,
            corner_radius=8,
            width=260,  # casi el ancho del sidebar

            fg_color="#3498db",
            text_color="white",
            button_color="#2980b9",
            button_hover_color="#2471a3",

            dropdown_fg_color="#3498db",
            dropdown_hover_color="#2980b9",
            dropdown_text_color="white",
            dropdown_font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.modo_menu.pack(pady=(20, 30), padx=20, fill="x")
        # =============================================

        # ------ Botones principales del sidebar ------
        self.btn_omitir = boton_OMITIR(left_frame, command=self.ir_OMITIR)
        self.btn_omitir.pack(pady=10, padx=20, fill="x")

        self.btn_ethernet = boton_Ethernet(left_frame, command=self.ir_ethernet)
        self.btn_ethernet.pack(pady=10, padx=20, fill="x")

        self.btn_conectividad = boton_Conectividad(left_frame, command=self.ir_conectividad)
        self.btn_conectividad.pack(pady=10, padx=20, fill="x")

        self.btn_otros_puertos = boton_Otrospuertos(left_frame, command=self.ir_otros_puertos)
        self.btn_otros_puertos.pack(pady=10, padx=20, fill="x")

        self.btn_wifi = boton_señaleswifi(left_frame, command=self.ir_senales_wifi)
        self.btn_wifi.pack(pady=10, padx=20, fill="x")
        # ---------------------------------------------

        # ====== Bloque de usuario + botón SALIR (abajo) ======
        self.user_block = ctk.CTkFrame(left_frame, fg_color="transparent")
        self.user_block.pack(side="bottom", fill="x", padx=20, pady=(20, 10))

        # Etiquetas de Id y Hola
        self.label_usuario_id = ctk.CTkLabel(
            self.user_block,
            text="Id: __________",
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            justify="left"
        )
        self.label_usuario_id.pack(anchor="w")

        self.label_usuario_nombre = ctk.CTkLabel(
            self.user_block,
            text="Hola: (nombre de usuario)",
            font=ctk.CTkFont(size=12),
            anchor="w",
            justify="left"
        )
        self.label_usuario_nombre.pack(anchor="w", pady=(2, 8))

        # Botón SALIR en rojo
        self.btn_salir = ctk.CTkButton(
            self.user_block,
            text="SALIR",
            fg_color="#e74c3c",
            hover_color="#c0392b",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6,
            height=32,
            command=self.ir_salir
        )
        self.btn_salir.pack(fill="x", pady=(4, 0))
        # =======================================================

        # Estado inicial: todos neutros (azules)
        self._set_all_buttons_state("neutral")

        # Frame derecho (área principal/contenido)
        self.right_frame = ctk.CTkFrame(self, corner_radius=0)
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # ========= BARRA SUPERIOR COMPLETA =========
        top_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=20, padx=40)

        # -- Izquierda: estado de la última prueba --
        left_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_bar.pack(side="left")

        lbl_prueba = ctk.CTkLabel(
            left_bar,
            text="Prueba:",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        lbl_prueba.pack(side="left")

        self.estado_prueba_label = ctk.CTkLabel(
            left_bar,
            text="SIN EJECUTAR",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f1c40f"  # amarillo
        )
        self.estado_prueba_label.pack(side="left", padx=(10, 0))

        # -- Centro: reloj / fecha --
        center_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        center_bar.pack(side="left", expand=True)

        self.clock_label = ctk.CTkLabel(
            center_bar,
            text="",
            font=ctk.CTkFont(size=20)
        )
        self.clock_label.pack()

        # -- Derecha: contador de pruebas realizadas --
        right_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_bar.pack(side="right")

        lbl_pruebas_realizadas = ctk.CTkLabel(
            right_bar,
            text="Pruebas realizadas:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        lbl_pruebas_realizadas.pack(side="left")

        self.pruebas_count_label = ctk.CTkLabel(
            right_bar,
            text="0",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        self.pruebas_count_label.pack(side="left", padx=(5, 0))
        # ===========================================

        # ======= CONTENIDO PRINCIPAL =======
        self.main_content = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.main_content.pack(expand=True, fill="both", padx=60, pady=(30, 0))

        # Frame de información (SN, MAC, SOFTWARE, etc.)
        info_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        info_frame.pack(side="top", fill="x", pady=(0, 30))

        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        # Columna izquierda (SN / MAC / SOFTWARE / WIFI / Password)
        lbl_sn = ctk.CTkLabel(
            info_frame,
            text="SN:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_sn.grid(row=0, column=0, sticky="w", pady=(0, 5))

        lbl_mac = ctk.CTkLabel(
            info_frame,
            text="MAC:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_mac.grid(row=1, column=0, sticky="w", pady=(0, 25))

        lbl_software = ctk.CTkLabel(
            info_frame,
            text="SOFTWARE:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_software.grid(row=2, column=0, sticky="w", pady=(10, 5))

        lbl_wifi24 = ctk.CTkLabel(
            info_frame,
            text="WIFI 2.4 GHz:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_wifi24.grid(row=3, column=0, sticky="w", pady=5)

        lbl_wifi5 = ctk.CTkLabel(
            info_frame,
            text="WIFI 5 GHz:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_wifi5.grid(row=4, column=0, sticky="w", pady=5)

        lbl_password = ctk.CTkLabel(
            info_frame,
            text="Password",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_password.grid(row=5, column=0, sticky="w", pady=(5, 0))

        # Columna derecha (Fo TX / Fo Rx / Usb Port)
        lbl_fo_tx = ctk.CTkLabel(
            info_frame,
            text="Fo TX:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_fo_tx.grid(row=2, column=1, sticky="w", padx=(40, 0), pady=(10, 5))

        lbl_fo_rx = ctk.CTkLabel(
            info_frame,
            text="Fo Rx:",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_fo_rx.grid(row=3, column=1, sticky="w", padx=(40, 0), pady=5)

        lbl_usb = ctk.CTkLabel(
            info_frame,
            text="Usb Port",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w"
        )
        lbl_usb.grid(row=4, column=1, sticky="w", padx=(40, 0), pady=(5, 0))
        # ====================================

        # Panel de pruebas de conectividad (compartido entre vistas)
        self.panel_pruebas = PanelPruebasConexion(self.main_content)
        self.panel_pruebas.pack(side="bottom", fill="x", padx=60, pady=(40, 10))
        # ====================================

        # Iniciar actualización del reloj
        self.update_clock()

        # Responsividad
        self.bind("<Configure>", self._on_resize)

    # ========= Métodos para usuario =========
    def set_usuario(self, user_id: str, nombre: str):
        """Permite actualizar los textos de Id y nombre de usuario."""
        self.label_usuario_id.configure(text=f"Id: {user_id}")
        self.label_usuario_nombre.configure(text=f"Hola: {nombre}")
    # ========================================

    # ================= Helpers de estilo =================
    def _set_button_style(self, button, state: str):
        """state: 'neutral', 'active', 'inactive'."""
        if state == "active":
            fg = self.color_activo_fg
            hover = self.color_activo_hover
        elif state == "inactive":
            fg = self.color_inactivo_fg
            hover = self.color_inactivo_hover
        else:  # neutral
            fg = self.color_neutro_fg
            hover = self.color_neutro_hover

        button.configure(fg_color=fg, hover_color=hover)

    def _set_all_buttons_state(self, state: str):
        """Pone TODOS los botones en el mismo estado."""
        self._set_button_style(self.btn_omitir, state)
        self._set_button_style(self.btn_ethernet, state)
        self._set_button_style(self.btn_conectividad, state)
        self._set_button_style(self.btn_otros_puertos, state)
        self._set_button_style(self.btn_wifi, state)

    # ================= Responsividad =================
    def _on_resize(self, event):
        """Ajusta proporciones cuando cambia el tamaño de la ventana."""
        if event.widget is not self:
            return

        width = max(event.width, 400)

        if width < 950:
            sidebar_width = 280
        else:
            sidebar_width = int(width * 0.22)
            sidebar_width = max(280, min(sidebar_width, 320))

        self.left_scroll.configure(width=sidebar_width)

    # ================= LÓGICA DE UI =================
    def update_clock(self):
        """Actualiza el reloj cada segundo."""
        now = datetime.now()
        time_string = now.strftime("%I:%M %p  %d %B %Y")

        meses = {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
        for eng, esp in meses.items():
            time_string = time_string.replace(eng, esp)

        self.clock_label.configure(text=time_string)
        self.after(1000, self.update_clock)

    def cambiar_modo(self, modo: str):
        """Se ejecuta cuando eliges Testeo / Retesteo / Etiqueta."""
        print(f"Modo seleccionado: {modo}")

        # Primero, todos neutros
        self._set_all_buttons_state("neutral")

        if modo == "Testeo":
            # Activos: OMITIR, CONECTIVIDAD, OTROS PUERTOS
            self._set_button_style(self.btn_omitir, "active")
            self._set_button_style(self.btn_conectividad, "active")
            self._set_button_style(self.btn_otros_puertos, "active")

            # Inactivos: ETHERNET, WIFI
            self._set_button_style(self.btn_ethernet, "inactive")
            self._set_button_style(self.btn_wifi, "inactive")

        elif modo == "Retesteo":
            # Todos activos
            self._set_all_buttons_state("active")

        elif modo == "Etiqueta":
            # Todos inactivos
            self._set_all_buttons_state("inactive")

    def actualizar_estado_prueba(self, estado):
        """
        Actualiza el texto y color de 'Prueba: ...'
        estado puede ser:
          - True / False
          - 'EXITOSA' / 'FALLIDA' / etc.
        """
        if isinstance(estado, str):
            estado_normalizado = estado.strip().upper()
        else:
            estado_normalizado = "EXITOSA" if estado else "FALLIDA"

        if estado_normalizado in ("EXITOSA", "OK", "SUCCESS", "TRUE"):
            texto = "EXITOSA"
            color = "#2ecc71"   # verde
        elif estado_normalizado in ("FALLIDA", "FAIL", "ERROR", "FALSE"):
            texto = "FALLIDA"
            color = "#e74c3c"   # rojo
        else:
            texto = str(estado)
            color = "#f1c40f"   # neutro

        self.estado_prueba_label.configure(text=texto, text_color=color)

    def incrementar_contador_pruebas(self):
        """Incrementa el contador y actualiza la etiqueta de 'Pruebas realizadas'."""
        self.pruebas_realizadas += 1
        self.pruebas_count_label.configure(text=str(self.pruebas_realizadas))

    def _ejecutar_prueba_desde_boton(self, nombre_prueba: str):
        """Utilidad para ejecutar la lógica de prueba desde cualquier botón."""
        print(f"Ejecutando {nombre_prueba}...")

        if self.viewmodel is not None:
            self.viewmodel.ejecutar_prueba()
        else:
            self._last_result_ok = not self._last_result_ok
            self.actualizar_estado_prueba(self._last_result_ok)
            self.incrementar_contador_pruebas()

    # ================= HANDLERS DE LOS BOTONES =================
    def ir_OMITIR(self):
        print("Navegando a OMITIR RETEST DE FÁBRICA")

    def ir_ethernet(self):
        self._ejecutar_prueba_desde_boton("PRUEBA DE ETHERNET")

    def ir_conectividad(self):
        self._ejecutar_prueba_desde_boton("PRUEBA DE CONECTIVIDAD")

    def ir_otros_puertos(self):
        self._ejecutar_prueba_desde_boton("PRUEBA DE OTROS PUERTOS")

    def ir_senales_wifi(self):
        self._ejecutar_prueba_desde_boton("PRUEBA DE SEÑALES WIFI")

    def ir_salir(self):
        """Cierra la ventana principal."""
        root = self.winfo_toplevel()
        root.destroy()


# Para probar la vista individualmente (sin VM)
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Tester View")
    app.geometry("1200x600")
    app.minsize(900, 550)

    view = TesterView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()
