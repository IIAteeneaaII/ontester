# src/Frontend/navigation/botones.py
import customtkinter as ctk
from pathlib import Path
from PIL import Image

# ---------- Estilo común: barra izquierda ----------
BTN_KWARGS = {
    "height": 36,
    "corner_radius": 8,
    "font": ("Segoe UI", 13, "bold"),
    "anchor": "w",         # contenido alineado a la izquierda
    "border_spacing": 12,  # margen interno desde el borde izquierdo
    # colores base (azul pastel)
    "fg_color": "#4EA5D9",
    "hover_color": "#3B8CC2",
    "text_color": "white",
}

# ---------- Estilo común: botones del panel central ----------
PANEL_BTN_KWARGS = {
    "height": 70,
    "corner_radius": 6,
    "font": ("Segoe UI", 11, "bold"),
    # mismos colores que barra izquierda, para consistencia
    "fg_color": "#4EA5D9",
    "hover_color": "#3B8CC2",
    "text_color": "white",
}

# ---------- Estilo común: botones superiores grandes ----------
TOP_BTN_KWARGS = {
    "height": 100,
    "corner_radius": 10,
    "font": ("Segoe UI", 12, "bold"),
    "text_color": "#2C3E50",
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


# ====== Iconos barra izquierda ======
OMITIR_ICON         = _cargar_icono("omitir_icon.png")
ETHERNET_ICON       = _cargar_icono("ethernet_icon.png")
CONECTIVIDAD_ICON   = _cargar_icono("conectividad_icon.png")
OTROS_PUERTOS_ICON  = _cargar_icono("otros_puertos_icon.png")
WIFI_ICON           = _cargar_icono("wifi_icon.png")
# ====================================


# ========= Botones barra izquierda =========
def boton_OMITIR(parent, command=None):
    """Botón para omitir retest de fábrica, con icono a la izquierda."""
    btn = ctk.CTkButton(
        parent,
        text="RESET DE FÁBRICA",
        image=OMITIR_ICON,
        compound="left" if OMITIR_ICON is not None else "center",
        command=command,
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
        **BTN_KWARGS
    )
    btn._icon_wifi = WIFI_ICON
    return btn


def boton_salir(parent, command=None):
    """
    Botón rojo de SALIR para el bloque inferior del sidebar.
    Mantiene la altura más pequeña y texto centrado.
    """
    kwargs = BTN_KWARGS.copy()
    # Para que el texto vaya centrado y sin sangría
    kwargs.update({
        "anchor": "center",
        "border_spacing": 0,
        "height": 32,
        # Colores específicos de salir (no azules)
        "fg_color": "#F28B82",
        "hover_color": "#E0665C",
    })

    return ctk.CTkButton(
        parent,
        text="SALIR",
        command=command,
        text_color="white",
        corner_radius=6,
        **kwargs,
    )
# =============================================


# ========= Botones superiores grandes (4 botones principales) =========
def boton_cambiar_estacion(parent, command=None):
    """Botón gris para cambiar estación."""
    return ctk.CTkButton(
        parent,
        text="CAMBIAR ESTACIÓN\n👤",
        command=command,
        fg_color="#B8B8B8",
        hover_color="#A0A0A0",
        **TOP_BTN_KWARGS
    )


def boton_modificar_etiquetado(parent, command=None):
    """Botón rosa para modificar etiquetado."""
    return ctk.CTkButton(
        parent,
        text="MODIFICAR ETIQUETADO\n🏷️",
        command=command,
        fg_color="#F1B4BB",
        hover_color="#E89BA3",
        **TOP_BTN_KWARGS
    )


def boton_modificar_parametros(parent, command=None):
    """Botón azul para modificar parámetros."""
    return ctk.CTkButton(
        parent,
        text="MODIFICAR PARÁMETROS\n⚙️",
        command=command,
        fg_color="#A8DADC",
        hover_color="#8FC9CB",
        **TOP_BTN_KWARGS
    )


def boton_prueba(parent, command=None):
    """Botón rosa para prueba."""
    return ctk.CTkButton(
        parent,
        text="PRUEBA\n🔧",
        command=command,
        fg_color="#F1B4BB",
        hover_color="#E89BA3",
        **TOP_BTN_KWARGS
    )


def boton_nuevo_tema(parent, command=None):
    """Botón naranja para nuevo tema."""
    return ctk.CTkButton(
        parent,
        text="NUEVO TEMA\n📋",
        command=command,
        fg_color="#F4A261",
        hover_color="#E89350",
        **TOP_BTN_KWARGS
    )
# =============================================


# ========= Botones del panel central =========
# (los 8 cuadritos: PING, FACTORY RESET, SOFTWARE, USB PORT, TX POWER, RX POWER, WIFI 2.4, WIFI 5.0)

def panel_boton_ping(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="PING",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_factory_reset(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="FACTORY RESET",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_software(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="SOFTWARE",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_usb_port(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="USB PORT",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_tx_power(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="TX POWER",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_rx_power(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="RX POWER",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_wifi_24(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="WIFI 2.4 GHz",
        command=command,
        **PANEL_BTN_KWARGS
    )


def panel_boton_wifi_50(parent, command=None):
    return ctk.CTkButton(
        parent,
        text="WIFI 5.0 GHz",
        command=command,
        **PANEL_BTN_KWARGS
    )
# =============================================


# ========= Botones del panel de detalles =========
# Botones para el panel derecho de "Escaneos del día"

def boton_imprimir_etiqueta(parent, command=None):
    """
    Botón azul claro para imprimir etiqueta.
    Incluye ícono de impresora si está disponible.
    """
    imprimir_icon = _cargar_icono("printer_icon.png", size=(24, 24))
    return ctk.CTkButton(
        parent,
        text="IMPRIMIR ETIQUETA",
        image=imprimir_icon,
        compound="top" if imprimir_icon is not None else "center",
        command=command,
        height=100,
        corner_radius=8,
        font=("Segoe UI", 12, "bold"),
        fg_color="#5DADE2",
        hover_color="#3498DB",
        text_color="white",
    )


def boton_borrar(parent, command=None):
    """
    Botón rojo/rosado para borrar registro.
    Incluye ícono de basurero si está disponible.
    """
    borrar_icon = _cargar_icono("delete_icon.png", size=(24, 24))
    return ctk.CTkButton(
        parent,
        text="BORRAR",
        image=borrar_icon,
        compound="top" if borrar_icon is not None else "center",
        command=command,
        height=100,
        corner_radius=8,
        font=("Segoe UI", 12, "bold"),
        fg_color="#EC7063",
        hover_color="#E74C3C",
        text_color="white",
    )
# ================================================