import customtkinter as ctk

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Mi App")
        self.geometry("1100x700")

        self.content = ctk.CTkFrame(self)
        self.content.pack(fill="both", expand=True)

        # Vista inicial
        from propiedades_view import PropiedadesView
        self.show_view(PropiedadesView)

    def show_view(self, ViewClass):
        # Borra lo actual
        for w in self.content.winfo_children():
            w.destroy()

        # Crea la nueva vista
        view = ViewClass(self.content, app=self)
        view.pack(fill="both", expand=True)
