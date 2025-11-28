import customtkinter as ctk

def boton_OMITIR(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="OMITIR RETEST DE FÁBRICA",
        command=command
    )

def boton_escaneos(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="Escaneos",
        command=command
    )

def boton_propiedades(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="Propiedades",
        command=command
    )

def boton_reporte(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="Reporte Global",
        command=command
    )

def boton_tester(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="Tester",
        command=command
    )