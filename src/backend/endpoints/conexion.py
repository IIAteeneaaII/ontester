from pathlib import Path
import threading
import time
from datetime import date, datetime
from src.backend.ont_automatico import main_loop

_UNIT_RUNNING = threading.Event()
_UNIT_LOCK = threading.Lock()

# def load_users_txt(path: str | Path) -> dict[str, str]:
#     users = {}
#     path = Path(path)
#     with path.open("r", encoding="utf-8") as f:
#         for line in f:
#             line = line.strip()
#             if not line or line.startswith("#"):
#                 continue
#             k, v = line.split("=", 1)
#             users[k.strip()] = v.strip()
#     return users

def now_local_iso():
    # ISO con zona local (ej: 2026-01-21T15:33:05-06:00)
    return datetime.now().astimezone().isoformat(timespec="seconds")

def load_default_users() -> dict[str, str]:
    # base_utils = Path(__file__).resolve().parents[1]   # -> backend
    from src.backend.sua_client.dao import get_usuarios_activos
    return get_usuarios_activos()

def inicializaruserStation(user_id):
    from src.backend.sua_client.dao import insertar_userStation, extraer_ultimo
    estacion = extraer_ultimo("stations")
    id_station = estacion["id"]
    insertar_userStation(user_id, id_station)

def cargarConfig() -> dict:
    """Devuelve el diccionario de configuración, o {} si no existe / falla."""
    # Desde la bd obtener ultimo id_settings para obtener los id de wifi y fibra, así como el campo de etiqueta
    from src.backend.sua_client.dao import extraer_ultimo, extraer_by_id
    config = extraer_ultimo("settings") # id || id_wifi || id_fibra || etiqueta
    station = extraer_ultimo("stations") # id || desc || activo || update || id_settings || created_at
    config["id"] # Registro a la station    
    id_wifi = config["id_wifi"]   # consulto wifi_set por id
    id_fibra = config["id_fibra"]  # consulto fibra_set por id
    etiqueta = config["etiqueta"]  # guardo config

    wifi_config = extraer_by_id(id_wifi, "wifi_set") # id || rssi_min || rssi_max || min_percent
    fibra_config = extraer_by_id(id_fibra, "fibra_set") # id || min_tx || max_tx || min_rx || max_rx

    # armar json de config
    config_final = {
        "wifi": {
            "rssi24_min":   float(wifi_config["rssi_min"]),
            "rssi5_min":    float(wifi_config["rssi_min"]),
            "rssi24_max":   float(wifi_config["rssi_max"]),
            "rssi5_max":    float(wifi_config["rssi_max"]),
            "min24percent": int(wifi_config["min_percent"]),
            "min5percent":  int(wifi_config["min_percent"])
        },
        "fibra": {
            "mintx": float(fibra_config["min_tx"]),
            "maxtx": float(fibra_config["max_tx"]),
            "minrx": float(fibra_config["min_rx"]),
            "maxrx": float(fibra_config["max_rx"])
        },
        "general": {
            "etiqueta": etiqueta,
            "estacion": station["id"]
        }
    }

    return config_final

