import customtkinter as ctk
from src.Frontend.navigation.navigator import Navigator

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("OnTester")
        self.geometry("800x600")
        
        # Navegador
        nav = Navigator(self)
        nav.pack(pady=20, padx=20, fill="x")

if __name__ == "__main__":
    app = App()
    app.mainloop()