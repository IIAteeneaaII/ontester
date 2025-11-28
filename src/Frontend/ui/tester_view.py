import customtkinter as ctk
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
        
        # Aquí puedes agregar el contenido principal
        content_label = ctk.CTkLabel(
            right_frame,
            text="Área de contenido principal",
            font=ctk.CTkFont(size=16)
        )
        content_label.pack(expand=True)
    
    # Comandos para los botones
    def ir_inicio(self):
        print("Navegando a Inicio")
        # Aquí agregarás la lógica de navegación
    
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