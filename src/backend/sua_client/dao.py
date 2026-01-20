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
        cur.execute(f'SELECT * FROM "{table_name}"')  # comillas dobles para nombres "raros"
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
        cur.execute(f'SELECT * FROM "{table_name}"')  # comillas dobles para nombres "raros"
        rows = cur.fetchall()

        return rows
    
def insertar_operacion(payload, modo):
    # Función para agregar datos del tester a la bd sqlite
    # Por el diseño de la bd cada prueba a la que no se le asigne valor tendrá por defecto SIN PRUEBA
    # Tratamiento de la payload
    
    with get_conn() as con:
        print(f"[DAO] Payload recibida: {payload}")
        # verificar que modo es pasando a upper
        modo = modo.upper()
        if modo == "ETIQUETA":
        elif modo == "TESTEO":
        else: