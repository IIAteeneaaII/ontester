# init_db, get_connection
from __future__ import annotations
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB_PATH = Path(r"C:\ONT\localONT.db")

def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def _schema_path() -> Path:
    # Compatibilidad para desarrollo y .exe
    base = Path(__file__).resolve().parent
    return base / "db/schema.sql"

def init_db() -> None:
    schema_file = _schema_path()
    print("SCHEMA PATH:", schema_file)
    print("SCHEMA EXISTS:", schema_file.exists())
    if schema_file.exists():
        print("SCHEMA SIZE:", schema_file.stat().st_size)
    with get_conn() as conn, schema_file.open(encoding="utf-8") as f:
        sql = f.read()
        conn.executescript(sql)
        # verificar que no esté vacía la tabla de settings y cargar datos iniciales
        registros_iniciales(conn)
        # Registrar version actual
        from src.backend.sua_client.dao import insertar_version
        insertar_version("1.4.3.1")
        conn.commit()

def registros_iniciales(con: sqlite3.Connection):
    # Verificar si la tabla settings está vacía
    from src.backend.sua_client.dao import extraer_registros
    check = extraer_registros("settings")
    if check:
        # significa que hay valores ∴ salimos
        return
    else:
        # Insertar inicial
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        # id || rssi_min || rssi_max || min_percent
        wifi_set = [
            (0, -80, -5, 90)
        ]

        # id || min_tx || max_tx || min_rx || max_rx
        fibra = [
            (0, 1.0, 5.0, -19.0, -13.0)
        ]

        # id || id_wifi || id_fibra || etiqueta
        settings = [
            (0, 0, 0, 2)
        ]

        # id || version || updated_at
        catalog = [
            (0, "1.4.3-", now)
        ]

        # id || descripcion || activo || update_at || id_settings || created_at
        stations = [
            (0, "estacion de prueba", 1, now, 0, now)
        ]

        # id || name || updated || activo || created_at
        users = [
            (0, "ANONIMO", now, 1, now),
            (2,   "DIEGO SANCHEZ VELAZCO", now, 1, now),
            (3,   "ABRAHAM CORREA ROMERO ", now, 1, now),
            (6,   "ALEXÍS GONZALEZ PERAL ", now, 1, now),
            (7,   "ALFONSO OLAF DELABRA MOLINA ", now, 1, now),
            (8,   "FRANYIS CAROLINA MORLES BURGOS", now, 1, now),
            (9,   "VALERIA HERNANDEZ AGUILAR ", now, 1, now),
            (10,  "ALONDRA HERBERTH ALONSO", now, 1, now),
            (11,  "LUIS ENRIQUE BARRIENTOS RUIZ ", now, 1, now),
            (12,  "ARELY AMAIRANI CRUZ RODRIGUEZ ", now, 1, now),
            (13,  "EMILIANO REYES GONZALEZ ", now, 1, now),
            (14,  "ASNERIS YSMAL SOSA REYES", now, 1, now),
            (15,  "DANIEL GALINDO ONTIVEROS", now, 1, now),
            (17,  "BRAYAN MORALES GONZALEZ ", now, 1, now),
            (19,  "CARLO ALEXANDER ESPIN CARREÑO ", now, 1, now),
            (20,  "PEDRO GARCIA ROSAS", now, 1, now),
            (21,  "CESAR DANIEL ESCALONA MARQUEZ ", now, 1, now),
            (22,  "CRISTOFER MALDONADO GONZALEZ ", now, 1, now),
            (23,  "ADRIAN ORDAZ SANCHEZ ", now, 1, now),
            (24,  "DANIEL EMMANUEL ARRIAGA HENANDEZ ", now, 1, now),
            (25,  "BETY CAROLINA ORTIZ CEDEÑO ", now, 1, now),
            (26,  "DARWIN DAVID DIAZ CHACON ", now, 1, now),
            (27,  "UZIAS GARCIA LUCERO ", now, 1, now),
            (28,  "GABRIEL ALFONSO GARCIA MENGUAL ", now, 1, now),
            (29,  "DIEGO BINZHA GUERRERO", now, 1, now),
            (30,  "EDGAR ALFREDO PALMA MONRROY", now, 1, now),
            (31,  "SANDRA MILENA ZARTA CORREDOR", now, 1, now),
            (32,  "JUNIOR JOSE GUTIERREZ DURAN ", now, 1, now),
            (33,  "ROIBER ANGEL TORRES PRIETO ", now, 1, now),
            (34,  "BRANDON ADRIAN PEREZ TERREROS ", now, 1, now),
            (35,  "DANAI BETZABETH PERALTA ACEVEDO", now, 1, now),
            (36,  "ERIKA RAMOS GOMEZ", now, 1, now),
            (37,  "EUSEBIO ANDRES HERNANDEZ PICON ", now, 1, now),
            (38,  "TANIA MICHELLE LUGO HERNANDEZ", now, 1, now),
            (39,  "FERNANDO ALARCON GUTIERREZ", now, 1, now),
            (40,  "IVERSON YAIR VILLARROEL TESILLO ", now, 1, now),
            (41,  "ARMANDO SANCHEZ MARTINEZ", now, 1, now),
            (42,  "ANDREA DEL CARMEN SALVADOR MENDEZ", now, 1, now),
            (43,  "FRAIN SEGUNDO GONZALEZ GONZALEZ", now, 1, now),
            (44,  "RAUL RODAS RODRIGUEZ ", now, 1, now),
            (45,  "GISSELLE MARIET URDANETA RIOS", now, 1, now),
            (46,  "DANIEL ACEVEDO MEJIA", now, 1, now),
            (48,  "SARAHI VELAZQUEZ MORALES ", now, 1, now),
            (49,  "OSCAR ISMAEL JAIME DIAZ ", now, 1, now),
            (50,  "MARIANNY DE LOS ANGELES QUINTERO HERNANDEZ", now, 1, now),
            (51,  "HANNA BETSABE INFANTE GOVEA", now, 1, now),
            (52,  "HENRY DANIEL MAYORA RIVAS ", now, 1, now),
            (53,  "IVAN JARED JIMENEZ GARCIA ", now, 1, now),
            (54,  "ISRAEL ALEJANDRO SOLANO SORIA ", now, 1, now),
            (55,  "JAVIER LOPEZ DRIGGS", now, 1, now),
            (56,  "JAVIER JOSE PEREZ FLORES", now, 1, now),
            (57,  "JESUS EMMANUEL MARTINEZ CRUZ ", now, 1, now),
            (58,  "LEONARDO EDER LOPEZ BALBUENA", now, 1, now),
            (59,  "HUGO ISRAEL PEREZ TORRES ", now, 1, now),
            (60,  "JORGE DELGADO FERNANDEZ", now, 1, now),
            (61,  "LEONARDO ESPINOZA BARRERA", now, 1, now),
            (62,  "JORGE LEANDRO SOSA REYES", now, 1, now),
            (64,  "JOSE ANGEL CRUZ ESPINOZA", now, 1, now),
            (65,  "JOSÈ ANGEL LÒPEZ MARTÌNEZ", now, 1, now),
            (66,  "JOSE ANTONIO DAVILA TAVERA", now, 1, now),
            (68,  "JOSE MIGUEL GONZALEZ GONZALEZ", now, 1, now),
            (70,  "JUAN MANUEL JIMENEZ", now, 1, now),
            (71,  "MARIA ELVA PALAFOX SORIA", now, 1, now),
            (72,  "YARELSY MERCEDES KEY NIÑO", now, 1, now),
            (73,  "SABRINA  DEL VALLE ARAUJO TORRES", now, 1, now),
            (74,  "JAYSON TADEO ROQUE GARCIA ", now, 1, now),
            (75,  "ALICIA MIREYA PIMIENTA GONZALEZ ", now, 1, now),
            (77,  "LUIS FERNANDO CASTILLO SOSA", now, 1, now),
            (78,  "LUIS ANGEL VALERIO ALFARO ", now, 1, now),
            (79,  "JANETH KARINA MENGUAL FERNANDEZ ", now, 1, now),
            (80,  "MARIA DE JESUS GARCIA RAMIREZ ", now, 1, now),
            (81,  "ALAN MIGUEL GOMEZ JUAREZ", now, 1, now),
            (82,  "MARIA FERNANDA FRAGOSO TAVERA", now, 1, now),
            (83,  "MAURICIO XOLALPA PEREZ", now, 1, now),
            (84,  "MIGUEL ANGEL ROJAS MARIN", now, 1, now),
            (85,  "SANTIAGO COCOLETZI BAUTISTA", now, 1, now),
            (86,  "ANNY MIREYA MONCAYO BASTIDAS ", now, 1, now),
            (87,  "MISSAEL CRUZ CARRILLO ", now, 1, now),
            (89,  "AQUILES ZAMBRANO PIMIENTA", now, 1, now),
            (91,  "ALEXANDRA PAULETTE CLETO GARDUÑO  ", now, 1, now),
            (92,  "SHAINA YERALDIN PEREZ TERREROS", now, 1, now),
            (93,  "PACZIRIK ANAHI BUSTOS PEREZ ", now, 1, now),
            (94,  "YAIGLEMAR LUCIA BRACHO MONTIEL ", now, 1, now),
            (95,  "RENI SALAS PACHECO", now, 1, now),
            (96,  "JOSE ENRIQUE MEDINA VALDEZ", now, 1, now),
            (97,  "RICARDO TORTOLERO ARANDA", now, 1, now),
            (98,  "YAILINETH ANDREA BARBOSA ", now, 1, now),
            (99,  "RODOLFO JOSE MACIAS REALES ", now, 1, now),
            (100, "ROMAN RIVERA FLORES", now, 1, now),
            (101, "MARLON BRANDON VEGA LINARES", now, 1, now),
            (102, "EMMANUEL  ALEJANDRO BANDERA RODRIGUEZ ", now, 1, now),
            (103, "KEVIN OCAMPO MORALES", now, 1, now),
            (104, "SANTIAGO TORRES FUENTES", now, 1, now),
            (106, "SCARLE ALEJANDRA ATENCIO GONZALEZ", now, 1, now),
            (107, "SAYURI DANIELA VILLASEÑOR RAMIREZ", now, 1, now),
            (109, "SHOAILIN ISABEL ZUBIRIA CONTRERAS", now, 1, now),
            (111, "URIEL ETZEL GONZALEZ BACA", now, 1, now),
            (112, "VALENTINA CRUZ CARRILLO", now, 1, now),
            (113, "MIGUEL ANGEL CAMACHO MENDEZ", now, 1, now),
            (114, "VICTOR ORLANDO VALENCIA GONZALEZ ", now, 1, now),
            (116, "WENDY JOHANNA PAEZ CHIMA", now, 1, now),
            (117, "MICHAEL NAZARETH FLORES CONOROPO ", now, 1, now),
            (118, "ROSA YANETZY GUTIERREZ PULIDO ", now, 1, now),
            (119, "YICELIZ  MARIA ORTIZ LUGO", now, 1, now),
            (120, "GILMAR ALEJANDRA RIERA BOLIVAR", now, 1, now),
            (121, "PAUL ALEJANDRO URDANETA VILLALOBOS", now, 1, now),
            (122, "DEIMER ALI VILLANUEVA FUENTES ", now, 1, now),
            (123, "HECTOR ALEXIS LOPEZ MARTINEZ ", now, 1, now),
            (124, "MARIA FERNANDA LORA GALLARDO ", now, 1, now),
            (125, "VICTOR ALEJANDRO ESCALONA ESTRADA ", now, 1, now),
            (126, "AMPARO LIZBETH MARTINEZ ROSAS", now, 1, now),
            (127, "NAOMI BETZABETH NAVARRETE ROBLEDO", now, 1, now),
            (128, "DANIEL HUGO HERNANDEZ LANDEROS ", now, 1, now),
            (129, "OSWALDO RAFAEL MARTINEZ GARCIA ", now, 1, now),
            (130, "SONIA DENNIS ACEVEDO REYES", now, 1, now),
            (131, "JOSE ANGEL GONZALEZ PARAMO ", now, 1, now),
            (132, "OMAR ASAEL CASTILLO OSORIO ", now, 1, now),
            (133, "TONALLI GAONA MELGAREJO", now, 1, now),
            (134, "MANUEL PERALTA ORTIZ ", now, 1, now),
            (135, "ALEXANDRA OLMEDO GARDUÑO ", now, 1, now),
            (136, "ERIC GERARDO ESPINOSA VERA", now, 1, now),
            (137, "YERSON ORLANDO NIÑO RODRIGUEZ ", now, 1, now),
            (138, "ISAAC COCOLETZI BAUTISTA", now, 1, now),
            (139, "KARLA ISABEL HERNANDEZ NAVARRO ", now, 1, now),
            (140, "XANDER GABRIEL SEGOVIA APONTE", now, 1, now),
            (141, "MARIA GABRIELA FLORES ROMERO ", now, 1, now),
            (142, "MARIA DANIELA MARCANO RIVAS ", now, 1, now),
            (144, "ROSNEDDIS NOEMI GUEVARA GALLARDO ", now, 1, now),
            (146, "SANTIAGO MONITA TORRES", now, 1, now),
            (147, "JUAN CARLOS PLATAS MORA ", now, 1, now)
        ]

        con.executemany(
            "INSERT OR IGNORE INTO wifi_set (id, rssi_min, rssi_max, min_percent) VALUES (?, ?, ?, ?);",
            wifi_set
        )

        con.executemany(
            "INSERT OR IGNORE INTO fibra_set (id, min_tx, max_tx, min_rx, max_rx) VALUES (?, ?, ?, ?, ?);",
            fibra
        )

        con.executemany(
            "INSERT OR IGNORE INTO settings (id, id_wifi, id_fibra, etiqueta) VALUES (?, ?, ?, ?);",
            settings
        )

        con.executemany(
            "INSERT OR IGNORE INTO catalog_meta (id, version, updated_at) VALUES (?, ?, ?);",
            catalog
        )

        con.executemany(
            "INSERT OR IGNORE INTO stations (id, descripcion, activo, update_at, id_settings, created_at) VALUES (?, ?, ?, ?, ?, ?);",
            stations
        )

        con.executemany(
            "INSERT OR IGNORE INTO users (id, name, updated, activo, created_at) VALUES (?, ?, ?, ?, ?);",
            users
        )