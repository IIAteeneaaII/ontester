import customtkinter as ctk
import sys
from pathlib import Path
from datetime import datetime
from PIL import Image

# Agregar la raíz del proyecto al path
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.navigation.botones import (
    boton_inicio,
    boton_escaneos,
    boton_propiedades,
    boton_reporte,
    boton_tester
)


class TesterView(ctk.CTkFrame):
    def __init__(self, parent, viewmodel=None, **kwargs):
        super().__init__(parent, **kwargs)

        # Referencia opcional al ViewModel
        self.viewmodel = viewmodel
        self._last_result_ok = False         # para pruebas sin VM
        self.pruebas_realizadas = 0          # contador de pruebas

        # Configurar grid general
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Frame izquierdo (columna de navegación)
        left_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        left_frame.grid_propagate(False)

        # ===== Logo circular en la parte superior izquierda =====
        assets_dir = Path(__file__).parent.parent / "assets" / "icons"
        logo_path = assets_dir / "logo_tester.png"

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

        # ===== Menú desplegable "Escoge tu modo" =====
        self.modo_var = ctk.StringVar(value="Escoge tu modo")
        self.modo_menu = ctk.CTkOptionMenu(
            left_frame,
            variable=self.modo_var,
            values=["Testeo", "Retesteo", "Etiqueta"],
            command=self.cambiar_modo,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.modo_menu.pack(pady=(20, 30), padx=20, fill="x")
        # =============================================

        # Botones importados
        boton_inicio(left_frame, command=self.ir_inicio).pack(pady=10, padx=20, fill="x")
        boton_escaneos(left_frame, command=self.ir_escaneos).pack(pady=10, padx=20, fill="x")
        boton_propiedades(left_frame, command=self.ir_propiedades).pack(pady=10, padx=20, fill="x")
        boton_reporte(left_frame, command=self.ir_reporte).pack(pady=10, padx=20, fill="x")
        boton_tester(left_frame, command=self.ir_tester).pack(pady=10, padx=20, fill="x")

        # Frame derecho (área principal/contenido)
        right_frame = ctk.CTkFrame(self, corner_radius=0)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # ========= BARRA SUPERIOR COMPLETA =========
        # [ Prueba: EXITOSA ]   [ reloj ]   [ Pruebas realizadas: N ]
        top_bar = ctk.CTkFrame(right_frame, fg_color="transparent")
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

        # Área de contenido principal
        self.content_label = ctk.CTkLabel(
            right_frame,
            text="Área de contenido principal",
            font=ctk.CTkFont(size=16)
        )
        self.content_label.pack(expand=True)

        # Iniciar actualización del reloj
        self.update_clock()

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
        self.content_label.configure(text=f"Modo actual: {modo}")

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

    # ================= HANDLERS DE LOS BOTONES =================

    def ir_inicio(self):
        print("Navegando a Inicio")

    def ir_escaneos(self):
        print("Navegando a Escaneos")

    def ir_propiedades(self):
        print("Navegando a Propiedades")

    def ir_reporte(self):
        print("Navegando a Reporte")

    def ir_tester(self):
        print("Navegando a Tester")
        # Si hay ViewModel, que él maneje la prueba real
        if self.viewmodel is not None:
            self.viewmodel.ejecutar_prueba()
        else:
            # Demo sin VM: alterna EXITOSA/FALLIDA y suma al contador
            self._last_result_ok = not self._last_result_ok
            self.actualizar_estado_prueba(self._last_result_ok)
            self.incrementar_contador_pruebas()


# Para probar la vista individualmente (sin VM)
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Tester View")
    app.geometry("1000x600")

    view = TesterView(app)
    view.pack(fill="both", expand=True)

    app.mainloop()
