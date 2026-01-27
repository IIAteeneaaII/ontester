"""
Módulo que define el panel inferior de pruebas de conectividad.

Este panel se usa como un componente reutilizable dentro de la interfaz principal
(tester_view.py). Visualmente está compuesto por:

- Una barra de estado que indica si el equipo está CONECTADO / NO CONECTADO.
- Un texto superior adicional (por ejemplo, para mostrar algún mensaje técnico).
- Una fila con 8 botones de prueba (PING, FACTORY RESET, SOFTWARE, etc.).
- Un texto inferior (por ahora fijo en "TEXTO", pensada como leyenda o nota).

La idea es que tester_view.py pueda instanciar este panel y, si lo desea,
actualizar el estado de conexión usando el método `actualizar_estado_conexion`.
"""

import sys
from pathlib import Path
import threading
from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion

import customtkinter as ctk
import traceback
# ---------------------------------------------------------------------
# Configuración del path para poder importar los botones reutilizables
# ---------------------------------------------------------------------

# Ubicación raíz del proyecto (dos niveles por arriba de /ui/)
root_path = Path(__file__).parent.parent.parent.parent
# Agregamos la ruta al sys.path para que Python encuentre "src.Frontend.navigation"
sys.path.insert(0, str(root_path))

# Importamos las funciones que crean los botones del panel central
from src.Frontend.navigation.botones import (
    panel_boton_ping,
    panel_boton_factory_reset,
    panel_boton_software,
    panel_boton_usb_port,
    panel_boton_tx_power,
    panel_boton_rx_power,
    panel_boton_wifi_24,
    panel_boton_wifi_50,
)


