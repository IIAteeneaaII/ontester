from pathlib import Path
import threading

def load_users_txt(path: str | Path) -> dict[str, str]:
    users = {}
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            k, v = line.split("=", 1)
            users[k.strip()] = v.strip()
    return users

def load_default_users() -> dict[str, str]:
    base_utils = Path(__file__).resolve().parents[1]   # -> backend
    txt_path = base_utils / "utils" / "empleados.txt"
    return load_users_txt(txt_path)

def iniciar_testerConexion(resetFabrica, usb, fibra, wifi, out_q = None):
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))
    opcionesTest = {
        "info": {
            "sn": True,
            "mac": True,
            "ssid_24ghz": True,
            "ssid_5ghz": True,
            "software_version": True,
            "wifi_password": True,
            "model": True
        },
        "tests": {
            "ping": True, # Esta prueba no se deshabilita
            "factory_reset": resetFabrica,
            "software_update": True, # Esta prueba no se deshabilita
            "usb_port": usb,
            "tx_power": fibra,
            "rx_power": fibra,
            "wifi_24ghz_signal": wifi,
            "wifi_5ghz_signal": wifi
        }
    }
    # Decir que ya se hizo la conexión
    emit("con", "CONECTADO")
    emit("log", "Iniciando pruebas...")
    # print("CONEXION: wifi: "+str(wifi))
    # Mandar a llamar a la función en ont_automatico
    from src.backend.ont_automatico import main_loop
    main_loop(opcionesTest, out_q) 
    # Se hará desde dentro del main_loop
    # from src.backend.mixins.common_mixin import _resultados_finales
    # resultados = _resultados_finales()  # función de resultados finales
    # emit("resultados", resultados)

    emit("log", "Pruebas terminadas.")