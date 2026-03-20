import os
import subprocess
from pathlib import Path

import psutil
import requests

from src.backend.endpoints.conexion import cargar_version
from src.backend.sua_client.sua_acceso import get_auth_headers
from src.backend.sua_client.settings import SUA_BASE_URL


DOWNLOAD_DIR = Path("C:/Users/Admin/Documents/NextGen")


def download_update_installer_from_url(version: str, url: str, installer_name: str):
    """
    Descarga instalador desde URL presignada.
    """
    from src.backend.sua_client.update_state import set_pending_update_target_version

    ver_actual = cargar_version()
    if ver_actual == version:
        print(f"[ACTUALIZADOR] Ya está en versión {version}")
        return False, ""

    print(f"[ACTUALIZADOR] Actualizando de {ver_actual} a {version}")

    # Guardar versión pendiente antes de descargar/instalar
    set_pending_update_target_version(
        version=version,
        installer_name=installer_name
    )

    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    dest_file = DOWNLOAD_DIR / installer_name

    with requests.get(url, stream=True, timeout=30) as r:
        r.raise_for_status()
        with open(dest_file, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)

    return True, str(dest_file)

def request_latest_update_info():
    """
    Pide a SSUA la última actualización disponible.
    Debe devolver JSON con:
      version, installer_url, installer_name
    """
    url = f"{SUA_BASE_URL}/api/instalador/updates"
    headers = get_auth_headers()

    r = requests.get(url, headers=headers, timeout=20)
    r.raise_for_status()
    return r.json()


def download_update_installer():
    """
    Flujo manual:
    1. pide a SSUA la info del último instalador
    2. guarda la target_version pendiente
    3. descarga el exe
    """
    from src.backend.sua_client.update_state import set_pending_update_target_version

    data = request_latest_update_info()

    version = data.get("version")
    installer_url = data.get("installer_url")
    installer_name = data.get("installer_name")

    if not version or not installer_url or not installer_name:
        raise RuntimeError("Respuesta incompleta del endpoint de actualización")

    # Guardar la versión pendiente para confirmar al siguiente arranque
    set_pending_update_target_version(
        version=version,
        installer_name=installer_name
    )

    return download_update_installer_from_url(
        version=version,
        url=installer_url,
        installer_name=installer_name
    )

def kill_processes_by_name(names: set[str]) -> None:
    normalized = {n.lower() for n in names}

    for p in psutil.process_iter(["name"]):
        try:
            process_name = (p.info["name"] or "").lower()
            if process_name in normalized:
                p.terminate()
        except Exception:
            pass


def launch_inno_setup(installer_path: str, *, install_formatos: bool = False, silent: bool = True) -> None:
    installer = Path(installer_path)
    if not installer.exists():
        raise FileNotFoundError(installer)

    args = []
    if silent:
        args += ["/SILENT", "/NOCANCEL", "/NORESTART"]

    if install_formatos:
        args += [r'/TASKS="instalar_formatos"']
    else:
        args += [r'/TASKS=""']

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    subprocess.Popen(
        [str(installer)] + args,
        close_fds=True,
        creationflags=creationflags
    )

    os._exit(0)