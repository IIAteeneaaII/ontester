# src/Frontend/viewmodels/tester_vm.py
import random
import sys
from pathlib import Path

import customtkinter as ctk

# Agregar la raíz del proyecto al path
root_path = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(root_path))

from src.Frontend.ui.tester_view import TesterView


class TesterViewModel:
    def __init__(self, view: TesterView):
        self.view = view
        # Registrar VM en la vista
        self.view.viewmodel = self

    def ejecutar_prueba(self):
        """
        Aquí iría la lógica real de testeo.
        Por ahora simulamos con un random True/False.
        """
        resultado_ok = random.choice([True, False])
        print(f"[VM] Resultado simulado de prueba: {resultado_ok}")

        # Actualizar estado visual
        self.view.actualizar_estado_prueba(resultado_ok)
        # Incrementar contador de pruebas realizadas
        self.view.incrementar_contador_pruebas()


# Main solo para probar VM + View juntos
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()
    app.title("Tester View + ViewModel")
    app.geometry("1000x600")

    view = TesterView(app)          # creamos la vista
    vm = TesterViewModel(view)      # la conectamos al VM
    view.pack(fill="both", expand=True)

    app.mainloop()
