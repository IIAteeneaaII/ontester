from __future__ import annotations

import time
import secrets
from pathlib import Path
from typing import Optional, Dict, Any
from src.backend.endpoints.resources import get_pc_id_from_mac_suffix

import requests

from .settings import (
    SUA_BASE_URL,
    STATION_ID,
    CERTIFICATE_PATH,
    PRIVATE_KEY_PATH,
    ROOT_CA_PATH,
)

from src.backend.sua_client.dao import (
    get_station_key_activa,
    get_enrollment_code_pendiente,
    upsert_enrollment_pendiente,
    activar_station_key, get_station_activa,obtener_enrollment_code_activa
)

TIMEOUT = 15


def _now() -> float:
    return time.time()


def _certs_exist() -> bool:
    return Path(CERTIFICATE_PATH).exists() and Path(PRIVATE_KEY_PATH).exists() and Path(ROOT_CA_PATH).exists()


def _download_file(url: str, dest: Path):
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=TIMEOUT) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)


class SuaClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self._jwt: Optional[str] = None
        self._jwt_exp_ts: float = 0.0

    # ------------- ENROLL -------------
    def enroll(self, station_id: str, enrollment_code: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/auth/enroll"
        r = requests.post(url, json={"station_id": station_id, "enrollment_code": enrollment_code}, timeout=TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"enroll {r.status_code}: {r.text}")
        return r.json()

    def claim_key(self, station_id: str, enrollment_code: str) -> Dict[str, Any]:
        url = f"{self.base_url}/api/auth/claim-key"
        r = requests.post(url, json={"station_id": station_id, "enrollment_code": enrollment_code}, timeout=TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"claim-key {r.status_code}: {r.text}")
        station_key = r.json()["station_key"]
        # reemplaza enrollment_code por station_key y activo=2
        activar_station_key(station_key)
        print("[SUA] station_key recibida. SQLite actualizado (descripcion=station_key, activo=2).")
        return r.json()

    # ------------- TOKEN -------------
    def _fetch_station_token(self, station_id: str, station_key: str) -> str:
        url = f"{self.base_url}/api/auth/station-token"
        r = requests.post(
            url,
            headers={"X-Station-Id": station_id, "X-Station-Key": station_key},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            raise RuntimeError(f"station-token {r.status_code}: {r.text}")

        data = r.json()
        token = data["access_token"]
        expires_in = float(data.get("expires_in", 600))
        self._jwt = token
        self._jwt_exp_ts = _now() + expires_in - 10
        return token

    def get_station_token(self, station_id: str, station_key: str) -> str:
        if not self._jwt or _now() >= self._jwt_exp_ts:
            return self._fetch_station_token(station_id, station_key)
        return self._jwt

    # ------------- CERTS -------------
    def get_presigned_urls(self) -> Dict[str, Any]:
        jwt_token = self.get_station_token(STATION_ID, get_station_key_activa())
        url = f"{self.base_url}/api/certificates/presigned-urls"
        r = requests.get(url, headers={"Authorization": f"Bearer {jwt_token}"}, timeout=TIMEOUT)
        if r.status_code != 200:
            raise RuntimeError(f"presigned {r.status_code}: {r.text}")
        urls = r.json()["urls"]

        _download_file(urls["certificate"], Path(CERTIFICATE_PATH))
        _download_file(urls["private_key"], Path(PRIVATE_KEY_PATH))
        _download_file(urls["root_ca"], Path(ROOT_CA_PATH))

        print("[SUA] certificados descargados")
        return True

def verificar_estado_estacion() -> bool:
    station = get_station_activa()
    if station and station == 2:
        print("[SUA] Estación activa y con station_key")
        return True
    else: 
        print("[SUA] Estación en proceso de enroll (activo=1). Esperando station_key...")
        return False
    

def ensure_certs_from_sua(poll_interval_sec: int = 10, max_wait_sec: int = 30) -> bool:
    """
    Flujo final con SQLite local:
    - stations.activo=2 => descripcion=station_key
    - stations.activo=1 => descripcion=enrollment_code
    """
    if _certs_exist():
        return True

    client = SuaClient(SUA_BASE_URL)

    # 1) ¿ya tenemos station_key?
    station_key = get_station_key_activa()
    if station_key:
        print("[SUA] station_key encontrada en SQLite (activo=2)")
    else:
        # 2) enrollment_code pendiente o generar
        enrollment_code = get_enrollment_code_pendiente()
        if (enrollment_code == None or "estacion" in enrollment_code):
            enrollment_code = secrets.token_urlsafe(32)
            upsert_enrollment_pendiente(enrollment_code)
            print("[SUA] enrollment_code generado y guardado en SQLite (activo=1)")
        else:
            print("[SUA] enrollment_code pendiente encontrada en SQLite (activo=1)")

        # 3) ENROLL (idempotente)
        try:
            client.enroll(STATION_ID, enrollment_code)
            print(f"[SUA] enroll enviado station_id={STATION_ID}")
        except Exception as e:
            print(f"[SUA] ERROR enroll: {e}")
            return False
    return True

def get_url_certificados() -> bool:
    client = SuaClient(SUA_BASE_URL)
    try:
        client.get_presigned_urls()
        return True
    except Exception as e:
        print(f"[SUA] ERROR get_presigned_urls: {e}")
        return False



def reclamar_llave_sua() -> bool:
    """
    Intenta reclamar la station_key usando el enrollment_code activo.
    Retorna True si tuvo éxito, False en caso de error.
    """
    try:
        # 1. Crear cliente SUA
        client = SuaClient(SUA_BASE_URL)
        
        # 2. Obtener enrollment_code activo (activo = 2)
        enrollment = obtener_enrollment_code_activa()
        if not enrollment:
            print("No hay enrollment_code activo (activo=2)")
            return False
        
        # 3. Llamar a claim_key (ya actualiza la BD internamente)
        resultado = client.claim_key(STATION_ID, enrollment)
        
        
        return True
    except Exception as e:
        print(f"Error en reclamar_llave_sua: {e}")
        return False