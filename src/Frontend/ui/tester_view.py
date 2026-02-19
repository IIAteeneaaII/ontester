# src/Frontend/ui/tester_view.py
from src.backend.endpoints.conexion import iniciar_testerConexion
import customtkinter as ctk
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image
import threading
import time

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion

# Agregar la raíz del proyecto al path para poder usar imports absolutos
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.navigation.botones import (
    boton_OMITIR,
    boton_Ethernet,
    boton_Conectividad,
    boton_Otrospuertos,
    boton_señaleswifi,
)

from src.Frontend.ui.menu_superior_view import MenuSuperiorDesplegable


class TesterView(ctk.CTkFrame):
    def __init__(self, parent, mdebug=None, viewmodel=None, **kwargs):
        # ✅ IMPORTANTE: transparente para que el Theme lo pinte
        super().__init__(parent, fg_color="transparent", **kwargs)

        self.viewmodel = viewmodel
        self._init_kwargs = dict(kwargs)

        # Para hilos / loop
        self.stop_event = threading.Event()
        self.tester_thread = None
        self.modelo_detectado = None

        self._mode_thread = None  # (si lo usas en otro lado)
        self._unit_thread = None
        self._unit_stop_event = None
        self._unit_running = False
        self._suppress_cleanup_until = 0.0

        # Paleta de colores para estados de botones (pastel)
        self.color_neutro_fg = "#4EA5D9"
        self.color_neutro_hover = "#3B8CC2"
        self.color_activo_fg = "#6FCF97"
        self.color_activo_hover = "#56B27D"
        self.color_inactivo_fg = "#F28B82"
        self.color_inactivo_hover = "#E0665C"

        # ====== estado sidebar + grid ======
        self.sidebar_visible = True
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)  # toggle
        self.grid_rowconfigure(1, weight=1)  # contenido

        # ========= ASSETS =========
        assets_dir = Path(__file__).parent.parent / "assets" / "icons"
        logo_path = assets_dir / "logo_tester.png"

        # ====== botón toggle esquina sup izq ======
        self.toggle_btn = ctk.CTkButton(
            self,
            text="◀",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=self.color_activo_fg,
            hover_color=self.color_activo_hover,
            text_color="white",
            command=self.toggle_sidebar,
        )
        self.toggle_btn.grid(row=0, column=0, sticky="nw", padx=6, pady=6)

        # ======= SIDEBAR CON SCROLL =======
        self.left_scroll = ctk.CTkScrollableFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color="#76CC3D",  # se sobreescribe por theme
        )
        self.left_scroll.grid(row=1, column=0, sticky="nsw", padx=0, pady=0)

        # Guardamos ref para theme
        self.left_frame = self.left_scroll

        # ===== Logo circular superior =====
        try:
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(48, 48),
            )
        except Exception:
            self.logo_image = None

        self.logo_frame = ctk.CTkFrame(
            self.left_frame, width=70, height=70, corner_radius=35, fg_color="#FFFFFF"
        )
        self.logo_frame.pack(pady=(15, 5))
        self.logo_frame.pack_propagate(False)

        ctk.CTkLabel(self.logo_frame, text="", image=self.logo_image).pack(expand=True)

        # ===== Menú desplegable "Escoge el modo" =====
        self.modo_var = ctk.StringVar(value="Escoge el modo")
        self.modo_menu = ctk.CTkOptionMenu(
            self.left_frame,
            variable=self.modo_var,
            values=["Testeo", "Retesteo", "Etiqueta", "Monitoreo"],
            command=self.cambiar_modo,
            font=ctk.CTkFont(size=16, weight="bold"),
            height=36,
            corner_radius=8,
            width=260,
            fg_color="#4EA5D9",
            text_color="white",
            button_color="#3B8CC2",
            button_hover_color="#2F6FA0",
            dropdown_fg_color="#4EA5D9",
            dropdown_hover_color="#3B8CC2",
            dropdown_text_color="white",
            dropdown_font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.modo_menu.pack(pady=(20, 30), padx=20, fill="x")

        # ------ Botones principales del sidebar ------
        self.btn_omitir = boton_OMITIR(self.left_frame, command=self.ir_OMITIR)
        self.btn_omitir.pack(pady=10, padx=20, fill="x")

        self.btn_ethernet = boton_Ethernet(self.left_frame, command=self.ir_ethernet)
        self.btn_ethernet.pack(pady=10, padx=20, fill="x")

        self.btn_conectividad = boton_Conectividad(self.left_frame, command=self.ir_conectividad)
        self.btn_conectividad.pack(pady=10, padx=20, fill="x")

        self.btn_otros_puertos = boton_Otrospuertos(self.left_frame, command=self.ir_otros_puertos)
        self.btn_otros_puertos.pack(pady=10, padx=20, fill="x")

        self.btn_wifi = boton_señaleswifi(self.left_frame, command=self.ir_senales_wifi)
        self.btn_wifi.pack(pady=10, padx=20, fill="x")

        # ====== Bloque de usuario + botón SALIR ======
        self.user_block = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.user_block.pack(side="bottom", fill="x", padx=20, pady=(20, 10))

        user_font_bold = ctk.CTkFont(family="Segoe UI", size=30, weight="bold")
        user_font_regular = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")

        self.label_usuario_id = ctk.CTkLabel(
            self.user_block,
            text="ID: ",
            font=user_font_bold,
            text_color="#37474F",
            anchor="w",
            justify="left",
        )
        self.label_usuario_id.pack(anchor="w")

        self.label_usuario_nombre = ctk.CTkLabel(
            self.user_block,
            text="HOLA: ",
            font=user_font_regular,
            text_color="#37474F",
            anchor="w",
            justify="left",
        )
        self.label_usuario_nombre.pack(anchor="w", pady=(2, 8))

        self.btn_salir = ctk.CTkButton(
            self.user_block,
            text="SALIR",
            fg_color="#F28B82",
            hover_color="#E0665C",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6,
            height=32,
            command=self.ir_salir,
        )
        self.btn_salir.pack(fill="x", pady=(4, 0))

        # REINICIO
        self.btn_reinicio = ctk.CTkButton(
            self.user_block,
            text="REINICIO",
            fg_color="#9B59B6",
            hover_color="#8E44AD",
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6,
            height=32,
            command=self.ir_reinicio,
        )
        self.btn_reinicio.pack(fill="x", pady=(8, 0))

        # Estado inicial de los botones
        self._set_all_buttons_state("neutral")

        # ===== Frame derecho (contenido principal) =====
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#D2E3EC")
        self.right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=0, pady=0)

        # ========= BARRA SUPERIOR =========
        self.top_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.top_bar.pack(fill="x", pady=20, padx=40)

        self.top_bar.grid_columnconfigure(0, weight=0)  # menú
        self.top_bar.grid_columnconfigure(1, weight=0)  # estado prueba
        self.top_bar.grid_columnconfigure(2, weight=1)  # reloj
        self.top_bar.grid_columnconfigure(3, weight=0)  # modelo

        self.menu_superior = MenuSuperiorDesplegable(
            self.top_bar,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=(0, 15))

        self.left_bar = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.left_bar.grid(row=0, column=1, sticky="w")

        self.prueba_static_label = ctk.CTkLabel(
            self.left_bar,
            text="Prueba:",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2C3E50",
        )
        self.prueba_static_label.pack(side="left")

        self.estado_prueba_label = ctk.CTkLabel(
            self.left_bar,
            text="SIN EJECUTAR",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f1c40f",
        )
        self.estado_prueba_label.pack(side="left", padx=(10, 0))

        self.center_bar = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.center_bar.grid(row=0, column=2, sticky="ew")

        self.clock_label = ctk.CTkLabel(
            self.center_bar,
            text="",
            font=ctk.CTkFont(size=20),
            text_color="#2C3E50",
        )
        self.clock_label.pack()

        self.right_bar = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        self.right_bar.grid(row=0, column=3, sticky="e")

        self.modelo_label = ctk.CTkLabel(
            self.right_bar,
            text="Modelo:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.modelo_label.pack(side="top", anchor="e")

        # ======= CONTENIDO PRINCIPAL =======
        self.main_content = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.main_content.pack(expand=True, fill="both", padx=60, pady=(30, 0))

        self.info_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        self.info_frame.pack(side="top", fill="both", pady=(0, 10), expand=True)

        self.info_frame.grid_columnconfigure(0, weight=1)
        self.info_frame.grid_columnconfigure(1, weight=1)

        label_font = ctk.CTkFont(size=18, weight="bold")
        label_fontInfo = ctk.CTkFont(size=30, weight="bold")
        label_color = "#37474F"

        self.snInfo = ctk.CTkLabel(self.info_frame, text="SN:", font=label_fontInfo, text_color=label_color, anchor="w")
        self.snInfo.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.macInfo = ctk.CTkLabel(self.info_frame, text="MAC:", font=label_fontInfo, text_color=label_color, anchor="w")
        self.macInfo.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.sftInfo = ctk.CTkLabel(self.info_frame, text="SOFTWARE:", font=label_font, text_color=label_color, anchor="w")
        self.sftInfo.grid(row=2, column=0, sticky="w", pady=(5, 5))
        self.w24Info = ctk.CTkLabel(self.info_frame, text="WIFI 2.4 GHz:", font=label_font, text_color=label_color, anchor="w")
        self.w24Info.grid(row=3, column=0, sticky="w", pady=5)
        self.w5Info = ctk.CTkLabel(self.info_frame, text="WIFI 5 GHz:", font=label_font, text_color=label_color, anchor="w")
        self.w5Info.grid(row=4, column=0, sticky="w", pady=5)
        self.pswInfo = ctk.CTkLabel(self.info_frame, text="Password:", font=label_font, text_color=label_color, anchor="w")
        self.pswInfo.grid(row=5, column=0, sticky="w", pady=(5, 0))

        self.txInfo = ctk.CTkLabel(self.info_frame, text="Fo TX:", font=label_font, text_color=label_color, anchor="w")
        self.txInfo.grid(row=2, column=1, sticky="w", padx=(40, 0), pady=(5, 5))
        self.rxInfo = ctk.CTkLabel(self.info_frame, text="Fo Rx:", font=label_font, text_color=label_color, anchor="w")
        self.rxInfo.grid(row=3, column=1, sticky="w", padx=(40, 0), pady=5)
        self.usbInfo = ctk.CTkLabel(self.info_frame, text="Usb Port:", font=label_font, text_color=label_color, anchor="w")
        self.usbInfo.grid(row=4, column=1, sticky="w", padx=(40, 0), pady=(5, 0))

        self.contador_pruebas_frame = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.contador_pruebas_frame.grid(row=5, column=1, sticky="w", padx=(40, 0), pady=(5, 0))

        self.contador_pruebas_label = ctk.CTkLabel(
            self.contador_pruebas_frame,
            text="Contador de pruebas:",
            font=label_font,
            text_color=label_color,
        )
        self.contador_pruebas_label.pack(side="left")

        self.contador_pruebas_valor = ctk.CTkLabel(
            self.contador_pruebas_frame,
            text="0",
            font=label_font,
            text_color=label_color,
        )
        self.contador_pruebas_valor.pack(side="left", padx=(10, 0))

        self.panel_pruebas = PanelPruebasConexion(
            self.main_content,
            modelo=None,
            on_run_unit=self._run_unit_from_panel
        )
        self.panel_pruebas.pack(side="bottom", fill="x", padx=0, pady=(0, 10))

        # Iniciar reloj
        self.update_clock()

        # Responsivo
        self.bind("<Configure>", self._on_resize)

        # Cargar usuario
        self.after(50, self._cargar_usuario_desde_root)

        # Rows info
        self.info_frame.grid_rowconfigure(0, weight=3, minsize=60)
        self.info_frame.grid_rowconfigure(1, weight=3, minsize=60)
        self.info_frame.grid_rowconfigure(2, weight=1)
        self.info_frame.grid_rowconfigure(3, weight=1)
        self.info_frame.grid_rowconfigure(4, weight=1)
        self.info_frame.grid_rowconfigure(5, weight=1)

        # ✅ aplicar tema si existe
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            try:
                self.apply_theme(root.theme.palette())
            except Exception:
                pass

    # ==================================================
    # THEME
    # ==================================================
    def apply_theme(self, p: dict):
        """
        Aplica paleta del ThemeManager a TesterView.
        Se llama desde root.refresh_theme() cuando el usuario hace toggle.
        """
        root = self.winfo_toplevel()
        mode = getattr(getattr(root, "theme", None), "mode", "light")

        # Fondo base
        self.configure(fg_color=p.get("bg", "transparent"))

        # Sidebar / scroll
        try:
            if mode == "dark":
                # en oscuro conviene que sidebar sea "card" para contraste
                self.left_scroll.configure(fg_color=p.get("card", "#0F172A"))
            else:
                # en claro: igual al bg (el verdosito/clarito que ves arriba)
                self.left_scroll.configure(fg_color=p.get("bg", "#E8F4F8"))
        except Exception:
            pass
        try:
            self.logo_frame.configure(fg_color=p.get("card", "#FFFFFF"))
        except Exception:
            pass

        # Toggle sidebar
        self.toggle_btn.configure(
            fg_color=p.get("primary", "#4EA5D9"),
            hover_color=p.get("primary_hover", "#3B8CC2"),
            text_color="white",
        )

        # OptionMenu
        if mode == "dark":
            self.modo_menu.configure(
                fg_color=p.get("panel", "#111827"),
                text_color=p.get("text", "#E5E7EB"),
                button_color=p.get("primary", "#60A5FA"),
                button_hover_color=p.get("primary_hover", "#3B82F6"),
                dropdown_fg_color=p.get("panel", "#111827"),
                dropdown_hover_color=p.get("card", "#0F172A"),
                dropdown_text_color=p.get("text", "#E5E7EB"),
            )
        else:
            self.modo_menu.configure(
                fg_color="#4EA5D9",
                text_color="white",
                button_color="#3B8CC2",
                button_hover_color="#2F6FA0",
                dropdown_fg_color="#4EA5D9",
                dropdown_hover_color="#3B8CC2",
                dropdown_text_color="white",
            )

        # Textos usuario
        self.label_usuario_id.configure(text_color=p.get("text", "#2C3E50"))
        self.label_usuario_nombre.configure(text_color=p.get("text", "#2C3E50"))

        # Frame derecho
        self.right_frame.configure(fg_color=p.get("panel", "#E9F5FF"))

        # Top bar labels
        self.prueba_static_label.configure(text_color=p.get("text", "#2C3E50"))
        self.clock_label.configure(text_color=p.get("text", "#2C3E50"))
        self.modelo_label.configure(text_color=p.get("text", "#2C3E50"))

        # Info labels
        label_color = p.get("text", "#37474F")
        for attr in [
            "snInfo", "macInfo", "sftInfo", "w24Info", "w5Info",
            "pswInfo", "txInfo", "rxInfo", "usbInfo",
            "contador_pruebas_label", "contador_pruebas_valor"
        ]:
            if hasattr(self, attr):
                getattr(self, attr).configure(text_color=label_color)

        # Estado de prueba (solo si está default)
        try:
            if self.estado_prueba_label.cget("text") == "SIN EJECUTAR" and mode == "dark":
                self.estado_prueba_label.configure(text_color="#FBBF24")
        except Exception:
            pass

        # Menú superior
        try:
            if hasattr(self.menu_superior, "apply_theme"):
                self.menu_superior.apply_theme(p)
        except Exception:
            pass

        # Panel inferior
        try:
            if hasattr(self.panel_pruebas, "apply_theme"):
                self.panel_pruebas.apply_theme(p)
        except Exception:
            pass

    # ====== toggle_sidebar ======
    def toggle_sidebar(self):
        self.sidebar_visible = not self.sidebar_visible
        if self.sidebar_visible:
            self.grid_columnconfigure(0, minsize=280)
            self.left_scroll.configure(width=280)
            self.toggle_btn.configure(text="◀")
        else:
            self.grid_columnconfigure(0, minsize=0)
            self.left_scroll.configure(width=0)
            self.toggle_btn.configure(text="▶")

    # ===================== USUARIO =====================
    def _cargar_usuario_desde_root(self):
        root = self.winfo_toplevel()
        user_id = getattr(root, "current_user_id", None)
        user_name = getattr(root, "current_user_name", None)
        if user_id and user_name:
            self.set_usuario(str(user_id), str(user_name))

    def set_usuario(self, user_id: str, nombre: str):
        self.label_usuario_id.configure(text=f"ID: {user_id}")
        self.label_usuario_nombre.configure(text=f"HOLA: {nombre}")

    # ===================== REINICIO =====================
    def ir_reinicio(self):
        parent = self.master
        root = self.winfo_toplevel()

        modo_actual = self.modo_var.get()
        user_id = getattr(root, "current_user_id", None)
        user_name = getattr(root, "current_user_name", None)
        init_kwargs = getattr(self, "_init_kwargs", {}) or {}

        VALIDOS = {"Testeo", "Retesteo", "Etiqueta", "Monitoreo"}
        if modo_actual not in VALIDOS:
            return

        try:
            self.destroy()
        except Exception:
            pass

        nueva = TesterView(parent, mdebug=None, **init_kwargs)
        setattr(root, "current_user_id", user_id)
        setattr(root, "current_user_name", user_name)

        nueva.pack(fill="both", expand=True)
        parent.dispatcher.set_target(nueva)

        def _restore():
            nueva.modo_var.set(modo_actual)
            nueva.cambiar_modo(modo_actual)

        nueva.after(0, _restore)

        # ✅ re-aplicar tema
        if hasattr(root, "theme"):
            try:
                nueva.apply_theme(root.theme.palette())
            except Exception:
                pass

    # ===================== NAVEGACIÓN =====================
    def _swap_view(self, view_cls, **init_kwargs):
        parent = self.master
        # ✅ tomar root ANTES de destruir (self puede quedar inválido)
        root = parent.winfo_toplevel()

        try:
            self.destroy()
        except Exception:
            pass

        nueva = view_cls(parent, modelo=None, **init_kwargs)
        nueva.pack(fill="both", expand=True)

        if hasattr(parent, "dispatcher") and parent.dispatcher:
            parent.dispatcher.set_target(nueva)

        # ✅ aplicar tema si existe (usa root, no self)
        if hasattr(root, "theme") and hasattr(nueva, "apply_theme"):
            try:
                nueva.apply_theme(root.theme.palette())
            except Exception:
                pass

    def ir_a_ont_tester(self):
        pass

    def ir_a_base_diaria(self):
        from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        self._swap_view(EscaneosDiaView)

    def ir_a_base_global(self):
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        from src.Frontend.ui.propiedades_view import TesterMainView
        self._swap_view(TesterMainView)

    def ir_salir(self):
        from src.Frontend.ui.inicio_view import InicioView
        self._swap_view(InicioView)

    # ===================== ESTILO / UI =====================
    def _set_button_style(self, button, state: str):
        if state == "active":
            fg = self.color_activo_fg
            hover = self.color_activo_hover
            status = "normal"
        elif state == "inactive":
            fg = self.color_inactivo_fg
            hover = self.color_inactivo_hover
            status = "disabled"
        else:
            fg = self.color_neutro_fg
            hover = self.color_neutro_hover
            status = "normal"
        button.configure(fg_color=fg, hover_color=hover, state=status)

    def _set_all_buttons_state(self, state: str):
        self._set_button_style(self.btn_omitir, state)
        self._set_button_style(self.btn_ethernet, state)
        self._set_button_style(self.btn_conectividad, state)
        self._set_button_style(self.btn_otros_puertos, state)
        self._set_button_style(self.btn_wifi, state)

    def _on_resize(self, event):
        if event.widget is not self:
            return
        if not getattr(self, "sidebar_visible", True):
            self.grid_columnconfigure(0, minsize=0)
            self.left_scroll.configure(width=0)
            return

        width = max(event.width, 400)
        if width < 950:
            sidebar_width = 280
        else:
            sidebar_width = int(width * 0.22)
            sidebar_width = max(280, min(sidebar_width, 320))
        self.grid_columnconfigure(0, minsize=sidebar_width)
        self.left_scroll.configure(width=sidebar_width)

    def update_clock(self):
        now = datetime.now()
        time_string = now.strftime("%I:%M %p  %d %B %Y")
        meses = {
            "January": "enero", "February": "febrero", "March": "marzo",
            "April": "abril", "May": "mayo", "June": "junio",
            "July": "julio", "August": "agosto", "September": "septiembre",
            "October": "octubre", "November": "noviembre", "December": "diciembre",
        }
        for eng, esp in meses.items():
            time_string = time_string.replace(eng, esp)

        self.clock_label.configure(text=time_string)
        self.after(1000, self.update_clock)

    # ------------------------------------------------------------
    # TODO: DE AQUÍ HACIA ABAJO CONSERVA TU LÓGICA.
    # Solo corregí indentaciones/bugs y apliqué theme.
    # ------------------------------------------------------------

    def cambiar_modo(self, modo: str):
        self.stop_event.set()

        if getattr(self, "_unit_stop_event", None) is not None:
            self._unit_stop_event.set()
            self._unit_stop_event = None

        print(f"     Modo seleccionado: {modo}")
        self._set_all_buttons_state("neutral")

        if modo == "Testeo":
            self._set_button_style(self.btn_omitir, "active")
            self._set_button_style(self.btn_conectividad, "active")
            self._set_button_style(self.btn_otros_puertos, "active")
            self._set_button_style(self.btn_ethernet, "inactive")
            self._set_button_style(self.btn_wifi, "inactive")
        elif modo == "Retesteo":
            self._set_button_style(self.btn_omitir, "inactive")
            self._set_button_style(self.btn_conectividad, "active")
            self._set_button_style(self.btn_otros_puertos, "active")
            self._set_button_style(self.btn_ethernet, "active")
            self._set_button_style(self.btn_wifi, "active")
        elif modo in ("Etiqueta", "Monitoreo"):
            self._set_all_buttons_state("inactive")

        if modo in ("Testeo", "Retesteo"):
            self.setOpcionesView(auto_test_on_detect=True)
        elif modo == "Monitoreo":
            self._start_monitor_loop()
            return
        else:
            self.setOpcionesView(auto_test_on_detect=False)

    def _start_monitor_loop(self):
        self.stop_event = threading.Event()
        from src.backend.endpoints.monitoreo import iniciar_monitoreo
        self.tester_thread = threading.Thread(
            target=iniciar_monitoreo,
            args=(self.master.event_q, self.stop_event),
            daemon=True
        )
        self.tester_thread.start()

    def setOpcionesView(self, auto_test_on_detect: bool = True):
        self._start_loop(auto_test_on_detect=auto_test_on_detect)

    def _get_loop_flags(self):
        resetFabrica = (self.btn_omitir.cget("state") == "normal")
        fibra = (self.btn_conectividad.cget("state") == "normal")
        usb = (self.btn_otros_puertos.cget("state") == "normal")
        wifi = (self.btn_wifi.cget("state") == "normal")
        return resetFabrica, usb, fibra, wifi

    def _start_loop(self, auto_test_on_detect: bool, start_in_monitor: bool = False):
        if self.tester_thread and self.tester_thread.is_alive():
            self.tester_thread.join(timeout=5)
            if self.tester_thread.is_alive():
                print("[WARN] El hilo anterior no terminó. No se crea duplicado.")
                return

        self.stop_event = threading.Event()
        resetFabrica, usb, fibra, wifi = self._get_loop_flags()

        self.tester_thread = threading.Thread(
            target=iniciar_testerConexion,
            args=(resetFabrica, usb, fibra, wifi, self.master.event_q, self.stop_event),
            kwargs={
                "auto_test_on_detect": auto_test_on_detect,
                "start_in_monitor": start_in_monitor,
            },
            daemon=True
        )
        self.tester_thread.start()

    def _stop_mode_loop(self):
        try:
            self.stop_event.set()
            t = getattr(self, "_mode_thread", None)
            if t and t.is_alive():
                t.join(timeout=15)
        except Exception:
            pass
        finally:
            self._mode_thread = None

    def _run_unit_from_panel(self, reset, soft, usb, fibra, wifi, modelo):
        self.stop_event.set()
        prev_thread = self.tester_thread

        unit_stop = threading.Event()
        self._unit_stop_event = unit_stop
        self._unit_running = True

        self._suppress_cleanup_until = time.time() + 60

        def worker():
            try:
                if prev_thread and prev_thread.is_alive():
                    self.master.event_q.put(("log", "Deteniendo ciclo actual para ejecutar unitaria..."))
                    prev_thread.join(timeout=20)

                if prev_thread and prev_thread.is_alive():
                    self.master.event_q.put(("log", "No se pudo detener el ciclo anterior. Ignorando unitaria."))
                    return

                from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
                iniciar_pruebaUnitariaConexion(
                    reset, soft, usb, fibra, wifi,
                    model=modelo,
                    out_q=self.master.event_q,
                    stop_event=unit_stop
                )

            finally:
                self._unit_running = False
                if self._unit_stop_event is unit_stop:
                    self._unit_stop_event = None

                if not unit_stop.is_set():
                    self.master.event_q.put(("resume_monitor", None))

        threading.Thread(target=worker, daemon=True).start()

    def _disparar_prueba(self, nombre_prueba: str):
        print(f"Solicitando backend: {nombre_prueba}")
        if self.viewmodel and hasattr(self.viewmodel, "ejecutar_prueba"):
            try:
                self.viewmodel.ejecutar_prueba(nombre_prueba)
            except TypeError:
                self.viewmodel.ejecutar_prueba()

    def ir_OMITIR(self):
        self._disparar_prueba("OMITIR RETEST DE FÁBRICA")

    def ir_ethernet(self):
        self._disparar_prueba("PRUEBA DE ETHERNET")

    def ir_conectividad(self):
        self._disparar_prueba("PRUEBA DE CONECTIVIDAD")

    def ir_otros_puertos(self):
        self._disparar_prueba("PRUEBA DE OTROS PUERTOS")

    def ir_senales_wifi(self):
        self._disparar_prueba("PRUEBA DE SEÑALES WIFI")

    def destroy(self):
        try:
            if getattr(self, "stop_event", None) is not None:
                self.stop_event.set()
        except Exception:
            pass

        try:
            if getattr(self, "_unit_stop_event", None) is not None:
                self._unit_stop_event.set()
                self._unit_stop_event = None
        except Exception:
            pass

        super().destroy()

    def on_event(self, kind, payload):
        if kind == "log":
            self.panel_pruebas.set_texto_superior(payload)

        elif kind == "logSuper":
            self.modelo_label.configure(text="Modelo: " + str(payload))
            self.modelo_detectado = payload
            self.panel_pruebas.modelo = payload

        elif kind == "pruebas":
            self.panel_pruebas.set_texto_inferior(payload)

        elif kind == "con":
            payload_lower = str(payload).lower()
            if "desconectado" in payload_lower:
                self.panel_pruebas.actualizar_estado_conexion(False)
                self._limpiezaElementos()
            else:
                self.panel_pruebas.actualizar_estado_conexion(True)

        elif kind == "resultados":
            from_unit = getattr(self, "_unit_running", False)
            self._render_resultados(payload, from_unit_test=from_unit)

            from src.backend.sua_client.dao import insertar_operacion, extraer_by_id
            modo = self.modo_var.get()
            root = self.winfo_toplevel()
            user_id = int(getattr(root, "current_user_id", None))
            id_ = insertar_operacion(payload, modo, user_id)
            _ = extraer_by_id(id_, "operations")

        elif kind == "test_individual":
            test_name = payload.get("name", "").lower()
            status = payload.get("status", "FAIL")
            name_to_key = {
                "ping": "ping",
                "ping_connectivity": "ping",
                "factory_reset": "factory_reset",
                "software_update": "software_update",
                "usb_port": "usb_port",
                "tx_power": "tx_power",
                "rx_power": "rx_power",
                "wifi_24ghz": "wifi_24ghz_signal",
                "wifi_5ghz": "wifi_5ghz_signal",
            }
            btn_key = name_to_key.get(test_name, test_name)
            self.panel_pruebas._set_button_status(btn_key, status)

        elif kind == "resume_monitor":
            modo = self.modo_var.get()
            auto = (modo in ("Testeo", "Retesteo"))
            self._start_loop(auto_test_on_detect=auto, start_in_monitor=True)

    def _limpiezaElementos(self):
        self.snInfo.configure(text="SN: ")
        self.macInfo.configure(text="MAC: ")
        self.sftInfo.configure(text="SOFTWARE: ")
        self.w24Info.configure(text="WIFI 2.4GHz: ")
        self.w5Info.configure(text="WIFI 5 GHz: ")
        self.pswInfo.configure(text="Password: ")
        self.txInfo.configure(text="Fo TX: —")
        self.rxInfo.configure(text="Fo RX: —")
        self.usbInfo.configure(text="Usb Port: ")
        self.estado_prueba_label.configure(text="SIN EJECUTAR", text_color="#f1c40f")
        self.modelo_label.configure(text="Modelo: ")
        self.panel_pruebas.set_texto_superior("-")
        self.panel_pruebas.set_texto_inferior("-")

        self.panel_pruebas._set_button_status("ping", "reset")
        self.panel_pruebas._set_button_status("factory_reset", "reset")
        self.panel_pruebas._set_button_status("software_update", "reset")
        self.panel_pruebas._set_button_status("usb_port", "reset")
        self.panel_pruebas._set_button_status("tx_power", "reset")
        self.panel_pruebas._set_button_status("rx_power", "reset")
        self.panel_pruebas._set_button_status("wifi_24ghz_signal", "reset")
        self.panel_pruebas._set_button_status("wifi_5ghz_signal", "reset")

    def _render_resultados(self, payload, from_unit_test: bool = False):
        print("La payload recibida es: " + str(payload))
        info = payload.get("info", {})
        tests = payload.get("tests", {})

        if self.modo_var.get() == "Etiqueta" and not from_unit_test:
            from src.backend.endpoints.conexion import generaEtiquetaTxt
            generaEtiquetaTxt(payload)

        self.panel_pruebas.modelo = info.get("modelo", "—")

        sn = info.get("sn", "—")
        mac = info.get("mac", "—")
        sftver = info.get("sftVer", "—")
        wifi24 = info.get("wifi24", "—")
        wifi5 = info.get("wifi5", "—")
        passWi = info.get("passWifi", "—")

        def set_if_present(test_key, btn_key):
            if test_key not in tests:
                return
            val = tests.get(test_key)
            if val is None or val == "SIN PRUEBA":
                return
            self.panel_pruebas._set_button_status(btn_key, val)

        set_if_present("ping", "ping")
        set_if_present("reset", "factory_reset")
        set_if_present("sftU", "software_update")
        set_if_present("usb", "usb_port")
        set_if_present("w24", "wifi_24ghz_signal")
        set_if_present("w5", "wifi_5ghz_signal")

        def _to_float_safe(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        from src.backend.endpoints.conexion import cargarConfig
        config = cargarConfig()
        fibra_cfg = config.get("fibra", {})
        mintx = float(fibra_cfg.get("mintx", 0.0))
        maxtx = float(fibra_cfg.get("maxtx", 1.0))
        minrx = float(fibra_cfg.get("minrx", 0.0))
        maxrx = float(fibra_cfg.get("maxrx", 1.0))

        if "tx" in tests:
            tx = tests.get("tx")
            self.txInfo.configure(text=("Fo TX: —" if tx in (False, None) else f"Fo TX: {tx} dBm"))
            txv = _to_float_safe(tx)
            txp = bool(txv is not None and mintx <= txv <= maxtx)
            self.panel_pruebas._set_button_status("tx_power", txp)

        if "rx" in tests:
            rx = tests.get("rx")
            self.rxInfo.configure(text=("Fo RX: —" if rx in (False, None) else f"Fo RX: {rx} dBm"))
            rxv = _to_float_safe(rx)
            rxp = bool(rxv is not None and minrx <= rxv <= maxrx)
            self.panel_pruebas._set_button_status("rx_power", rxp)

        if "usb" in tests:
            usb = tests.get("usb")
            if usb == "SIN PRUEBA":
                usb_label = "Prueba omitida"
            elif usb == "PASS" or usb is True:
                usb_label = "USB detectada"
            else:
                usb_label = "USB no detectada"
            self.usbInfo.configure(text="Usb Port: " + str(usb_label))

        self.snInfo.configure(text="SN: " + str(sn))
        self.macInfo.configure(text="MAC: " + str(mac))
        self.sftInfo.configure(text="SOFTWARE: " + str(sftver))
        self.w24Info.configure(text="WIFI 2.4GHz: " + str(wifi24))
        self.w5Info.configure(text="WIFI 5 GHz: " + str(wifi5))
        self.pswInfo.configure(text="Password: " + str(passWi))

        self.estado_prueba_label.configure(text="EJECUTADO", text_color="#6B9080")


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Tester View")
    app.geometry("1200x600")
    app.minsize(900, 550)

    # Simular sesión
    app.current_user_id = "09"
    app.current_user_name = "Ram"

    view = TesterView(app, mdebug=None)
    view.pack(fill="both", expand=True)
    app.mainloop()
