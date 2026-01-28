import sys
from pathlib import Path
import uuid

def get_pc_id_from_mac_suffix(prefix="ONT") -> str:
    mac = uuid.getnode()
    mac_hex = f"{mac:012x}".upper()
    return f"{prefix}-{mac_hex[-6:]}"  # ONT-3A9F2C

def resource_path(*relative_parts: str) -> Path:
    """
    Devuelve la ruta absoluta a un recurso (imagen, etc.),
    funcionando tanto en desarrollo como en el ejecutable de PyInstaller.
    """
    # Cuando está congelado con PyInstaller, existe sys._MEIPASS
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(sys._MEIPASS)
    else:
        # Modo normal: base = raíz del proyecto (ajusta si lo necesitas)
        base_path = Path(__file__).resolve().parents[2]  # src/utils -> src -> raíz

    return base_path.joinpath(*relative_parts)