import os
import sys
import subprocess
from pathlib import Path
import psutil

# Descargar el actualizador
def download_update_installer(version: str):
    """
    Función que descarga el instalador y devuelve:
    bool: Indica si se completó la descarga o no
    str: Indica la ruta de descarga
    """
    
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