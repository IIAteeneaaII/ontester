import customtkinter as ctk
from src.Frontend.navigation.botones import (
    boton_inicio,
    boton_escaneos,
    boton_propiedades,
    boton_reporte,
    boton_tester
)

class Navigator(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        # Crear botones
        boton_inicio(self, command=self.ir_inicio).pack(side="left", padx=5)
        boton_escaneos(self, command=self.ir_escaneos).pack(side="left", padx=5)
        boton_propiedades(self, command=self.ir_propiedades).pack(side="left", padx=5)
        boton_reporte(self, command=self.ir_reporte).pack(side="left", padx=5)
        boton_tester(self, command=self.ir_tester).pack(side="left", padx=5)
    
    def ir_inicio(self):
        print("Ir a Inicio")
        # Tu lógica aquí
    
    def ir_escaneos(self):
        print("Ir a Escaneos")
        # Tu lógica aquí
    
    def ir_propiedades(self):
        print("Ir a Propiedades")
    
    def ir_reporte(self):
        print("Ir a Reporte")
    
    def ir_tester(self):
        print("Ir a Tester")