import customtkinter as ctk
from pathlib import Path
from PIL import Image

# Estilo común para los botones de la barra izquierda
BTN_KWARGS = {
    "height": 36,
    "corner_radius": 8,
    "font": ("Segoe UI", 13, "bold"),
    "anchor": "w",         # contenido alineado a la izquierda
    "border_spacing": 12,  # margen interno desde el borde izquierdo
}

# Carpeta de iconos
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


def _cargar_icono(nombre_archivo: str, size=(20, 20)):
    """
    Intenta cargar un CTkImage desde assets/icons.
    Si el archivo no existe, regresa None (para no tronar la app).
    """
    ruta = ASSETS_DIR / nombre_archivo
    if ruta.exists():
        return ctk.CTkImage(
            light_image=Image.open(ruta),
            dark_image=Image.open(ruta),
            size=size,
        )
    return None


# ====== Iconos ======
OMITIR_ICON         = _cargar_icono("omitir_icon.png")
ETHERNET_ICON       = _cargar_icono("ethernet_icon.png")
CONECTIVIDAD_ICON   = _cargar_icono("conectividad_icon.png")
OTROS_PUERTOS_ICON  = _cargar_icono("otros_puertos_icon.png")
WIFI_ICON           = _cargar_icono("wifi_icon.png")
# ====================


def boton_OMITIR(parent, command=None):
    """Botón para omitir retest de fábrica, con icono a la izquierda."""
    btn = ctk.CTkButton(
        parent,
        text="OMITIR RETEST DE FÁBRICA",
        image=OMITIR_ICON,
        compound="left" if OMITIR_ICON is not None else "center",
        command=command,
        hover_color="#1e8449",
        **BTN_KWARGS
    )
    btn._icon_omitir = OMITIR_ICON
    return btn


def boton_Ethernet(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE ETHERNET",
        image=ETHERNET_ICON,
        compound="left" if ETHERNET_ICON is not None else "center",
        command=command,
        hover_color="#1e8449",
        **BTN_KWARGS
    )
    btn._icon_ethernet = ETHERNET_ICON
    return btn


def boton_Conectividad(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE CONECTIVIDAD",
        image=CONECTIVIDAD_ICON,
        compound="left" if CONECTIVIDAD_ICON is not None else "center",
        command=command,
        hover_color="#1e8449",
        **BTN_KWARGS
    )
    btn._icon_conectividad = CONECTIVIDAD_ICON
    return btn


def boton_Otrospuertos(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE OTROS PUERTOS",
        image=OTROS_PUERTOS_ICON,
        compound="left" if OTROS_PUERTOS_ICON is not None else "center",
        command=command,
        hover_color="#1e8449",
        **BTN_KWARGS
    )
    btn._icon_otros_puertos = OTROS_PUERTOS_ICON
    return btn


def boton_señaleswifi(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE SEÑALES WIFI",
        image=WIFI_ICON,
        compound="left" if WIFI_ICON is not None else "center",
        command=command,
        hover_color="#1e8449",
        **BTN_KWARGS
    )
    btn._icon_wifi = WIFI_ICON
    return btn
