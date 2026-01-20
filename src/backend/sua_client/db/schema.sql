PRAGMA foreign_keys = ON;

-- ===========================
-- 1) Tabla catalog_meta
-- ===========================
CREATE TABLE IF NOT EXISTS catalog_meta (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    version     INTEGER NOT NULL,
    updated_at  TEXT    NOT NULL
);

-- ===========================
-- 2) Tablas de sets / parámetros
-- ===========================

-- Wifi: umbrales de RSSI y porcentaje mínimo
CREATE TABLE IF NOT EXISTS wifi_set (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    rssi_min     REAL    NOT NULL,      -- ej: -70.0
    rssi_max     REAL    NOT NULL,      -- ej: -30.0
    min_percent  INTEGER NOT NULL,      -- ej: 80 = 80%

    CHECK (rssi_min <= rssi_max),
    CHECK (min_percent BETWEEN 0 AND 100)
);

-- Fibra: rangos de TX/RX en dBm
CREATE TABLE IF NOT EXISTS fibra_set (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    min_tx  REAL    NOT NULL,          -- ej: -30.0
    max_tx  REAL    NOT NULL,
    min_rx  REAL    NOT NULL,
    max_rx  REAL    NOT NULL,

    CHECK (min_tx <= max_tx),
    CHECK (min_rx <= max_rx)
);

-- ===========================
-- 3) Settings (combina wifi_set y fibra_set)
-- ===========================
CREATE TABLE IF NOT EXISTS settings (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_wifi   INTEGER,
    id_fibra  INTEGER,
    etiqueta  INTEGER NOT NULL,     -- sencilla: 1, doble: 2

    FOREIGN KEY (id_wifi)  REFERENCES wifi_set(id),
    FOREIGN KEY (id_fibra) REFERENCES fibra_set(id)
);

-- ===========================
-- 4) Usuarios
-- ===========================
CREATE TABLE IF NOT EXISTS users (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT    NOT NULL,
    updated    TEXT,
    activo     INTEGER NOT NULL DEFAULT 1,  -- 1 = activo, 0 = inactivo
    created_at TEXT    NOT NULL
);

-- ===========================
-- 5) Estaciones
-- ===========================
CREATE TABLE IF NOT EXISTS stations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    descripcion TEXT    NOT NULL,
    activo      INTEGER NOT NULL DEFAULT 1,
    update_at   TEXT,
    id_settings INTEGER,
    created_at  TEXT    NOT NULL,

    FOREIGN KEY (id_settings) REFERENCES settings(id)
);

-- ===========================
-- 6) Relación usuario-estación
-- ===========================
CREATE TABLE IF NOT EXISTS user_station (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    id_user     INTEGER NOT NULL,
    id_station  INTEGER NOT NULL,

    FOREIGN KEY (id_user)    REFERENCES users(id),
    FOREIGN KEY (id_station) REFERENCES stations(id)
);

-- ===========================
-- 7) Operaciones / pruebas realizadas
-- ===========================
-- Enum tipo_operacion: 'ETIQUETA', 'TESTEO', 'RETEST'
-- Enum test_result:    'PASS', 'FAIL', 'SIN_PRUEBA'
CREATE TABLE IF NOT EXISTS operations (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    id_station   INTEGER NOT NULL,
    id_user      INTEGER NOT NULL,
    id_settings  INTEGER,

    tipo         TEXT    NOT NULL,        -- enum tipo_operacion
    fecha_test   TEXT    NOT NULL,        -- 'YYYY-MM-DD HH:MM:SS'
    modelo       TEXT    NOT NULL,
    sn           TEXT    NOT NULL,
    mac          TEXT    NOT NULL,
    sftVer       TEXT    NOT NULL,
    wifi24       TEXT,
    wifi5        TEXT,
    passWifi     TEXT,

    ping         TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    reset        TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    usb          TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    tx           TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    rx           TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    w24          TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    w5           TEXT NOT NULL DEFAULT 'SIN_PRUEBA',
    sftU         TEXT NOT NULL DEFAULT 'SIN_PRUEBA',

    valido       INTEGER NOT NULL DEFAULT 0,

    FOREIGN KEY (id_station)  REFERENCES stations(id),
    FOREIGN KEY (id_user)     REFERENCES users(id),
    FOREIGN KEY (id_settings) REFERENCES settings(id),

    CHECK (tipo IN ('ETIQUETA','TESTEO','RETEST')),
    CHECK (ping  IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (reset IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (usb   IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (tx    IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (rx    IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (w24   IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (w5    IN ('PASS','FAIL','SIN_PRUEBA')),
    CHECK (sftU  IN ('PASS','FAIL','SIN_PRUEBA'))
);