def guardarConfig(configRecibida, tipo, user_id):
    # config es el diccionario de info recibida, tipo es de que grupo pertenece
    # Consultar ultima station (la actual)
    from src.backend.sua_client.dao import extraer_ultimo, insertar_settings, insertar_etiqueta, insertar_estacion
    from src.backend.sua_client.dao import insertar_userStation, existe_valor_en_campo, insertar_wifi, insertar_fibra, update_settings
    from src.backend.sua_client.dao import update_fecha_station
    now = now_local_iso()
    estacion = extraer_ultimo("stations")
    # Consultar id_settings
    id_settings = estacion["id_settings"]
    if (id_settings == 0):
        # Configuración inicial ∴ crear nuevo registro
        # insert into settings + valores default (posteriormente se actualizan)
        # obtener nuevo id y cambiar id_settings (variable local)
        id_settings = insertar_settings()

    # Configuración ya iniciada ∴ solo actualizar seccion
    if tipo == "valores":
        # Configuración de fibra y wifi
        # Nuevo registro en fibra Y en wifi + update settings where id = id_settings
        rssi_min = configRecibida.get("rssi24_min")
        rssi_max = configRecibida.get("rssi50_max")
        min_percent = configRecibida.get("busquedas")
        id_wifi = insertar_wifi(rssi_min, rssi_max, min_percent)

        min_tx = configRecibida.get("tx_min")
        max_tx = configRecibida.get("tx_max")
        min_rx = configRecibida.get("rx_min")
        max_rx = configRecibida.get("rx_max")
        id_fibra = insertar_fibra(min_tx, max_tx, min_rx, max_rx)

        update_settings(id_wifi, id_fibra, id_settings)

    elif tipo == "estacion":
        # Configuracion de numero de estacion
        # Crear nuevo registro de stations (id++ no need, "nueva estacion", 1, now, id_settings, now)
        # Nuevo registro en user_station
        # revisar si existe el id, si no existe insert into estacion, si existe solo insert UserStation
        if (existe_valor_en_campo("stations", "id", configRecibida)):
            # Hacer update de fecha
            id_station = configRecibida
            update_fecha_station(id_station, now)
        else:
            id_station = insertar_estacion(configRecibida, "nueva estacion",1, now, id_settings, now)
        insertar_userStation(user_id, id_station)
    else:
        # Configuracion de etiqueta
        # insert into settings where id = id_settings
        insertar_etiqueta(id_settings, configRecibida)


def norm_result(v, *, false_means: str = "FAIL") -> str:
    """
    false_means: "FAIL" o "SIN_PRUEBA"
    """
    ALLOWED = {"PASS", "FAIL", "SIN_PRUEBA"}
    if v is None:
        return "SIN_PRUEBA"

    if isinstance(v, bool):
        if v is True:
            return "PASS"
        return false_means  # False

    if isinstance(v, (int, float)):
        # Si llegan números aquí, no aplican a enum
        return "SIN_PRUEBA"

    if isinstance(v, str):
        s = v.strip().upper().replace(" ", "_")
        # normalizaciones comunes
        if s in ("SINPRUEBA", "SIN-PRUEBA"):
            s = "SIN_PRUEBA"
        if s == "OK":
            s = "PASS"
        if s == "ERROR":
            s = "FAIL"
        return s if s in ALLOWED else "SIN_PRUEBA"

    return "SIN_PRUEBA"

def norm_power(valor, tipo):
    def _to_float_safe(v):
        try:
            return float(v)
        except (TypeError, ValueError):
            return None
    from src.backend.endpoints.conexion import cargarConfig
    config = cargarConfig()
    fibra_cfg = config.get("fibra", {})
    mintx = float(fibra_cfg.get("mintx", 0.0))
    maxtx = float(fibra_cfg.get("maxtx", 1.0))
    minrx = float(fibra_cfg.get("minrx", 0.0))
    maxrx = float(fibra_cfg.get("maxrx", 1.0))
    # TX/RX solo si vienen (para no borrar el valor anterior)
    try:
        float(valor)
    except (TypeError, ValueError):
        return "SIN_PRUEBA"
    if tipo == "tx":
        if(_to_float_safe(valor) >= mintx and _to_float_safe(valor) <= maxtx):
            # Validar si está dentro de los valores
            return "PASS"
        else:
            return "FAIL"
    if tipo == "rx":
        if(_to_float_safe(valor) >= minrx and _to_float_safe(valor) <= maxrx):
            return "PASS"
        else:
            return "FAIL"
    return "SIN_PRUEBA"

def get_daily_report_path() -> Path:
        """
        Devuelve la ruta del CSV del día.
        Ejemplo: C:\\ONT\\Reportes diarios\\reportes_YYYY-MM-DD.csv
        """
        base_dir = Path(r"C:\ONT") 
        reports_dir = base_dir / "Reportes diarios"
        reports_dir.mkdir(parents=True, exist_ok=True)

        today = date.today().isoformat()
        filename = f"reportes_{today}.csv"
        return reports_dir / filename

