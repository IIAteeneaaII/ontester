import customtkinter as ctk
import sys
from pathlib import Path
from datetime import datetime

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
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Configurar grid
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Frame izquierdo (columna de navegación)
        left_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        left_frame.grid_propagate(False)
        
        # Título "Escoge tu modo"
        titulo = ctk.CTkLabel(
            left_frame,
            text="Escoge tu modo",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        titulo.pack(pady=(20, 30), padx=20)
        
        # Botones importados
        boton_inicio(left_frame, command=self.ir_inicio).pack(pady=10, padx=20, fill="x")
        boton_escaneos(left_frame, command=self.ir_escaneos).pack(pady=10, padx=20, fill="x")
        boton_propiedades(left_frame, command=self.ir_propiedades).pack(pady=10, padx=20, fill="x")
        boton_reporte(left_frame, command=self.ir_reporte).pack(pady=10, padx=20, fill="x")
        boton_tester(left_frame, command=self.ir_tester).pack(pady=10, padx=20, fill="x")
        
        # Frame derecho (área principal/contenido)
        right_frame = ctk.CTkFrame(self, corner_radius=0)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
        
        # Reloj en tiempo real
        self.clock_label = ctk.CTkLabel(
            right_frame,
            text="",
            font=ctk.CTkFont(size=20)
        )
        self.clock_label.pack(pady=20, padx=20, anchor="nw")
        
        # Iniciar actualización del reloj
        self.update_clock()
        
        # Área de contenido principal
        content_label = ctk.CTkLabel(
            right_frame,
            text="Área de contenido principal",
            font=ctk.CTkFont(size=16)
        )
        content_label.pack(expand=True)
    
    def update_clock(self):
        """Actualiza el reloj cada segundo"""
        now = datetime.now()
        time_string = now.strftime("%I:%M %p  %d %B %Y")
        # Reemplazar nombres de mes en inglés por español
        meses = {
            'January': 'enero', 'February': 'febrero', 'March': 'marzo',
            'April': 'abril', 'May': 'mayo', 'June': 'junio',
            'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
            'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
        }
        for eng, esp in meses.items():
            time_string = time_string.replace(eng, esp)
        
        self.clock_label.configure(text=time_string)
        # Actualizar cada 1000ms (1 segundo)
        self.after(1000, self.update_clock)
    
    # Comandos para los botones
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

# Para probar la vista individualmente
if __name__ == "__main__":
    app = ctk.CTk()
    app.title("Tester View")
    app.geometry("1000x600")
    
    view = TesterView(app)
    view.pack(fill="both", expand=True)
    
    app.mainloop()