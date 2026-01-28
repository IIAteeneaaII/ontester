# Metodos para la bd
import sqlite3
from src.backend.sua_client.local_db import get_conn


def obtenerTablas():
    # with hace que la conexion a la bd se cierre sola
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name;
        """)
        return [row["name"] for row in cur.fetchall()]

def fetch_table(table_name: str) -> tuple[list[str], list[tuple]]:
    """
    return columns, rows
    columns = ["id", "nombre", "fecha"]
    rows    = [(1, "Diego", "2025-01-01"), ...]
    """
    with get_conn() as con:
        cur = con.cursor()
        # 1) Validar que la tabla exista (y evitar SQL injection por nombre de tabla)
        cur.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name = ?
              AND name NOT LIKE 'sqlite_%'
            LIMIT 1;
        """, (table_name,))
        if cur.fetchone() is None:
            raise ValueError(f"Tabla no existe: {table_name}")

        # 2) Consultar datos
        cur.execute(f'SELECT * FROM "{table_name}";')  # comillas dobles para nombres "raros"
        rows = cur.fetchall()

        # 3) Obtener nombres de columnas
        columns = [desc[0] for desc in cur.description] if cur.description else []

        return columns, rows

def extraer_registros(table_name):
    with get_conn() as con:
        cur = con.cursor()
        # 1) Validar que la tabla exista (y evitar SQL injection por nombre de tabla)
        cur.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name = ?
              AND name NOT LIKE 'sqlite_%'
            LIMIT 1;
        """, (table_name,))
        if cur.fetchone() is None:
            raise ValueError(f"Tabla no existe: {table_name}")

        # 2) Consultar datos
        cur.execute(f'SELECT * FROM "{table_name}";')  # comillas dobles para nombres "raros"
        rows = cur.fetchall()

        return rows

def extraer_ultimo(table_name):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name = ?
              AND name NOT LIKE 'sqlite_%'
            LIMIT 1;
        """, (table_name,))
        if cur.fetchone() is None:
            raise ValueError(f"Tabla no existe: {table_name}")
        cur.execute(f'SELECT * FROM "{table_name}" ORDER BY id DESC LIMIT 1;')
        rows = cur.fetchone()
        return rows

