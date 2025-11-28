from tkinter import *
import customtkinter

customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

root = customtkinter.CTk()
root.title('Tkinter.com - Custom Tkinter!')
# root.iconbitmap('images/codemy.ico')  # Comentado - archivo no existe
root.geometry('600x350')

my_button = customtkinter.CTkButton(root, text="Hello World!!!")
my_button.pack(pady=80)

root.mainloop()
