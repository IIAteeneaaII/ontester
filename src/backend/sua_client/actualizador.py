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
    url = "https://amzn-s3-sua-ontester.s3.us-east-1.amazonaws.com/ONT_TESTER_RAM_SETUP_FULL_1.7.1.1N.exe?response-content-disposition=inline&X-Amz-Content-Sha256=UNSIGNED-PAYLOAD&X-Amz-Security-Token=IQoJb3JpZ2luX2VjELT%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIAnUmITQrBJRzcg7TlCy%2FSQBH3DbomFe3l4SIG%2Fe%2BgYDAiEAyykyyIQQ%2BwfQx35XN%2BcqGFspZQ559oj4BNLgLP7Qx%2BIqzAMIfRAAGgwxNDc4NzE2ODg5NzciDEVN6Q705OgjhpFrgCqpA%2F3NJ7qh8HGljDp7LFyoO%2FlNoBPy9Kbb3cDwn9sGZuD4mcdhiknHLmLKUBTgTK%2BrRYlsSNtxN0VTQQRJDOxRkulAJ7UOZJbBbR6RTzKx5VhS4GHWNRjgHHoQMgFsbo4wmvMTINQDegP4t4j9DaBsC%2FCP1eSyrQFTUg5ekn5T1jxTadxYtFhwlDTOZDgcrkxLvnGpFuPFN9X%2FsFkcvKzwK2tpK%2BDK2x11M97ZxEBi%2BEcyHoXFibcO7eIB0WpHX7yTpry0Vfnd%2BSDZn6W9Mnp1cYb7IBDdLvw2NZXtcUXBeWxS1bGCNLnGQdjc3aSFRNJoPlGDR9cfE%2Ff%2BgWhGJbnkrRob9GedrfM9HSGkuAoIzI2U531aQAC%2Bwg7yOwTTZ897kv9vKAmBW02w5%2BzKgYjGK%2FrXfKOWDXSdZL5mDsdEPx4uBeirPIK2NmTh63FIg7bwj%2FYp%2BC7s7BXw1AJkr1hsVbJzCQenCQ45zfoeaCEYvQTrTAsi3IoRA%2FQRGKjdyOxoW0w4DHEZVJp5b%2BeRjDhZbMA0UcU5u1bL%2F7j9UTNTnzqTC%2Bf9vsEKN3w4MI%2F3y80GOt4CWIFtNzkHMpABpgaDt6qVbAgc%2BmiIAR2CFYaSSzKJmmm5s8FO9p5dIuiv4N6CWvrquLdQSC7I9a0T8FIphNyhS6xqZnBu4DcdnXO%2FqjSIJRna29nCkIagrX6p0ZrD3sXELVgKRKKJSGGD30QT33vO0c2t0DVZmP70SYwtHrfmq1ODNolYn%2FMT9ZfUFJ2g0QSbrvcjV%2BOwDbLsFAFNd0QOyU1AWQBv7bYTV%2BFTLtb4MXRIYkhjMX6pT6v7lVYSuGSlWPH6b5R47qL%2FVMU75gj6rqkggzm2mQfLCWwXrT%2BB9PuriAaDMr%2FXl663lOQ4BBVqiF6ncpA1GaFwLXYfFSQTAaFo8j9CcPRLAFLMpYH5cmuvVv99hnhzhw0HkB1tzbueCyv3r3aza6fUtqXB%2FxT1Dv%2FwBfXis%2Ff%2Fa%2FECwDMa1oZDmayZx8%2BeDaiOyq%2F5HpUFJm0is9UTsU6TK%2Bft%2BbY%3D&X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=ASIASE3OW5EISNROBPFU%2F20260312%2Fus-east-1%2Fs3%2Faws4_request&X-Amz-Date=20260312T193317Z&X-Amz-Expires=1200&X-Amz-SignedHeaders=host&X-Amz-Signature=df4ca2e16ec6c55b5127b88a46ac563cf4f94b856a097a79533ab05023badb7e"
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