def extraer_by_id(id, table_name):
    with get_conn() as con:
        cur = con.cursor()
        cur.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type='table' AND name = ?
              AND name NOT LIKE 'sqlite_%'
            LIMIT 1;
        """, (table_name,))
        if cur.fetchone() is None:
            raise ValueError(f"Tabla no existe: {table_name}")
        cur.execute(f'SELECT * FROM "{table_name}" WHERE id = ? LIMIT 1;', (id,))
        row = cur.fetchone()
        return row

def insertar_operacion(payload, modo, id_user):
    # Función para agregar datos del tester a la bd sqlite
    # Por el diseño de la bd cada prueba a la que no se le asigne valor tendrá por defecto SIN PRUEBA
    # Tratamiento de la payload
    info  = payload.get("info", {})
    tests = payload.get("tests", {})
    modo = modo.upper()
    # Comprobar que no viene de una unitaria
    if (modo not in  {"ETIQUETA", "TESTEO", "RETEST"}):
        return -1
    id_station = 0
    id_settings = 0
    false_means = "FAIL"
    from src.backend.endpoints.conexion import norm_result, norm_power
    params = {
        "id_station":  id_station,  # Estos parametros (station, settings) deben leerse desde la bd (config)
        "id_user":     id_user,     # Se pasa desde la llamada
        "id_settings": id_settings, # Se lee desde bd
        "tipo":        modo,

        "fecha_test": info.get("fecha_test"),
        "modelo":    info.get("modelo"),
        "sn":        info.get("sn"),
        "mac":       info.get("mac"),
        "sftVer":    info.get("sftVer"),
        "wifi24":    info.get("wifi24"),
        "wifi5":     info.get("wifi5"),
        "passWifi":  info.get("passWifi"),

        # si no viene, forzamos SIN_PRUEBA
        "ping": norm_result(tests.get("ping"), false_means=false_means),
        "reset": norm_result(tests.get("reset"), false_means=false_means),
        "usb": norm_result(tests.get("usb"), false_means=false_means),
        "tx": norm_power(tests.get("tx"), "tx"),
        "rx": norm_power(tests.get("rx"), "rx"),
        "w24": norm_result(tests.get("w24"), false_means=false_means),
        "w5":  norm_result(tests.get("w5"), false_means=false_means),
        "sftU": norm_result(tests.get("sftU"), false_means=false_means),

        # sqlite: bool -> int
        "valido": int(bool(payload.get("valido"))),
    }

    sql = """
    INSERT INTO operations (
        id_station, id_user, id_settings, tipo,
        fecha_test, modelo, sn, mac, sftVer, wifi24, wifi5, passWifi,
        ping, reset, usb, tx, rx, w24, w5, sftU,
        valido
    ) VALUES (
        :id_station, :id_user, :id_settings, :tipo,
        :fecha_test, :modelo, :sn, :mac, :sftVer, :wifi24, :wifi5, :passWifi,
        :ping, :reset, :usb, :tx, :rx, :w24, :w5, :sftU,
        :valido
    );
    """
    with get_conn() as con:
        cur = con.execute(sql, params)
        con.commit()
        return cur.lastrowid

def insertar_settings():
    # Función pensada para añadir una row en settings con valores default
    with get_conn() as con:
        cur = con.execute(
            "INSERT INTO settings (id_wifi, id_fibra, etiqueta) VALUES (?, ?, ?);",
            (0, 0, 2)
        )
        con.commit()
        return cur.lastrowid

def insertar_etiqueta(id_settings, etiqueta):
    # Alter nadamas etiqueta into settings
    with get_conn() as con:
        con.execute("UPDATE settings SET etiqueta = ? WHERE id = ?;", 
                   (etiqueta, id_settings)                  
        )
        con.commit()

def insertar_estacion(id_s, desc, activo, update, id_settings, created_at):
    with get_conn() as con:
        con.execute(
            "INSERT INTO stations (id, descripcion, activo, update_at, id_settings, created_at) VALUES (?, ?, ?, ?, ?, ?);",
            (id_s, desc, activo, update, id_settings, created_at)
        )
        con.commit()
        return id_s

def insertar_userStation(id_user, id_station):
    with get_conn() as con:
        con.execute(
            "INSERT INTO user_station (id_user, id_station) VALUES (?, ?);",
            (id_user, id_station)
        )
        con.commit()

def insertar_wifi(rssi_min, rssi_max, min_percent) -> int:
    with get_conn() as con:
        cur = con.execute(
            "INSERT INTO wifi_set (rssi_min, rssi_max, min_percent) VALUES (?, ?, ?);",
            (rssi_min, rssi_max, min_percent)
        )
        con.commit()
        return cur.lastrowid

def update_fecha_station(id_station, fecha):
    with get_conn() as con:
        con.execute(
            "UPDATE stations SET update_at = ? WHERE id = ?;", 
            (fecha, id_station)   
        )
        con.commit

def insertar_fibra(min_tx, max_tx, min_rx, max_rx):
    with get_conn() as con:
        cur = con.execute(
            "INSERT INTO fibra_set (min_tx, max_tx, min_rx, max_rx) VALUES (?, ?, ?, ?);",
            (min_tx, max_tx, min_rx, max_rx)
        )
        con.commit()
        return cur.lastrowid
    
def update_settings(id_wifi, id_fibra, id_settings):
    with get_conn() as con:
        con.execute("UPDATE settings SET id_wifi = ?, id_fibra = ? WHERE id = ?;", 
                   (id_wifi, id_fibra, id_settings)                  
        )
        con.commit()

def existe_valor_en_campo(table_name: str, campo: str, valor) -> bool:
    with get_conn() as con:
        # 1) validar que la tabla exista
        row = con.execute("""
            SELECT 1
            FROM sqlite_master
            WHERE type='table'
              AND name = ?
              AND name NOT LIKE 'sqlite_%'
            LIMIT 1;
        """, (table_name,)).fetchone()

        if row is None:
            raise ValueError(f"Tabla no existe: {table_name}")

        # 2) validar que la columna exista en esa tabla
        cols = con.execute(f'PRAGMA table_info("{table_name}");').fetchall()
        colnames = {c["name"] for c in cols}
        if campo not in colnames:
            raise ValueError(f"Campo no existe: {campo} en tabla {table_name}")

        # 3) consulta EXISTS (el valor sí va parametrizado)
        r = con.execute(
            f'SELECT EXISTS(SELECT 1 FROM "{table_name}" WHERE "{campo}" = ? LIMIT 1) AS existe;',
            (valor,)
        ).fetchone()

        return bool(r["existe"]) if r else False

def clear_user_station() -> None:
    with get_conn() as con:
        con.execute("DELETE FROM user_station;")
        con.commit()

def get_usuarios_activos() -> dict[int, str]:
    with get_conn() as con:
        cur = con.execute("SELECT id, name FROM users WHERE activo = 1;")
        return {row["id"]: row["name"] for row in cur.fetchall()}
    
def get_baseDiaria_view(date):
    with get_conn() as con:
        cur = con.execute(
            "SELECT sn, mac, wifi24, wifi5, passWifi, valido, tipo, modelo, fecha_test FROM operations;"
        )