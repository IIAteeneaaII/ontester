# src/Frontend/ui/escaneos_dia_view.py

import customtkinter as ctk
import sys
from pathlib import Path

# Para poder usar imports absolutos (igual que en tester_view)
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.panel_pruebas_view import PanelPruebasConexion


class EscaneosDiaView(ctk.CTkFrame):
    """
    Vista para 'Escaneos del día'.

    De momento sólo muestra:
      - Un título en la parte superior.
      - El mismo panel de pruebas de conectividad (PanelPruebasConexion)
        reutilizado en la parte inferior.
    """
    def __init__(self, parent, viewmodel=None, **kwargs):
        # Fondo azul claro, consistente con TesterView
        super().__init__(parent, fg_color="#E9F5FF", **kwargs)

        self.viewmodel = viewmodel

        # Layout básico: un solo frame interno que contiene todo
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=0, sticky="nsew", padx=40, pady=30)

        # ---------- Título de la ventana ----------
        titulo = ctk.CTkLabel(
            self.main_content,
            text="Escaneos del día",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#2C3E50",
        )
        titulo.pack(side="top", anchor="w", pady=(0, 20))

        # Aquí podrías agregar tablas / filtros de escaneos más adelante
        # frame_datos = ctk.CTkFrame(self.main_content, fg_color="transparent")
        # frame_datos.pack(expand=True, fill="both")

        # ---------- Contenedor de pruebas (reutilizado) ----------
        self.panel_pruebas = PanelPruebasConexion(self.main_content)
        self.panel_pruebas.pack(
            side="bottom",
            fill="x",
            expand=False,
            padx=0,
            pady=(20, 10),
        )
        # ------------------------------------------


# Para probar esta vista de forma independiente
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Escaneos del día")
    app.geometry("1000x500")

    view = EscaneosDiaView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()