class PanelPruebasConexion(ctk.CTkFrame):
    """
    Panel horizontal reutilizable con:

    - Label superior de estado: "CONECTADO" / "NO CONECTADO".
    - Un texto superior adicional (por ejemplo, para mensajes técnicos).
    - Ocho botones de pruebas en una sola fila.
    - Un texto inferior (actualmente fijo en "TEXTO").

    Esta clase NO ejecuta realmente las pruebas; únicamente muestra la
    interfaz gráfica. El comportamiento de cada botón (qué hace al
    presionarse) se define en quien use este panel (por ahora, sólo se
    imprime un mensaje en consola).
    """

    def __init__(self, parent, modelo, on_run_unit=None, **kwargs):
        """
        Constructor del panel.

        :param parent:  Widget padre que contendrá este panel (por ejemplo,
                        un frame dentro de tester_view).
        :param kwargs:  Parámetros adicionales que se pasan al CTkFrame base.
        """
        super().__init__(parent, **kwargs)
        self.on_run_unit = on_run_unit  # Callback para ejecutar pruebas unitarias

        # Paleta para estados
        self.COL_IDLE  = "#4EA5D9"  # color base
        self.COL_PASS  = "#6B9080"  # verde
        self.COL_FAIL  = "#C1666B"  # rojo

        # Config
        self.modelo = modelo
        app = self.winfo_toplevel()
        self.q = app.event_q
        # -----------------------------------------------------------------
        # Apariencia general del marco contenedor
        # -----------------------------------------------------------------
        # Ahora usamos un verde suave que coincide con la paleta de la app
        self.configure(
            corner_radius=10,
            fg_color="#D4E7D7",   # Verde muy suave, más claro que #90C695
            border_width=2,
            border_color="#6B9080"  # Borde verde principal
        )

        # -----------------------------------------------------------------
        # Configuración de columnas para la grilla interna
        # -----------------------------------------------------------------
        # Como tenemos 8 botones, definimos 8 columnas con el mismo "peso"
        # para que se repartan homogéneamente en el ancho disponible.
        for col in range(8):
            self.grid_columnconfigure(col, weight=1)

        # -----------------------------------------------------------------
        # Label de estado de conexión (renglón 0)
        # -----------------------------------------------------------------
        # Muestra "CONECTADO" o "NO CONECTADO". El texto se modifica desde
        # el método `actualizar_estado_conexion`.
        self.lbl_estado = ctk.CTkLabel(
            self,
            text="NO CONECTADO",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#C1666B",    # Rojo suave para el estado "no conectado"
        )
        self.lbl_estado.grid(
            row=0,
            column=0,
            columnspan=8,   # Ocupa todo el ancho del panel
            pady=(10, 5),
            sticky="n"      # Se alinea hacia la parte superior de la celda
        )

        # -----------------------------------------------------------------
        # Texto superior adicional (renglón 1)
        # -----------------------------------------------------------------
        # Este texto puede usarse para mostrar mensajes como:
        # "Respuesta desde 192.168.100.1..." o cualquier otra leyenda.
        self.lbl_texto_superior = ctk.CTkLabel(
            self,
            text="status",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50",
        )
        self.lbl_texto_superior.grid(
            row=1,
            column=0,
            columnspan=8,
            pady=(0, 10),
            sticky="n"
        )

        # -----------------------------------------------------------------
        # Fila de botones (renglón 2)
        # -----------------------------------------------------------------
        # Cada botón se crea mediante una función de `navigation.botones`
        # para mantener un estilo consistente en toda la aplicación.
        # Por ahora, el comando sólo llama a `_on_click`, que imprime el
        # nombre de la prueba en consola (pensado como gancho para futuro).
        self.btn_ping = panel_boton_ping(self, command=lambda: self._on_click("PING"))
        self.btn_ping.grid(row=2, column=0, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_factory = panel_boton_factory_reset(
            self, command=lambda: self._on_click("FACTORY RESET")
        )
        self.btn_factory.grid(row=2, column=1, padx=7, pady=(0, 10), sticky="nsew")

        self.btn_software = panel_boton_software(
            self, command=lambda: self._on_click("SOFTWARE")
        )
        self.btn_software.grid(row=2, column=2, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_usb = panel_boton_usb_port(
            self, command=lambda: self._on_click("USB PORT")
        )
        self.btn_usb.grid(row=2, column=3, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_tx = panel_boton_tx_power(
            self, command=lambda: self._on_click("TX POWER")
        )
        self.btn_tx.grid(row=2, column=4, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_rx = panel_boton_rx_power(
            self, command=lambda: self._on_click("RX POWER")
        )
        self.btn_rx.grid(row=2, column=5, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_wifi24 = panel_boton_wifi_24(
            self, command=lambda: self._on_click("WIFI 2.4 GHz")
        )
        self.btn_wifi24.grid(row=2, column=6, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_wifi50 = panel_boton_wifi_50(
            self, command=lambda: self._on_click("WIFI 5.0 GHz")
        )
        self.btn_wifi50.grid(row=2, column=7, padx=5, pady=(0, 10), sticky="nsew")

        # -----------------------------------------------------------------
        # Texto inferior (renglón 3)
        # -----------------------------------------------------------------
        # De momento se deja fijo como "TEXTO". Sirve como leyenda, pista o
        # información adicional breve debajo de los botones.
        self.lbl_texto = ctk.CTkLabel(
            self,
            text="PRUEBAS",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#2C3E50",
        )
        self.lbl_texto.grid(
            row=3,
            column=0,
            columnspan=8,
            pady=(0, 8),
            sticky="s"
        )

        # Mapeo
        self.test_buttons = {
            "ping": self.btn_ping,
            "factory_reset": self.btn_factory,
            "software_update": self.btn_software,
            "usb_port": self.btn_usb,
            "tx_power": self.btn_tx,
            "rx_power": self.btn_rx,
            "wifi_24ghz_signal": self.btn_wifi24,
            "wifi_5ghz_signal": self.btn_wifi50,
        }

    # -----------------------------------------------------------------
    # API pública del panel
    # -----------------------------------------------------------------
    def actualizar_estado_conexion(self, conectado: bool):
        """
        Actualiza el label de estado ("CONECTADO" / "NO CONECTADO").

        :param conectado: True si el equipo está conectado,
                          False si no lo está.
        """
        if conectado:
            # Estado conectado: texto en verde
            self.lbl_estado.configure(
                text="CONECTADO",
                text_color="#6B9080"  # Verde principal de la app
            )
        else:
            # Estado no conectado: texto en rojo pastel
            self.lbl_estado.configure(
                text="NO CONECTADO",
                text_color="#C1666B"  # Rojo suave
            )
    def set_texto_superior(self, texto):
        self.lbl_texto_superior.configure(text=texto)
    def set_texto_inferior(self, texto):
        self.lbl_texto.configure(text=texto)
    
    # Modificar los botones con base en la prueba ejecutada
    def _set_button_status(self, test_key: str, status):
        """
        status puede ser 'PASS' / 'FAIL' o True / False / None
        """
        btn = self.test_buttons.get(test_key)
        if not btn:
            return

        # Normalizamos el status
        if isinstance(status, str):
            status = status.upper()

        if status is True or status == "PASS":
            fg = self.COL_PASS
        elif status is False or status == "FAIL":
            fg = self.COL_FAIL
        else:
            fg = self.COL_IDLE

        btn.configure(fg_color=fg, hover_color=fg)
    # -----------------------------------------------------------------
    # Callbacks internos
    # -----------------------------------------------------------------
    def _on_click(self, nombre_prueba: str):
        """
        Callback genérico para los botones.

        Por ahora solo imprime el nombre de la prueba en consola.
        En el futuro, aquí se puede enlazar la lógica real de ejecución.

        :param nombre_prueba: Identificador de la prueba (PING, TX POWER, etc.).
        PING
        FACTORY RESET
        SOFTWARE
        USB PORT
        TX POWER
        RX POWER
        WIFI 2.4 GHz
        WIFI 5.0 GHz
        """
        reset = soft = usb = fibra = wifi = False
        if(nombre_prueba == "FACTORY RESET"):
            reset = True
        if(nombre_prueba == "SOFTWARE"):
            soft = True
        if(nombre_prueba == "USB PORT"):
            usb = True
        if(nombre_prueba == "TX POWER"):
            fibra = True
        if(nombre_prueba == "RX POWER"):
            fibra = True
        if(nombre_prueba == "WIFI 2.4 GHz"):
            wifi = True
        if(nombre_prueba == "WIFI 5.0 GHz"):
            wifi = True

        print("[PANELPRUEBAS] El modelo recibido es: ", self.modelo)
        
        # Llamar a la función de pruebas unitarias
        '''from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
        iniciar_pruebaUnitariaConexion(reset, soft, usb, fibra, wifi, model=self.modelo)
        print(f"[PanelPruebasConexion] Click en {nombre_prueba}")'''

        # Delegar la ejecución a TesterView (para que pueda parar el loop del modo antes)
        if callable(getattr(self, "on_run_unit", None)):
            # Firma esperada: on_run_unit(reset, soft, usb, fibra, wifi, modelo)
            self.on_run_unit(reset, soft, usb, fibra, wifi, self.modelo)
        else:
            # Fallback si alguien instancia el panel sin callback
            import threading
            from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
            threading.Thread(
                target=iniciar_pruebaUnitariaConexion,
                args=(reset, soft, usb, fibra, wifi),
                kwargs={"model": self.modelo, "out_q": self.master.event_q},
                daemon=True
            ).start()

        print(f"[PanelPruebasConexion] Click en {nombre_prueba}")

# ---------------------------------------------------------------------
# Bloque de prueba independiente
# ---------------------------------------------------------------------
# Permite ejecutar este archivo directamente (python panel_pruebas_view.py)
# para ver únicamente el panel, sin necesidad de cargar toda la interfaz
# principal del tester.
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1100x250")
    root.title("Demo PanelPruebasConexion")

    panel = PanelPruebasConexion(root)
    panel.pack(fill="x", expand=True, padx=20, pady=20)

    root.mainloop()