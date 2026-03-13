import os
import sys
import subprocess
from pathlib import Path
from src.backend.endpoints.conexion import cargar_version
import psutil
import requests
from pathlib import Path

# Descargar el actualizador
def download_update_installer(version: str):
    """
    Función que descarga el instalador y devuelve:
    bool: Indica si se completó la descarga o no
    str: Indica la ruta de descarga
    """
    # Validar si la versión es diferente a la actual
    ver_actual = cargar_version()
    if (ver_actual != version):
        print(f"[ACTUALIZADOR] Actualizando de {ver_actual} a {version}")
    # TODO poner este bloque dentro de la lógica
    # Conectarse y descargar del bucket
    url = ""
    dest = Path("C:/Users/Admin/Documents/NextGen")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=15) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                if chunk:
                    f.write(chunk)
    return True, "ruta"

# Matar los procesos necesarios
def kill_processes_by_name(names: set[str]) -> None:
    """
    Mata los procesos que impiden la instalación del tester
    kill_processes_by_name({"chromedriver.exe", "cmd.exe"})  
    """
    for p in psutil.process_iter(["name"]):
        try:
            if (p.info["name"] or "").lower() in names:
                p.terminate()
        except Exception:
            pass
# Lanzar el instalador
def launch_inno_setup(installer_path: str, *, install_formatos: bool = False, silent: bool = True) -> None:
    """
    Lanza un instalador Inno Setup y sale del proceso actual.
    - install_formatos: si quieres marcar el task "instalar_formatos"
    - silent: True para /VERYSILENT (auto-update), False para modo normal
    """
    installer = Path(installer_path)
    if not installer.exists():
        raise FileNotFoundError(installer)

    args = []
    if silent:
        args += ["/SILENT", "/NOCANCEL","/NORESTART"]
        # (opcional) log para debugging:
        # args += [f'/LOG="{str(Path(os.getenv("TEMP","C:\\\\Temp")) / "ont_setup.log")}"']

    # Si tu instalador usa Tasks (como "instalar_formatos")
    if install_formatos:
        args += [r'/TASKS="instalar_formatos"']
    else:
        # fuerza a que NO se seleccione ese task si quedó guardado de antes
        args += [r'/TASKS=""']

    # Lanza separado para que sobreviva aunque tu app se cierre
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS

    subprocess.Popen(
        [str(installer)] + args,
        close_fds=True,
        creationflags=creationflags
    )

    # IMPORTANTÍSIMO: salir para liberar archivos en C:\ONT
    os._exit(0)