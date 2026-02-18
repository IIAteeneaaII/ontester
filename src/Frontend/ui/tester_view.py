from src.backend.endpoints.conexion import iniciar_testerConexion
import customtkinter as ctk
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image
# Para correr el back  y actualizar elementos
import threading
import queue
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
    def __init__(self, parent, mdebug, viewmodel=None, **kwargs):
        
        #Vista
        super().__init__(parent, fg_color="#E3F7F2", **kwargs)

        self.viewmodel = viewmodel
        # Los kwargs
        self._init_kwargs = dict(kwargs)   
        # Para la queue
        self._polling = False # ya no se usará
        self.stop_event = threading.Event()  # Para cancelar hilos al cambiar de modo
        self.tester_thread = None # Hilo actual del tester
        self.modelo_detectado = None  # Se actualiza cuando el backend detecta el modelo
        self._mode_tread = None  # Hilo del modo actual (testeo/monitor)
        self._unit_tread = None  # Hilo de la prueba unitaria
        self._unit_stop_event = None  # Evento de parada para la unitaria
        self._unit_running = False
        self._suppress_cleanup_until = 0.0
        # Paleta de colores para estados de botones (pastel)
        self.color_neutro_fg = "#4EA5D9"
        self.color_neutro_hover = "#3B8CC2"
        self.color_activo_fg = "#6FCF97"
        self.color_activo_hover = "#56B27D"
        self.color_inactivo_fg = "#F28B82"
        self.color_inactivo_hover = "#E0665C"

        # ====== SOLO AGREGADO (1/4): estado sidebar + grid para toggle ======
        self.sidebar_visible = True
        # Layout general: columna 0 = sidebar, columna 1 = contenido
        self.grid_columnconfigure(0, weight=0, minsize=280)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=0)  # toggle
        self.grid_rowconfigure(1, weight=1)  # contenido
        # ================================================================

        # ========= ASSETS =========
        assets_dir = Path(__file__).parent.parent / "assets" / "icons"
        logo_path = assets_dir / "logo_tester.png"
        # ==========================

        # ====== SOLO AGREGADO (2/4): botón toggle esquina sup izq ======
        self.toggle_btn = ctk.CTkButton(
        self, text="◀", width=28, height=28,
        corner_radius=6,
        fg_color=self.color_activo_fg,        # <- verde clarito
        hover_color=self.color_activo_hover,  # <- verde hover
        text_color="white", command=self.toggle_sidebar
        )

        self.toggle_btn.grid(row=0, column=0, sticky="nw", padx=6, pady=6)
        # ============================================================

        # ======= SIDEBAR CON SCROLL =======
        self.left_scroll = ctk.CTkScrollableFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color="#E3F7F2",
        )
        self.left_scroll.grid(row=1, column=0, sticky="nsw", padx=0, pady=0)
        left_frame = self.left_scroll
        # ==================================

        # ===== Logo circular superior =====
        try:
            self.logo_image = ctk.CTkImage(
                light_image=Image.open(logo_path),
                dark_image=Image.open(logo_path),
                size=(48, 48),
            )
        except Exception:
            self.logo_image = None

        logo_frame = ctk.CTkFrame(left_frame, width=70, height=70, corner_radius=35, fg_color="#FFFFFF")
        logo_frame.pack(pady=(15, 5))
        logo_frame.pack_propagate(False)

        ctk.CTkLabel(logo_frame, text="", image=self.logo_image).pack(expand=True)
        # ==================================

        # ===== Menú desplegable "Escoge el modo" =====
        self.modo_var = ctk.StringVar(value="Escoge el modo")
        self.modo_menu = ctk.CTkOptionMenu(
            left_frame,
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

        # ====== Bloque de usuario + botón SALIR ======
        self.user_block = ctk.CTkFrame(left_frame, fg_color="transparent")
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
            fg_color="#9B59B6",      # morado
            hover_color="#8E44AD",   # morado hover
            text_color="white",
            font=ctk.CTkFont(size=13, weight="bold"),
            corner_radius=6,
            height=32,
            command=self.ir_reinicio,  
        )
        self.btn_reinicio.pack(fill="x", pady=(8, 0))

        # =============================================

        # Estado inicial de los botones
        self._set_all_buttons_state("neutral")

        # ===== Frame derecho (contenido principal) =====
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#D2E3EC")
        self.right_frame.grid(row=0, column=1, rowspan=2, sticky="nsew", padx=0, pady=0)

        # ========= BARRA SUPERIOR =========
        top_bar = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=20, padx=40)

        top_bar.grid_columnconfigure(0, weight=0)  # menú
        top_bar.grid_columnconfigure(1, weight=0)  # estado prueba
        top_bar.grid_columnconfigure(2, weight=1)  # reloj
        top_bar.grid_columnconfigure(3, weight=0)  # modelo

        # Menú hamburguesa
        self.menu_superior = MenuSuperiorDesplegable(
            top_bar,
            on_open_tester=self.ir_a_ont_tester,
            on_open_base_diaria=self.ir_a_base_diaria,
            on_open_base_global=self.ir_a_base_global,
            on_open_otros=self.ir_a_otros,
        )
        self.menu_superior.grid(row=0, column=0, sticky="w", padx=(0, 15))

        # Estado de prueba (NO se auto-cambia aquí; backend lo debe actualizar)
        left_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_bar.grid(row=0, column=1, sticky="w")

        ctk.CTkLabel(
            left_bar,
            text="Prueba:",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#2C3E50",
        ).pack(side="left")

        self.estado_prueba_label = ctk.CTkLabel(
            left_bar,
            text="SIN EJECUTAR",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#f1c40f",
        )
        self.estado_prueba_label.pack(side="left", padx=(10, 0))

        # Reloj
        center_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        center_bar.grid(row=0, column=2, sticky="ew")

        self.clock_label = ctk.CTkLabel(
            center_bar,
            text="",
            font=ctk.CTkFont(size=20),
            text_color="#2C3E50",
        )
        self.clock_label.pack()

        # Modelo (solo texto; backend puede actualizarlo)
        right_bar = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_bar.grid(row=0, column=3, sticky="e")

        self.modelo_label = ctk.CTkLabel(
            right_bar,
            text="Modelo:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.modelo_label.pack(side="top", anchor="e")
        # ===================================

        # ======= CONTENIDO PRINCIPAL =======
        self.main_content = ctk.CTkFrame(self.right_frame, fg_color="transparent")
        self.main_content.pack(expand=True, fill="both", padx=60, pady=(30, 0))

        info_frame = ctk.CTkFrame(self.main_content, fg_color="transparent")
        info_frame.pack(side="top", fill="both", pady=(0, 10), expand=True)

        info_frame.grid_columnconfigure(0, weight=1)
        info_frame.grid_columnconfigure(1, weight=1)

        label_font = ctk.CTkFont(size=18, weight="bold")
        label_fontInfo = ctk.CTkFont(size=30, weight="bold")
        label_color = "#37474F"

        self.snInfo = ctk.CTkLabel(info_frame, text="SN:", font=label_fontInfo, text_color=label_color, anchor="w")
        self.snInfo.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.macInfo = ctk.CTkLabel(info_frame, text="MAC:", font=label_fontInfo, text_color=label_color, anchor="w")
        self.macInfo.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 5))
        self.sftInfo = ctk.CTkLabel(info_frame, text="SOFTWARE:", font=label_font, text_color=label_color, anchor="w")
        self.sftInfo.grid(row=2, column=0, sticky="w", pady=(5, 5))
        self.w24Info = ctk.CTkLabel(info_frame, text="WIFI 2.4 GHz:", font=label_font, text_color=label_color, anchor="w")
        self.w24Info.grid(row=3, column=0, sticky="w", pady=5)
        self.w5Info = ctk.CTkLabel(info_frame, text="WIFI 5 GHz:", font=label_font, text_color=label_color, anchor="w")
        self.w5Info.grid(row=4, column=0, sticky="w", pady=5)
        self.pswInfo = ctk.CTkLabel(info_frame, text="Password:", font=label_font, text_color=label_color, anchor="w")
        self.pswInfo.grid(row=5, column=0, sticky="w", pady=(5, 0))

        self.txInfo = ctk.CTkLabel(info_frame, text="Fo TX:", font=label_font, text_color=label_color, anchor="w")
        self.txInfo.grid(row=2, column=1, sticky="w", padx=(40, 0), pady=(5, 5))
        self.rxInfo = ctk.CTkLabel(info_frame, text="Fo Rx:", font=label_font, text_color=label_color, anchor="w")
        self.rxInfo.grid(row=3, column=1, sticky="w", padx=(40, 0), pady=5)
        self.usbInfo = ctk.CTkLabel(info_frame, text="Usb Port:", font=label_font, text_color=label_color, anchor="w")
        self.usbInfo.grid(row=4, column=1, sticky="w", padx=(40, 0), pady=(5, 0))
        # ===== Contador de pruebas (debajo de Usb Port) =====
        self.contador_pruebas_frame = ctk.CTkFrame(info_frame, fg_color="transparent")
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
            text="0",  # valor inicial 
            font=label_font,
            text_color=label_color,
        )
        self.contador_pruebas_valor.pack(side="left", padx=(10, 0))


        # Panel inferior
        self.panel_pruebas = PanelPruebasConexion(
            self.main_content,
            modelo=None,
            on_run_unit=self._run_unit_from_panel  # Callback
        )
        self.panel_pruebas.pack(side="bottom", fill="x", padx=0, pady=(0, 10)) #, expand=False

        # Inicializar contador
        self.updatePruebas()

        # Iniciar reloj
        self.update_clock()

        # Responsivo
        self.bind("<Configure>", self._on_resize)

        # Cargar usuario desde InicioView (root.current_user_id / root.current_user_name)
        self.after(50, self._cargar_usuario_desde_root)

        # Configurar las rows de info
        info_frame.grid_rowconfigure(0, weight=3, minsize=60)  # SN:  fila grande
        info_frame.grid_rowconfigure(1, weight=3, minsize=60)  # MAC: fila grande
        info_frame.grid_rowconfigure(2, weight=1)
        info_frame.grid_rowconfigure(3, weight=1)
        info_frame.grid_rowconfigure(4, weight=1)
        info_frame.grid_rowconfigure(5, weight=1)

    # ====== SOLO AGREGADO (3/4): toggle_sidebar ======
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
    # ==================================================

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

    # FUNCION DE REINICIO FORZOSO
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
        # 6) Montar UI y actualizar dispatcher
        nueva.pack(fill="both", expand=True)
        parent.dispatcher.set_target(nueva)

        # 7) Restaurar modo y arrancarlo (mejor con after para evitar race)
        def _restore():
            nueva.modo_var.set(modo_actual)
            nueva.cambiar_modo(modo_actual)

        nueva.after(0, _restore)

    # ===================== NAVEGACIÓN =====================
    def _swap_view(self, view_cls, **init_kwargs):
        parent = self.master
        try:
            self.destroy()
        except Exception:
            pass
        nueva = view_cls(parent, modelo=None, **init_kwargs)
        nueva.pack(fill="both", expand=True)

        # El dispatcher del parent ahora apunta a la nueva vista
        parent.dispatcher.set_target(nueva)
    def ir_a_ont_tester(self):
        pass

    def ir_a_base_diaria(self):
        try:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        except ImportError:
            from src.Frontend.ui.escaneos_dia_view import EscaneosDiaView
        self._swap_view(EscaneosDiaView)

    def ir_a_base_global(self):
        from src.Frontend.ui.reporte_global_view import ReporteGlobalView
        self._swap_view(ReporteGlobalView)

    def ir_a_otros(self):
        from src.Frontend.ui.propiedades_view import TesterMainView
        self._swap_view(TesterMainView)

    def ir_salir(self):
        # Regresar a InicioView (NO cerrar app)
        from src.Frontend.ui.inicio_view import InicioView
        self._swap_view(InicioView)

    # ===================== Actualizar contador de pruebas ========
    def updatePruebas(self):
        # Llamar a la dao que me trae la consulta con el numero
        from src.backend.sua_client.dao import get_pruebas_validas
        pruebas = get_pruebas_validas()
        self.contador_pruebas_valor.configure(text=str(pruebas))
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
        # ====== SOLO AGREGADO (4/4): respetar sidebar_visible ======
        if not getattr(self, "sidebar_visible", True):
            self.grid_columnconfigure(0, minsize=0)
            self.left_scroll.configure(width=0)
            return
        # ==========================================================
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
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre',
        }
        for eng, esp in meses.items():
            time_string = time_string.replace(eng, esp)

        self.clock_label.configure(text=time_string)
        self.after(1000, self.update_clock)

    # ... (TODO TU CÓDIGO RESTANTE EXACTAMENTE IGUAL)
    # (No modifiqué nada más)


    def cambiar_modo(self, modo: str):
        self.stop_event.set()  # Señal de parar al hilo anterior (modo)

        # Cancelar también la unitaria si hay una corriendo
        if getattr(self, "_unit_stop_event", None) is not None:
            self._unit_stop_event.set()
            self._unit_stop_event = None

        # NO crear nuevo stop_event aquí - _start_loop lo hará después de verificar
        # que el hilo anterior murió
        # Limpiar la UI
        self._limpiezaElementos()

        print(f"     Modo seleccionado: {modo}")
        self._set_all_buttons_state("neutral")

        if modo == "Testeo":
            self._set_button_style(self.btn_omitir, "active")
            self._set_button_style(self.btn_conectividad, "active")
            self._set_button_style(self.btn_otros_puertos, "active")
            self._set_button_style(self.btn_ethernet, "inactive")
            self._set_button_style(self.btn_wifi, "inactive")
        elif modo == "Retesteo":
            # self._set_all_buttons_state("active")
            self._set_button_style(self.btn_omitir, "inactive")
            self._set_button_style(self.btn_conectividad, "active")
            self._set_button_style(self.btn_otros_puertos, "active")
            self._set_button_style(self.btn_ethernet, "active")
            self._set_button_style(self.btn_wifi, "active")
        elif modo == "Etiqueta":
            self._set_all_buttons_state("inactive")
        elif modo == "Monitoreo":
            self._set_all_buttons_state("inactive")
        # Arrancar loop según modo:
        # - Testeo / Retesteo: sí corre pruebas completas al detectar
        # - Etiqueta: normalmente NO corre pruebas (monitor)
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
            args=(self.master.event_q, self.stop_event),  # pásalo también
            daemon=True
        )
        self.tester_thread.start()

    def setOpcionesView(self, auto_test_on_detect: bool = True):
        # Arranca/reanuda el loop según el modo (auto-test o monitor)
        self._start_loop(auto_test_on_detect=auto_test_on_detect)

        '''# 1) Leer estados (strings) y convertir a bool
        resetFabrica = (self.btn_omitir.cget("state") == "normal")
        fibra       = (self.btn_conectividad.cget("state") == "normal")
        usb         = (self.btn_otros_puertos.cget("state") == "normal")
        wifi        = (self.btn_wifi.cget("state") == "normal")
        #print("En wifi es "+str(wifi))
        # Importar la conexion
        from src.backend.endpoints.conexion import iniciar_testerConexion
        #iniciar_testerConexion(resetFabrica, usb, fibra, wifi)
        # 4) Arranca hilo con stop_event para poder cancelarlo
        self.tester_thread = threading.Thread(
            target=iniciar_testerConexion,
            args=(resetFabrica, usb, fibra, wifi, self.event_q, self.stop_event),
            daemon=True
        )
        self.tester_thread.start()'''

    # Helper opciones actuales
    def _get_loop_flags(self):
        resetFabrica = (self.btn_omitir.cget("state") == "normal")
        fibra        = (self.btn_conectividad.cget("state") == "normal")
        usb          = (self.btn_otros_puertos.cget("state") == "normal")
        wifi         = (self.btn_wifi.cget("state") == "normal")
        return resetFabrica, usb, fibra, wifi
    
    # Helper para arrancar/reanudar el loop (auto-test o monitor) creando un stop_event nuevo y evitando duplicar hilos
    def _start_loop(self, auto_test_on_detect: bool, start_in_monitor: bool = False):
        # stop_event nuevo:
        # - El anterior pudo quedar "set" (por cambiar de modo / detener el loop / correr una unitaria)
        # - Si lo reusamos, main_loop saldría inmediatamente
        # - Por eso se crea un Event nuevo cada vez que arrancamos un loop

        # Esperar a que el hilo anterior muera antes de crear uno nuevo
        if self.tester_thread and self.tester_thread.is_alive():
            self.tester_thread.join(timeout=5)  # Esperar hasta 5s
            # Si sigue vivo, NO crear duplicado
            if self.tester_thread.is_alive():
                print("[WARN] El hilo anterior no terminó. No se crea duplicado.")
                return

        # stop_event nuevo (el anterior pudo quedar set)
        self.stop_event = threading.Event()

        resetFabrica, usb, fibra, wifi = self._get_loop_flags()

        from src.backend.endpoints.conexion import iniciar_testerConexion
        self.tester_thread = threading.Thread(
            target=iniciar_testerConexion,
            args=(resetFabrica, usb, fibra, wifi, self.master.event_q, self.stop_event),
            kwargs={"auto_test_on_detect": auto_test_on_detect,
                    "start_in_monitor": start_in_monitor,},  # Clave
            daemon=True
        )
        self.tester_thread.start()

    # Función "mata modos"
    def _stop_mode_loop(self):
        """Detiene el hilo del modo actual (Etiqueta/Test/Retest)."""
        try:
            self.stop_event.set()  # avisa al main_loop que se detenga
            t = self._mode_thread
            if t and t.is_alive():
                t.join(timeout=15)  # le das chance real de morir
        except Exception:
            pass
        finally:
            self._mode_thread = None

    # Handler para correr la unitaria desde el panel inferior
    def _run_unit_from_panel(self, reset, soft, usb, fibra, wifi, modelo):
        """
        Callback que viene del panel inferior.
        1) Para el loop del modo seleccionado
        2) Corre la unitaria en hilo
        3) Al terminar, reanuda en MONITOR (para que NO re-ejecute el modo anterior)
        """
        # 1) detener loop actual
        self.stop_event.set()
        prev_thread = self.tester_thread

        # 2) preparar control de unitaria (para poder cancelarla desde cambiar_modo)
        unit_stop = threading.Event()
        self._unit_stop_event = unit_stop
        self._unit_running = True

        # evita que una desconexión por reboot durante unitaria borre PASS/FAIL
        self._suppress_cleanup_until = time.time() + 60  # 60s de gracia (ajusta si quieres)

        def worker():
            try:
                # 3) esperar a que muera el loop anterior
                if prev_thread and prev_thread.is_alive():
                    self.master.event_q.put(("log", "Deteniendo ciclo actual para ejecutar unitaria..."))
                    prev_thread.join(timeout=20)

                # si no murió, no corras unitaria encima
                if prev_thread and prev_thread.is_alive():
                    self.master.event_q.put(("log", "No se pudo detener el ciclo anterior. Ignorando unitaria."))
                    return

                # 4) correr la unitaria
                from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
                iniciar_pruebaUnitariaConexion(
                    reset, soft, usb, fibra, wifi,
                    model=modelo,
                    out_q=self.master.event_q,
                    stop_event=unit_stop
                )

            finally:
                # 5) limpiar flags
                self._unit_running = False
                if self._unit_stop_event is unit_stop:
                    self._unit_stop_event = None

                # 6) reanudar MONITOR SI NO fue cancelada
                if not unit_stop.is_set():
                    self.master.event_q.put(("resume_monitor", None))

        threading.Thread(target=worker, daemon=True).start()

        '''
        # 1) pedir stop al loop actual
        self.stop_event.set()

        prev_thread = self.tester_thread
        unit_stop = threading.Event()

        def worker():
            # 2) join del hilo anterior SIN bloquear UI
            if prev_thread and prev_thread.is_alive():
                self.event_q.put(("log", "Deteniendo ciclo actual para ejecutar unitaria..."))
                prev_thread.join()  # join real, pero en worker thread

            # 3) correr la unitaria
            from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
            iniciar_pruebaUnitariaConexion(
                reset, soft, usb, fibra, wifi,
                model=model_display,
                out_q=self.event_q,
                stop_event=unit_stop
            )

            # asegura reanudación del loop
            self.event_q.put(("resume_loop", None))

        threading.Thread(target=worker, daemon=True).start()
        '''

    # ===================== BOTONES (sin toggle local) =====================
    def _disparar_prueba(self, nombre_prueba: str):
        """
        Ya NO cambia 'FALLIDA/EXITOSA' ni contador.
        Solo dispara backend si existe.
        """
        print(f"Solicitando backend: {nombre_prueba}")
        if self.viewmodel and hasattr(self.viewmodel, "ejecutar_prueba"):
            try:
                self.viewmodel.ejecutar_prueba(nombre_prueba)
            except TypeError:
                # por si tu backend no recibe nombre
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

    # Funciones para la queue de los hilos
    def destroy(self):
        self._polling = False
        # Destruccion de eventos
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
            # ejemplo: mostrar en label/textbox
            self.panel_pruebas.set_texto_superior(payload)
            #self.lbl_texto_superior.configure(text = payload)
        elif kind == "logSuper":
            self.modelo_label.configure(text="Modelo: "+str(payload))
            self.modelo_detectado = payload
            self.panel_pruebas.modelo = payload  # Actualizar modelo en el panel
        elif kind == "pruebas":
            self.panel_pruebas.set_texto_inferior(payload)
        elif kind == "con":
            # Cuando se conecta hace una limpieza y establece que se ha conectado
            payload_lower = str(payload).lower()

            '''if "conectado" in payload_lower and "desconectado" not in payload_lower:
                self.panel_pruebas.actualizar_estado_conexion(True)
            else:
                self.panel_pruebas.actualizar_estado_conexion(False)'''
            
            if "desconectado" in payload_lower:
                self.panel_pruebas.actualizar_estado_conexion(False)

                # Si estamos en unitaria (o acaba de ocurrir), NO borres PASS/FAIL
                # if (not self._unit_running) and (time.time() >= self._suppress_cleanup_until):
                self._limpiezaElementos()
            else:
                self.panel_pruebas.actualizar_estado_conexion(True)

        elif kind == "resultados":
            # ejemplo: pintar resultados en tu UI
            info  = payload.get("info", {})
            # Detectar si viene de prueba unitaria usando el flag _unit_running
            from_unit = getattr(self, '_unit_running', False)
            self._render_resultados(payload, from_unit_test=from_unit)
            # guardar en DB
            from src.backend.sua_client.dao import insertar_operacion, extraer_by_id, existe_operacion_dia, validar_por_modo
            modo = self.modo_var.get()
            root = self.winfo_toplevel()
            user_id = int(getattr(root, "current_user_id", None))
            # Antes de insertar hay que validar que el sn no esté ya registrado en ese MODO
            registroAnterior = existe_operacion_dia(info.get("sn", "—"), modo)
            if registroAnterior:
                # No insertar, actualizar UI con: equipo ya registrado (emit lower maybe)
                def emit(kind, payload):
                    if self.master.event_q:
                        self.master.event_q.put((kind, payload))
                emit("log", "DISPOSITIVO YA REGISTRADO, NO SE CONTARÁ PARA LAS PRUEBAS")
            else:
                id = insertar_operacion(payload, modo, user_id)
                # Actualizar el campo de valido
                validar_por_modo(info.get("sn","-"), modo)
                payload_final = extraer_by_id(id, "operations")
            
            self.updatePruebas()
            # publicar a IOT
            
        elif kind == "test_individual":
            # Actualiza el botón de una prueba individual al terminar
            # payload = {"name": "TX_POWER", "status": "PASS"} o "FAIL"
            test_name = payload.get("name", "").lower()
            status = payload.get("status", "FAIL")
            modo = self.modo_var.get()
            # Mapeo de nombres de test a keys de botones
            name_to_key = {
                "ping":              "ping",
                "ping_connectivity": "ping",
                "factory_reset":     "factory_reset",
                "software_update":   "software_update",
                "usb_port":          "usb_port",
                "tx_power":          "tx_power",
                "rx_power":          "rx_power",
                "wifi_24ghz":        "wifi_24ghz_signal",
                "wifi_5ghz":         "wifi_5ghz_signal",
            }
            btn_key = name_to_key.get(test_name, test_name)
            self.panel_pruebas._set_button_status(btn_key, status)

            # Validar para que solo en pruebas unitarias haga registros
            if getattr(self, "_unit_running", False):
                raw = self.snInfo.cget("text")         
                sn = raw.replace("SN:", "", 1).strip() # Leer el sn de la UI, Eliminar "SN: "
                # Normalizar a BD
                from src.backend.endpoints.conexion import normalizar_valor_bd
                campo = normalizar_valor_bd(btn_key)
                # Actualizar el registro de el modo seleccionado
                from src.backend.sua_client.dao import validar_por_modo, update_operation_snmodo
                # Primero hacer update
                # Verificar que el campo no sea None
                if campo != None:
                    update_operation_snmodo(sn, modo, campo, status)
                    # Update al campo de valido
                    valido = validar_por_modo(sn, modo)
                    if valido:
                        #actualizar UI
                        self.updatePruebas()
        #elif kind == "test":
            # ejemplo: actualizar un cuadrito por prueba || de momento no
            # payload = {"nombre":"wifi_24ghz_signal","estado":"PASS","valor":"-14.6 dBm"}
            #self._update_test(payload)

        elif kind == "resume_monitor":
            # Reanudar en MONITOR: vuelve a escaneo/pings pero NO dispara pruebas completas al detectar
            # self._start_loop(auto_test_on_detect=False)
            modo = self.modo_var.get()
            auto = (modo in ("Testeo", "Retesteo"))
            self._start_loop(auto_test_on_detect=auto, start_in_monitor=True)

    def _limpiezaElementos(self):
        # Label
        self.snInfo.configure(text="SN: ")
        self.macInfo.configure(text="MAC: ")
        self.sftInfo.configure(text="SOFTWARE: ")
        self.w24Info.configure(text="WIFI 2.4GHz: ")
        self.w5Info.configure(text="WIFI 5 GHz: ")
        self.pswInfo.configure(text="Password: ")
        self.txInfo.configure(text="Fo TX: —")
        self.rxInfo.configure(text="Fo RX: —")
        self.usbInfo.configure(text="Usb Port: ")
        self.estado_prueba_label.configure(text="SIN EJECUTAR")
        self.estado_prueba_label.configure(text_color="#f1c40f")
        self.modelo_label.configure(text="Modelo: ")
        self.panel_pruebas.set_texto_superior("-")
        self.panel_pruebas.set_texto_inferior("-")
        # botones
        self.panel_pruebas._set_button_status("ping", "reset")
        self.panel_pruebas._set_button_status("factory_reset", "reset")
        self.panel_pruebas._set_button_status("software_update", "reset") 
        self.panel_pruebas._set_button_status("usb_port", "reset")
        # validar los valores 
        self.panel_pruebas._set_button_status("tx_power", "reset")
        self.panel_pruebas._set_button_status("rx_power", "reset")
        # ya están validadas
        self.panel_pruebas._set_button_status("wifi_24ghz_signal", "reset")
        self.panel_pruebas._set_button_status("wifi_5ghz_signal", "reset")

    def _render_resultados(self, payload, from_unit_test: bool = False):
        print("La payload recibida es: "+str(payload))
        info  = payload.get("info", {})
        tests = payload.get("tests", {})

        #Archivo txt para modo etiqueta (solo si NO viene de prueba unitaria)
        if self.modo_var.get() == "Etiqueta" and not from_unit_test:
            # Usar funcion en archivo conexion
            from src.backend.endpoints.conexion import generaEtiquetaTxt
            generaEtiquetaTxt(payload)
        # Actualizar obj panel_pruebas
        self.panel_pruebas.modelo = info.get("modelo", "—")
        # valido = payload.get("valido", False)

        # INFO
        # modelo = info.get("modelo", "—") # se actualiza desde ont_automatico
        sn     = info.get("sn", "—")
        mac    = info.get("mac", "—")
        sftver = info.get("sftVer", "—")
        wifi24 = info.get("wifi24", "—")
        wifi5  = info.get("wifi5", "—")
        passWi = info.get("passWifi", "—")

        # TESTS || AQUI ES MOVER LOS BOTONES (utilizar self.panel_pruebas)
        ping   = tests.get("ping", "SIN PRUEBA")
        reset  = tests.get("reset", "SIN PRUEBA")
        usb    = tests.get("usb", "SIN PRUEBA")
        tx     = tests.get("tx", None)
        rx     = tests.get("rx", None)
        w24    = tests.get("w24", "SIN PRUEBA")
        w5     = tests.get("w5", "SIN PRUEBA")
        sftU   = tests.get("sftU", "SIN PRUEBA")

        '''self.panel_pruebas._set_button_status("ping", ping)
        self.panel_pruebas._set_button_status("factory_reset", reset)
        self.panel_pruebas._set_button_status("software_update", sftU) # falta mandarla a llamar (literalmente terminamos la prueba hace unas horas)
        self.panel_pruebas._set_button_status("usb_port", usb)
        # validar los valores TX
        self.panel_pruebas._set_button_status("tx_power", tx)
        # validar los valores RX
        self.panel_pruebas._set_button_status("rx_power", rx)
        # ya están validadas
        self.panel_pruebas._set_button_status("wifi_24ghz_signal", w24)
        self.panel_pruebas._set_button_status("wifi_5ghz_signal", w5)'''

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
        # TX/RX solo si vienen (para no borrar el valor anterior)
        if "tx" in tests:
            tx = tests.get("tx")
            self.txInfo.configure(text=("Fo TX: —" if tx in (False, None) else f"Fo TX: {tx} dBm"))
            if(_to_float_safe(tx) >= mintx and _to_float_safe(tx) <= maxtx):
                # Validar si está dentro de los valores
                txp = True
            else:
                txp = False
            self.panel_pruebas._set_button_status("tx_power", txp)
        if "rx" in tests:
            rx = tests.get("rx")
            self.rxInfo.configure(text=("Fo RX: —" if rx in (False, None) else f"Fo RX: {rx} dBm"))
            if(_to_float_safe(rx) >= minrx and _to_float_safe(rx) <= maxrx):
                rxp = True
            else:
                rxp = False
            self.panel_pruebas._set_button_status("rx_power", rxp)

        # USB label solo si viene (no borrar si no está en el payload - prueba unitaria)
        if "usb" in tests:
            usb = tests.get("usb")
            if usb == "SIN PRUEBA":
                usb_label = "Prueba omitida"
            elif usb == "PASS" or usb == True:
                usb_label = "USB detectada"
            else:
                usb_label = "USB no detectada"
            self.usbInfo.configure(text="Usb Port: " + str(usb_label))
        # else: No hacer nada - conservar el valor anterior

        # -------- INFO (lado izquierdo) --------
        self.snInfo.configure(text="SN: "+str(sn))
        self.macInfo.configure(text="MAC: "+str(mac))
        self.sftInfo.configure(text="SOFTWARE: "+str(sftver))
        self.w24Info.configure(text="WIFI 2.4GHz: "+str(wifi24))
        self.w5Info.configure(text="WIFI 5 GHz: "+str(wifi5))
        self.pswInfo.configure(text="Password: "+str(passWi))

        # Nota: TX/RX ya se actualizan arriba en el bloque condicional "if 'tx' in tests"
        # No duplicar aquí para evitar sobrescribir con valores vacíos

        self.estado_prueba_label.configure(text="EJECUTADO")
        self.estado_prueba_label.configure(text_color="#6B9080")

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

    view = TesterView(app)
    view.pack(fill="both", expand=True)
    app.mainloop()