def _get_report_path_for(d: date) -> Path:
        """
        Devuelve la ruta del CSV para la fecha d.
        Ejem: C:\\ONT\\Reportes diarios\\reportes_YYYY-MM-DD.csv
        """
        base_dir = Path(r"C:\ONT")
        reports_dir = base_dir / "Reportes diarios"
        reports_dir.mkdir(parents=True, exist_ok=True)

        filename = f"reportes_{d.isoformat()}.csv"
        return reports_dir / filename

def iniciar_testerConexion(resetFabrica, usb, fibra, wifi, out_q = None, stop_event = None, auto_test_on_detect = True):
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))

    # Mostrar cambio de modo detectado primero
    emit("log", "Cambio de modo detectado.")
    time.sleep(1) # Pequeña pausa para que sea perceptible

    print("[CONEXION] Fibra recibida: "+str(fibra))
    if any([resetFabrica, usb, fibra, wifi]):
        sftU = True
    else:
        sftU = False
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
            "software_update": sftU, # Esta prueba no se deshabilita, validar si almenos una prueba está encendida
            "usb_port": usb,
            "tx_power": fibra,
            "rx_power": fibra,
            "wifi_24ghz_signal": wifi,
            "wifi_5ghz_signal": wifi
        }
    }
    
    emit("log", "Iniciando pruebas...")
    # print("CONEXION: wifi: "+str(wifi))
    # Mandar a llamar al main loop de ont_automatico
    main_loop(opcionesTest, out_q, stop_event, auto_test_on_detect=auto_test_on_detect)
    # Se hará desde dentro del main_loop
    # from src.backend.mixins.common_mixin import _resultados_finales
    # resultados = _resultados_finales()  # función de resultados finales
    # emit("resultados", resultados)

    # Solo emitir "Pruebas terminadas" si no fue cancelado
    if not (stop_event and stop_event.is_set()):
        emit("log", "Pruebas terminadas.")

def iniciar_pruebaUnitariaConexion(resetFabrica, sftU, usb, fibra, wifi, model, out_q=None, stop_event=None):
    # 1) Definir emisor ANTES de usarlo
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))

    # 2) Check + set del flag SOLO dentro del lock (y salir del lock rápido)        
    with _UNIT_LOCK:
        if _UNIT_RUNNING.is_set():
            emit("log", "Ya hay una prueba unitaria en ejecución. Ignorando este click.")
            return
        _UNIT_RUNNING.set()
    
    # Determinar qué prueba unitaria se está ejecutando para mostrar mensaje claro
    prueba_nombre = "Prueba unitaria"
    if resetFabrica:
        prueba_nombre = "Factory Reset"
    elif sftU:
        prueba_nombre = "Software Update"
    elif usb:
        prueba_nombre = "USB Port"
    elif fibra:
        prueba_nombre = "TX/RX Power (Fibra)"
    elif wifi:
        prueba_nombre = "WiFi 2.4/5 GHz"
    
    try:
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
                "software_update": sftU, 
                "usb_port": usb,
                "tx_power": fibra,
                "rx_power": fibra,
                "wifi_24ghz_signal": wifi,
                "wifi_5ghz_signal": wifi
            }
        }
        
        # Emitir al panel inferior inmediatamente al iniciar
        emit("pruebas", f"Iniciando: {prueba_nombre}...")
        emit("log", f"Iniciando prueba unitaria: {prueba_nombre}")

        # Mandar a llamar una prueba unitaria
        from src.backend.ont_automatico import pruebaUnitariaONT
        pruebaUnitariaONT(opcionesTest=opcionesTest, out_q=out_q, modelo=model, stop_event=stop_event)
        
        # Emitir finalización (solo si no fue cancelado)
        if not (stop_event and stop_event.is_set()):
            emit("pruebas", f"Completado: {prueba_nombre}")
            emit("log", f"Prueba unitaria completada: {prueba_nombre}")
        else:
            emit("pruebas", f"Cancelado: {prueba_nombre}")
            emit("log", f"Prueba unitaria cancelada: {prueba_nombre}")

    finally:
        # 3) SIEMPRE liberar la bandera aunque falle/cancele
        with _UNIT_LOCK:
            _UNIT_RUNNING.clear()
    
    # Solo emitir "Prueba unitaria terminada" si no fue cancelado
    if not (stop_event and stop_event.is_set()):
        emit("log", "Prueba unitaria terminada.")
    
