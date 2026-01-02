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
    def __init__(self, parent, event_q, viewmodel=None, **kwargs):
        
        #Vista
        super().__init__(parent, fg_color="#E9F5FF", **kwargs)

        self.viewmodel = viewmodel
        # Para la queue
        self.event_q = event_q
        self._polling = True
        self.stop_event = threading.Event()  # Para cancelar hilos al cambiar de modo
        self.tester_thread = None # Hilo actual del tester
        self.modelo_detectado = None  # Se actualiza cuando el backend detecta el modelo
        self._mode_tread = None  # Hilo del modo actual (testeo/monitor)
        self._unit_tread = None  # Hilo de la prueba unitaria
        self._unit_stop_event = None  # Evento de parada para la unitaria
        self._unit_running = False
        self._suppress_cleanup_until = 0.0
        self.after(100, self._poll_queue)
        # Paleta de colores para estados de botones (pastel)
        self.color_neutro_fg = "#4EA5D9"
        self.color_neutro_hover = "#3B8CC2"
        self.color_activo_fg = "#6FCF97"
        self.color_activo_hover = "#56B27D"
        self.color_inactivo_fg = "#F28B82"
        self.color_inactivo_hover = "#E0665C"

        # Layout general: columna 0 = sidebar, columna 1 = contenido
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ========= ASSETS =========
        assets_dir = Path(__file__).parent.parent / "assets" / "icons"
        logo_path = assets_dir / "logo_tester.png"
        # ==========================

        # ======= SIDEBAR CON SCROLL =======
        self.left_scroll = ctk.CTkScrollableFrame(
            self,
            width=280,
            corner_radius=0,
            fg_color="#E3F7F2",
        )
        self.left_scroll.grid(row=0, column=0, sticky="nsw", padx=0, pady=0)
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
            values=["Testeo", "Retesteo", "Etiqueta"],
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
        # =============================================

        # Estado inicial de los botones
        self._set_all_buttons_state("neutral")

        # ===== Frame derecho (contenido principal) =====
        self.right_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#E9F5FF")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

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

        # Panel inferior
        self.panel_pruebas = PanelPruebasConexion(
            self.main_content,
            modelo=None,
            q=self.event_q,
            on_run_unit=self._run_unit_from_panel  # Callback
        )
        self.panel_pruebas.pack(side="bottom", fill="x", padx=0, pady=(0, 10)) #, expand=False

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

    # ===================== NAVEGACIÓN =====================
    def _swap_view(self, view_cls, **init_kwargs):
        parent = self.master
        try:
            self.destroy()
        except Exception:
            pass
        nueva = view_cls(parent, **init_kwargs)
        nueva.pack(fill="both", expand=True)

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
        width = max(event.width, 400)
        if width < 950:
            sidebar_width = 280
        else:
            sidebar_width = int(width * 0.22)
            sidebar_width = max(280, min(sidebar_width, 320))
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

    def cambiar_modo(self, modo: str):
        self.stop_event.set()  # Señal de parar al hilo anterior (modo)

        # Cancelar también la unitaria si hay una corriendo
        if getattr(self, "_unit_stop_event", None) is not None:
            self._unit_stop_event.set()
            self._unit_stop_event = None

        # NO crear nuevo stop_event aquí - _start_loop lo hará después de verificar
        # que el hilo anterior murió

        print(f"     Modo seleccionado: {modo}")
        self._set_all_buttons_state("neutral")

        if modo == "Testeo":
            self._set_button_style(self.btn_omitir, "active")
            self._set_button_style(self.btn_conectividad, "active")
            self._set_button_style(self.btn_otros_puertos, "active")
            self._set_button_style(self.btn_ethernet, "inactive")
            self._set_button_style(self.btn_wifi, "inactive")
        elif modo == "Retesteo":
            self._set_all_buttons_state("active")
        elif modo == "Etiqueta":
            self._set_all_buttons_state("inactive")
        # Arrancar loop según modo:
        # - Testeo / Retesteo: sí corre pruebas completas al detectar
        # - Etiqueta: normalmente NO corre pruebas (monitor)
        if modo in ("Testeo", "Retesteo"):
            self.setOpcionesView(auto_test_on_detect=True)
        else:
            self.setOpcionesView(auto_test_on_detect=False)

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
    def _start_loop(self, auto_test_on_detect: bool):
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
            args=(resetFabrica, usb, fibra, wifi, self.event_q, self.stop_event),
            kwargs={"auto_test_on_detect": auto_test_on_detect},  # Clave
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
                    self.event_q.put(("log", "Deteniendo ciclo actual para ejecutar unitaria..."))
                    prev_thread.join(timeout=20)

                # si no murió, no corras unitaria encima
                if prev_thread and prev_thread.is_alive():
                    self.event_q.put(("log", "No se pudo detener el ciclo anterior. Ignorando unitaria."))
                    return

                # 4) correr la unitaria
                from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
                iniciar_pruebaUnitariaConexion(
                    reset, soft, usb, fibra, wifi,
                    model=modelo,
                    out_q=self.event_q,
                    stop_event=unit_stop
                )

            finally:
                # 5) limpiar flags
                self._unit_running = False
                if self._unit_stop_event is unit_stop:
                    self._unit_stop_event = None

                # 6) reanudar MONITOR SI NO fue cancelada
                if not unit_stop.is_set():
                    self.event_q.put(("resume_monitor", None))

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
        super().destroy()

    def _poll_queue(self):
        if not self._polling:
            return

        try:
            while True:
                kind, payload = self.event_q.get_nowait()

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
                        if (not self._unit_running) and (time.time() >= self._suppress_cleanup_until):
                            self._limpiezaElementos()
                    else:
                        self.panel_pruebas.actualizar_estado_conexion(True)

                elif kind == "resultados":
                    # ejemplo: pintar resultados en tu UI
                    self._render_resultados(payload)
                elif kind == "test_individual":
                    # Actualiza el botón de una prueba individual al terminar
                    # payload = {"name": "TX_POWER", "status": "PASS"} o "FAIL"
                    test_name = payload.get("name", "").lower()
                    status = payload.get("status", "FAIL")
                    # Mapeo de nombres de test a keys de botones
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

                #elif kind == "test":
                    # ejemplo: actualizar un cuadrito por prueba || de momento no
                    # payload = {"nombre":"wifi_24ghz_signal","estado":"PASS","valor":"-14.6 dBm"}
                    #self._update_test(payload)

                elif kind == "resume_monitor":
                    # Reanudar en MONITOR: vuelve a escaneo/pings pero NO dispara pruebas completas al detectar
                    self._start_loop(auto_test_on_detect=False)

        except queue.Empty:
            pass

        self.after(100, self._poll_queue)

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

    def _render_resultados(self, payload):
        print("La payload recibida es: "+str(payload))
        info  = payload.get("info", {})
        tests = payload.get("tests", {})
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

        # TX/RX solo si vienen (para no borrar el valor anterior)
        if "tx" in tests:
            tx = tests.get("tx")
            self.panel_pruebas._set_button_status("tx_power", tx)
            self.txInfo.configure(text=("Fo TX: —" if tx in (False, None) else f"Fo TX: {tx} dBm"))

        if "rx" in tests:
            rx = tests.get("rx")
            self.panel_pruebas._set_button_status("rx_power", rx)
            self.rxInfo.configure(text=("Fo RX: —" if rx in (False, None) else f"Fo RX: {rx} dBm"))

        # USB label solo si viene
        if "usb" in tests:
            usb = tests.get("usb")
            if usb == "SIN PRUEBA":
                usb_label = "Prueba omitida"
            elif usb == "PASS":
                usb_label = "USB detectada"
            else:
                usb_label = "USB no detectada"
            self.usbInfo.configure(text="Usb Port: " + str(usb_label))

        # -------- INFO (lado izquierdo) --------
        self.snInfo.configure(text="SN: "+str(sn))
        self.macInfo.configure(text="MAC: "+str(mac))
        self.sftInfo.configure(text="SOFTWARE: "+str(sftver))
        self.w24Info.configure(text="WIFI 2.4GHz: "+str(wifi24))
        self.w5Info.configure(text="WIFI 5 GHz: "+str(wifi5))
        self.pswInfo.configure(text="Password: "+str(passWi))

        # -------- TESTS (lado derecho) --------
        # Si tx/rx son números (dBm), los formateamos
        self.txInfo.configure(text=("Fo TX: —" if tx in (False, None) else f"Fo TX: {tx} dBm"))
        self.rxInfo.configure(text=("Fo RX: —" if rx in (False, None) else f"Fo RX: {rx} dBm"))

        # USB puede venir "PASS"/"ERROR"/"SIN PRUEBA"
        if usb == "SIN PRUEBA":
            usb_label = "Prueba omitida"
        elif usb == True and usb == "PASS":
            usb_label = "USB detectada"
        else:
            usb_label = "USB no detectada"
        self.usbInfo.configure(text="Usb Port: "+str(usb_label))

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
