# src/Frontend/navigation/botones.py
import customtkinter as ctk
from pathlib import Path
from PIL import Image

# Carpeta de iconos
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "icons"


def _cargar_icono(nombre_archivo: str, size=(20, 20)):
    ruta = ASSETS_DIR / nombre_archivo
    if ruta.exists():
        return ctk.CTkImage(
            light_image=Image.open(ruta),
            dark_image=Image.open(ruta),
            size=size,
        )
    return None


# ====== Iconos barra izquierda ======
OMITIR_ICON         = _cargar_icono("omitir_icon.png")
ETHERNET_ICON       = _cargar_icono("ethernet_icon.png")
CONECTIVIDAD_ICON   = _cargar_icono("conectividad_icon.png")
OTROS_PUERTOS_ICON  = _cargar_icono("otros_puertos_icon.png")
WIFI_ICON           = _cargar_icono("wifi_icon.png")
# ====================================


# -------------------------------------------------------------------
# ESTILOS BASE (SIN COLORES FIJOS) -> el theme los aplicará después
# -------------------------------------------------------------------
BTN_BASE = {
    "height": 36,
    "corner_radius": 8,
    "font": ("Segoe UI", 13, "bold"),
    "anchor": "w",
    "border_spacing": 12,
    "border_width": 1,
}

PANEL_BTN_BASE = {
    "height": 70,
    "corner_radius": 6,
    "font": ("Segoe UI", 11, "bold"),
    "border_width": 1,
}

TOP_BTN_BASE = {
    "height": 100,
    "corner_radius": 10,
    "font": ("Segoe UI", 12, "bold"),
}


def _tag(btn: ctk.CTkButton, role: str):
    """
    Guardamos un rol para aplicar theme después desde la vista.
    role: 'sidebar', 'sidebar-danger', 'panel', 'top', etc.
    """
    btn._theme_role = role
    return btn


# ========= Botones barra izquierda =========
def boton_OMITIR(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="RESET DE FÁBRICA",
        image=OMITIR_ICON,
        compound="left" if OMITIR_ICON is not None else "center",
        command=command,
        **BTN_BASE,
    )
    btn._icon_omitir = OMITIR_ICON
    return _tag(btn, "sidebar")


def boton_Ethernet(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE ETHERNET",
        image=ETHERNET_ICON,
        compound="left" if ETHERNET_ICON is not None else "center",
        command=command,
        **BTN_BASE,
    )
    btn._icon_ethernet = ETHERNET_ICON
    return _tag(btn, "sidebar")


def boton_Conectividad(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE CONECTIVIDAD",
        image=CONECTIVIDAD_ICON,
        compound="left" if CONECTIVIDAD_ICON is not None else "center",
        command=command,
        **BTN_BASE,
    )
    btn._icon_conectividad = CONECTIVIDAD_ICON
    return _tag(btn, "sidebar")


def boton_Otrospuertos(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE OTROS PUERTOS",
        image=OTROS_PUERTOS_ICON,
        compound="left" if OTROS_PUERTOS_ICON is not None else "center",
        command=command,
        **BTN_BASE,
    )
    btn._icon_otros_puertos = OTROS_PUERTOS_ICON
    return _tag(btn, "sidebar")


def boton_señaleswifi(parent, command=None):
    btn = ctk.CTkButton(
        parent,
        text="PRUEBA DE SEÑALES WIFI",
        image=WIFI_ICON,
        compound="left" if WIFI_ICON is not None else "center",
        command=command,
        **BTN_BASE,
    )
    btn._icon_wifi = WIFI_ICON
    return _tag(btn, "sidebar")


def boton_salir(parent, command=None):
    kwargs = BTN_BASE.copy()
    kwargs.update({
        "anchor": "center",
        "border_spacing": 0,
        "height": 32,
        "corner_radius": 6,
    })
    btn = ctk.CTkButton(
        parent,
        text="SALIR",
        command=command,
        **kwargs,
    )
    return _tag(btn, "sidebar-danger")
# =============================================


# ========= Botones superiores grandes (si los usas en otra vista) =========
def boton_cambiar_estacion(parent, command=None):
    btn = ctk.CTkButton(parent, text="CAMBIAR ESTACIÓN\n👤", command=command, **TOP_BTN_BASE)
    return _tag(btn, "top")

def boton_modificar_etiquetado(parent, command=None):
    btn = ctk.CTkButton(parent, text="MODIFICAR ETIQUETADO\n🏷️", command=command, **TOP_BTN_BASE)
    return _tag(btn, "top")

def boton_modificar_parametros(parent, command=None):
    btn = ctk.CTkButton(parent, text="MODIFICAR PARÁMETROS\n⚙️", command=command, **TOP_BTN_BASE)
    return _tag(btn, "top")

def boton_prueba(parent, command=None):
    btn = ctk.CTkButton(parent, text="PRUEBA\n🔧", command=command, **TOP_BTN_BASE)
    return _tag(btn, "top")
# =============================================


# ========= Botones del panel central =========
def panel_boton_ping(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="PING", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_factory_reset(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="FACTORY RESET", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_software(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="SOFTWARE", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_usb_port(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="USB PORT", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_tx_power(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="TX POWER", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_rx_power(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="RX POWER", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_wifi_24(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="WIFI 2.4 GHz", command=command, **kw)
    return _tag(btn, "panel")

def panel_boton_wifi_50(parent, command=None, **over):
    kw = PANEL_BTN_BASE.copy(); kw.update(over)
    btn = ctk.CTkButton(parent, text="WIFI 5.0 GHz", command=command, **kw)
    return _tag(btn, "panel")
# =============================================


# ========= Botones del panel de detalles =========
def boton_imprimir_etiqueta(parent, command=None):
    imprimir_icon = _cargar_icono("printer_icon.png", size=(24, 24))
    btn = ctk.CTkButton(
        parent,
        text="IMPRIMIR ETIQUETA",
        image=imprimir_icon,
        compound="top" if imprimir_icon is not None else "center",
        command=command,
        height=100,
        corner_radius=8,
        font=("Segoe UI", 12, "bold"),
        border_width=1,
    )
    return _tag(btn, "panel-primary")


def boton_borrar(parent, command=None):
    borrar_icon = _cargar_icono("delete_icon.png", size=(24, 24))
    btn = ctk.CTkButton(
        parent,
        text="BORRAR",
        image=borrar_icon,
        compound="top" if borrar_icon is not None else "center",
        command=command,
        height=100,
        corner_radius=8,
        font=("Segoe UI", 12, "bold"),
        border_width=1,
    )
    return _tag(btn, "panel-danger")
