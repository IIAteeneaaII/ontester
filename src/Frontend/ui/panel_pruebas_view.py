"""
Módulo que define el panel inferior de pruebas de conectividad.

Este panel se usa como un componente reutilizable dentro de la interfaz principal.
"""

import sys
from pathlib import Path
import threading
import customtkinter as ctk

# ---------------------------------------------------------------------
# Configuración del path para poder importar los botones reutilizables
# ---------------------------------------------------------------------
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

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
    - Un texto superior adicional (para mensajes técnicos).
    - Ocho botones de pruebas en una sola fila.
    - Un texto inferior (leyenda).
    """

    def __init__(self, parent, modelo=None, on_run_unit=None, **kwargs):
        super().__init__(parent, **kwargs)

        self.on_run_unit = on_run_unit
        self.modelo = modelo

        # Colores (fallback) – se sobreescriben con apply_theme()
        self.COL_IDLE = "#7BBADF"
        self.COL_IDLE_HOVER = "#4085B3"
        self.COL_PASS = "#22C55E"
        self.COL_FAIL = "#EF4444"
        self.COL_TEXT = "#2C3E50"
        self.COL_BORDER = "#8FA3B0"
        self.COL_BG = "#FFFFFF"

        # Apariencia general del marco contenedor
        self.configure(
            corner_radius=10,
            fg_color=self.COL_BG,
            border_width=2,
            border_color=self.COL_BORDER,
        )

        # 8 columnas para botones
        for col in range(8):
            self.grid_columnconfigure(col, weight=1)

        # Estado conexión
        self.lbl_estado = ctk.CTkLabel(
            self,
            text="NO CONECTADO",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=self.COL_FAIL,
        )
        self.lbl_estado.grid(row=0, column=0, columnspan=8, pady=(10, 5), sticky="n")

        # Texto superior
        self.lbl_texto_superior = ctk.CTkLabel(
            self,
            text="status",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COL_TEXT,
        )
        self.lbl_texto_superior.grid(row=1, column=0, columnspan=8, pady=(0, 10), sticky="n")

        # Botones
        self.btn_ping = panel_boton_ping(self, command=lambda: self._on_click("PING"))
        self.btn_ping.grid(row=2, column=0, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_factory = panel_boton_factory_reset(self, command=lambda: self._on_click("FACTORY RESET"))
        self.btn_factory.grid(row=2, column=1, padx=7, pady=(0, 10), sticky="nsew")

        self.btn_software = panel_boton_software(self, command=lambda: self._on_click("SOFTWARE"))
        self.btn_software.grid(row=2, column=2, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_usb = panel_boton_usb_port(self, command=lambda: self._on_click("USB PORT"))
        self.btn_usb.grid(row=2, column=3, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_tx = panel_boton_tx_power(self, command=lambda: self._on_click("TX POWER"))
        self.btn_tx.grid(row=2, column=4, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_rx = panel_boton_rx_power(self, command=lambda: self._on_click("RX POWER"))
        self.btn_rx.grid(row=2, column=5, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_wifi24 = panel_boton_wifi_24(self, command=lambda: self._on_click("WIFI 2.4 GHz"))
        self.btn_wifi24.grid(row=2, column=6, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_wifi50 = panel_boton_wifi_50(self, command=lambda: self._on_click("WIFI 5.0 GHz"))
        self.btn_wifi50.grid(row=2, column=7, padx=5, pady=(0, 10), sticky="nsew")

        # Texto inferior
        self.lbl_texto = ctk.CTkLabel(
            self,
            text="PRUEBAS",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.COL_TEXT,
        )
        self.lbl_texto.grid(row=3, column=0, columnspan=8, pady=(0, 8), sticky="s")

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

        # Paleta actual (para set_table_rows en vistas etc.)
        self._palette = {}

        # Auto-aplicar tema si existe en root
        root = self.winfo_toplevel()
        if hasattr(root, "theme"):
            try:
                self.apply_theme(root.theme.palette())
            except Exception:
                pass

    # ------------------------------------------------------------
    # THEME
    # ------------------------------------------------------------
    def apply_theme(self, p: dict):
        """
        Ajusta colores del panel en base a la paleta global.
        """
        self._palette = dict(p or {})
        root = self.winfo_toplevel()
        mode = getattr(getattr(root, "theme", None), "mode", "light")

        bg = p.get("card", "#FFFFFF")
        border = p.get("border", "#8FA3B0")
        text = p.get("text", "#2C3E50")
        primary = p.get("primary", "#4EA5D9")
        primary_hover = p.get("primary_hover", "#3B8CC2")
        ok = p.get("ok", "#22C55E")
        err = p.get("error", "#EF4444")
        titulosColor = p.get("titulos", "#6B9080")

        self.COL_BG = bg
        self.COL_BORDER = border
        self.COL_TEXT = text
        self.COL_IDLE = primary
        self.COL_IDLE_HOVER = primary_hover
        self.COL_PASS = ok
        self.COL_FAIL = err
        self.COL_TITULO_VERDE = titulosColor

        # Frame: en claro lo dejamos "verdecito" como tu versión original
        if mode == "dark":
            frame_bg = bg
            frame_border = border
        else:
            frame_bg = "#D4E7D7"      # verde suave
            frame_border = "#6B9080"  # borde verde

        self.configure(fg_color=frame_bg, border_color=frame_border)

        # Labels
        self.lbl_texto_superior.configure(text_color=text)
        self.lbl_texto.configure(text_color=text)

        # Estado conexión conserva color según texto actual
        try:
            if str(self.lbl_estado.cget("text")).upper().startswith("CONECTADO"):
                self.lbl_estado.configure(text_color=titulosColor)
            else:
                self.lbl_estado.configure(text_color=err)
        except Exception:
            pass

        # Pintar botones a idle si están en reset
        for key, btn in self.test_buttons.items():
            try:
                # Si el botón trae un color "extraño" (por hardcode), lo normalizamos
                #btn.configure(fg_color=primary, hover_color=primary_hover, text_color="white")
                btn.configure(
                    fg_color=primary,
                    hover_color=primary_hover,
                    text_color="white",
                    border_width=0,              # <-- importante: quita el borde heredado
                    border_color=border,         # opcional, por si luego quieres usar borde
                    text_color_disabled="white", # por si alguno se deshabilita
                )
            except Exception:
                pass

    # ------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------
    def actualizar_estado_conexion(self, conectado: bool):
        if conectado:
            self.lbl_estado.configure(text="CONECTADO", text_color=self.COL_TITULO_VERDE)
        else:
            self.lbl_estado.configure(text="NO CONECTADO", text_color=self.COL_FAIL)

    def set_texto_superior(self, texto: str):
        self.lbl_texto_superior.configure(text=str(texto))

    def set_texto_inferior(self, texto: str):
        self.lbl_texto.configure(text=str(texto))

    def _set_button_status(self, test_key: str, status):
        btn = self.test_buttons.get(test_key)
        if not btn:
            return

        # Normalizamos
        if isinstance(status, str):
            status_norm = status.upper().strip()
        else:
            status_norm = status

        if status_norm is True or status_norm == "PASS":
            fg, hover = self.COL_PASS, self.COL_PASS
        elif status_norm is False or status_norm == "FAIL":
            fg, hover = self.COL_FAIL, self.COL_FAIL
        else:
            fg, hover = self.COL_IDLE, self.COL_IDLE_HOVER

        btn.configure(fg_color=fg, hover_color=hover, text_color="white")

    # ------------------------------------------------------------
    # Callback interno
    # ------------------------------------------------------------
    def _on_click(self, nombre_prueba: str):
        reset = soft = usb = fibra = wifi = False

        if nombre_prueba == "FACTORY RESET":
            reset = True
        elif nombre_prueba == "SOFTWARE":
            soft = True
        elif nombre_prueba == "USB PORT":
            usb = True
        elif nombre_prueba in ("TX POWER", "RX POWER"):
            fibra = True
        elif nombre_prueba in ("WIFI 2.4 GHz", "WIFI 5.0 GHz"):
            wifi = True

        # Delegar ejecución a la vista (para parar loop antes)
        if callable(getattr(self, "on_run_unit", None)):
            self.on_run_unit(reset, soft, usb, fibra, wifi, self.modelo)
        else:
            from src.backend.endpoints.conexion import iniciar_pruebaUnitariaConexion
            threading.Thread(
                target=iniciar_pruebaUnitariaConexion,
                args=(reset, soft, usb, fibra, wifi),
                kwargs={"model": self.modelo},
                daemon=True
            ).start()


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1100x250")
    root.title("Demo PanelPruebasConexion")

    panel = PanelPruebasConexion(root, modelo=None)
    panel.pack(fill="x", expand=True, padx=20, pady=20)

    root.mainloop()
