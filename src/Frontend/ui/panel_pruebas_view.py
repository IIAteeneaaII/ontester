# src/Frontend/ui/panel_pruebas_view.py
import sys
from pathlib import Path

import customtkinter as ctk

# Para poder hacer import de navigation.botones
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
      - Label superior: CONECTADO / NO CONECTADO
      - 8 botones de prueba en una fila.
    """
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        # Apariencia del marco contenedor
        self.configure(
            corner_radius=10,
            fg_color="#ecf0f1",   # gris claro tipo tarjeta
        )

        # Columnas para los 8 botones
        for col in range(8):
            self.grid_columnconfigure(col, weight=1)

        # ----- Label de estado de conexión -----
        self.lbl_estado = ctk.CTkLabel(
            self,
            text="NO CONECTADO",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#e74c3c",    # rojo
        )
        self.lbl_estado.grid(
            row=0,
            column=0,
            columnspan=8,
            pady=(10, 15),
            sticky="n"
        )

        # ----- Fila de botones -----
        # fila 1, columnas 0..7
        self.btn_ping = panel_boton_ping(self, command=lambda: self._on_click("PING"))
        self.btn_ping.grid(row=1, column=0, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_factory = panel_boton_factory_reset(self, command=lambda: self._on_click("FACTORY RESET"))
        self.btn_factory.grid(row=1, column=1, padx=7, pady=(0, 10), sticky="nsew")

        self.btn_software = panel_boton_software(self, command=lambda: self._on_click("SOFTWARE"))
        self.btn_software.grid(row=1, column=2, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_usb = panel_boton_usb_port(self, command=lambda: self._on_click("USB PORT"))
        self.btn_usb.grid(row=1, column=3, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_tx = panel_boton_tx_power(self, command=lambda: self._on_click("TX POWER"))
        self.btn_tx.grid(row=1, column=4, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_rx = panel_boton_rx_power(self, command=lambda: self._on_click("RX POWER"))
        self.btn_rx.grid(row=1, column=5, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_wifi24 = panel_boton_wifi_24(self, command=lambda: self._on_click("WIFI 2.4 GHz"))
        self.btn_wifi24.grid(row=1, column=6, padx=5, pady=(0, 10), sticky="nsew")

        self.btn_wifi50 = panel_boton_wifi_50(self, command=lambda: self._on_click("WIFI 5.0 GHz"))
        self.btn_wifi50.grid(row=1, column=7, padx=5, pady=(0, 10), sticky="nsew")

    # --------- API pública útil ---------

    def actualizar_estado_conexion(self, conectado: bool):
        """
        Cambia el texto y color del label superior:
          True  -> CONECTADO (verde)
          False -> NO CONECTADO (rojo)
        """
        if conectado:
            self.lbl_estado.configure(
                text="CONECTADO",
                text_color="#2ecc71"  # verde
            )
        else:
            self.lbl_estado.configure(
                text="NO CONECTADO",
                text_color="#e74c3c"  # rojo
            )

    # Este método lo puedes usar para debug o para enlazar lógica real.
    def _on_click(self, nombre_prueba: str):
        print(f"[PanelPruebasConexion] Click en {nombre_prueba}")


# Para probar el panel por separado
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = ctk.CTk()
    root.geometry("1100x250")
    root.title("Demo PanelPruebasConexion")

    panel = PanelPruebasConexion(root)
    panel.pack(fill="x", expand=True, padx=20, pady=20)

    root.mainloop()