def generaEtiquetaTxt(payload):
    print("[CONEXION] Generando etiqueta")
    info  = payload.get("info", {})

    # Obtener el modelo para variaciones de nombres de redes
    modelo = info.get("modelo", "DESCONOCIDO").upper()

    # Extraer valores para la banda 2.4 GHz
    wifi24_limpio = info.get("wifi24", "")[-4:] if info.get("wifi24") else ""

    # Extraer valores para la banda 5 GHz (ZTE usa un SSID distinto)
    es_fiber = "FIBER" in modelo.upper() or "HG6145" in modelo.upper()

    if not es_fiber:
        wifi5_raw = info.get("wifi5", "")

        # Formato del resto de dispositivos: "Totalplay-XXXX-5G", se debe extrear "XXXX"
        partes = wifi5_raw.split("-") if wifi5_raw else []
        wifi5_limpio = partes[1] if len(partes) >= 2 else ""
    else:
        # Formato de dispositivos Fiber: "Totalplay-5G-XXXX", se debe extraer "XXXX
        wifi5_limpio = info.get("wifi5", "")[-4:] if info.get("wifi5") else ""

    # Filtrar valores para txt
    valores = [
        info.get("sn", ""),
        info.get("mac", "").replace(":", "").upper(), # MAC sin guiones y mayúsculas
        wifi24_limpio, # últimos 4 caracteres
        info.get("passWifi", ""),
        wifi5_limpio,
        info.get("passWifi", "")
    ]

    # Crear línea CSV (sin espacios)
    linea_csv = ",".join(valores)

    # Obtener modelo y limpiar caracteres inválidos para nombre de archivo
    modelo = info.get("modelo", "DESCONOCIDO").upper()
    modelo_seguro = modelo.replace("/", "-").replace("\\", "-").replace(" ", "_")
    
    # Crear directorio etiquetas si no existe
    directorio_etiquetas = Path(r"C:\ONT\etiquetas")
    directorio_etiquetas.mkdir(parents=True, exist_ok=True)

    # Fecha para histórico
    today = date.today().isoformat()
    
    # Ruta del archivo por modelo
    ruta_txt = directorio_etiquetas / f"etiqueta_{modelo_seguro}.txt"
    ruta_historico = directorio_etiquetas / f"historico_etiqueta_{modelo_seguro}_{today}.txt"

    # Formato de cabecera para Bartender
    cabecera = "GPON SN,MAC,SSID,KEY,SSID5g,KEY5g\n"
    
    # 1) Sobrescribir el archivo "etiqueta_[modelo].txt" con SOLO el último registro
    try:
        with ruta_txt.open("w", encoding="utf-8") as f:
            f.write(cabecera)
            f.write(linea_csv + "\n")
    except Exception as e:
        print(f"[TXT] Error escribiendo {ruta_txt}: {e}")

    # 2) Agregar al histórico "historico_etiqueta_[modelo].txt"
    try:
        escribir_cabecera_hist = not ruta_historico.exists() or ruta_historico.stat().st_size == 0
        with ruta_historico.open("a", encoding="utf-8") as f:
            if escribir_cabecera_hist:
                f.write(cabecera)
            f.write(linea_csv + "\n")
    except Exception as e:
        print(f"[TXT] Error escribiendo {ruta_historico}: {e}")

    print(f"[TXT] Etiqueta actual guardada en: {ruta_txt}")
    print(f"[TXT] Registro añadido a histórico: {ruta_historico}")