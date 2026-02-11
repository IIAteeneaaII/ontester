#!/usr/bin/env python3
"""
ONT Automated Test Suite
Pruebas automatizadas basadas en protocolo de testing
Fecha: 26/11/2025
"""

import argparse
import json
import os
import sys
import socket
import subprocess
import platform
import re
import threading
import time
import requests
import csv
from datetime import datetime
from datetime import date
from pathlib import Path
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime
from pathlib import Path
MAC_REGEX = re.compile(r"([0-9A-Fa-f]{2}(?:(?::|-)?[0-9A-Fa-f]{2}){5})")
# Selenium para login automático
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    from selenium.common.exceptions import StaleElementReferenceException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[WARNING] Selenium no disponible. Instala con: pip install selenium webdriver-manager")

# IMPORTAR LOS MODULOS MIXIN
from src.backend.mixins.zte_mixin import ZTEMixin # importar la clase
from src.backend.mixins.huawei_mixin import HuaweiMixin
from src.backend.mixins.fiber_mixin import FiberMixin
from src.backend.mixins.grandstream_mixin import GrandStreamMixin
from src.backend.mixins.common_mixin import CommonMixin
# IMPORTAR EL CERTIFICADO
from src.backend.certificado.certificado import generarCertificado

# ==========================
# COORDINACIÓN UNITARIA vs MAIN LOOP
# ==========================
UNIT_TEST_ACTIVE = threading.Event() # Indica “hay una unitaria corriendo”
UNIT_TEST_JUST_FINISHED = threading.Event()  # Indica "unitaria recién terminó, skip fase2"
CREATE_NO_WINDOW = 0x08000000
_SUPPRESS_LOCK = threading.Lock()
_SUPPRESS_UNTIL = {}     # ip -> deadline (time.monotonic)
_SUPPRESS_REASON = {}    # ip -> str

def suppress_mode(ip: str, seconds: int, reason: str = "") -> None:
    """Evita que main_loop vuelva a ejecutar el modo (etiqueta/test/retest) por X segundos."""
    deadline = time.monotonic() + max(0, int(seconds))
    with _SUPPRESS_LOCK:
        prev = _SUPPRESS_UNTIL.get(ip, 0.0)
        _SUPPRESS_UNTIL[ip] = max(prev, deadline)
        if reason:
            _SUPPRESS_REASON[ip] = reason

def suppressed_remaining(ip: str) -> int:
    """Segundos restantes de supresión para ese IP."""
    with _SUPPRESS_LOCK:
        dl = _SUPPRESS_UNTIL.get(ip, 0.0)
        rem = dl - time.monotonic()
        if rem <= 0:
            _SUPPRESS_UNTIL.pop(ip, None)
            _SUPPRESS_REASON.pop(ip, None)
            return 0
        return int(rem)

def is_suppressed(ip: str) -> bool:
    return suppressed_remaining(ip) > 0

def suppress_reason(ip: str) -> str:
    with _SUPPRESS_LOCK:
        return _SUPPRESS_REASON.get(ip, "")

class ONTAutomatedTester(ZTEMixin, HuaweiMixin, FiberMixin, GrandStreamMixin, CommonMixin):
    def __init__(self, host: str, model: str = None):
        self.host = host
        self.model = model  # Puede ser None, se detectará automáticamente
        self.base_url = f"http://{host}"
        self.ajax_url = f"http://{host}/cgi-bin/ajax"
        self.type_url = f"http://{host}/?_type=menuData&_tag="
        self.session = requests.Session()
        self.authenticated = False
        self.session_id = None
        self.driver = None
        self.selenium_cookies = None
        # q
        self.out_q = None
        # Hacer run_all_tests cancelable
        self._stop_event = None
        # Ajustes para el fiber
        self.minWifi24Signal = -80  # Valor mínimo de señal WiFi 2.4GHz
        self.minWifi5Signal = -80  # Valor mínimo de señal WiFi 2.4GHz
        self.maxWifi24Signal = -5  # Valor máximo de señal WiFi 2.4GHz
        self.maxWifi5Signal = -5  # Valor máximo de señal WiFi 5GHz
        # Ajustes para ZTE y Huawei
        self.minWifi24Percent = 60  # Porcentaje mínimo de señal WiFi 2.4GHz
        self.minWifi5Percent = 60   # Porcentaje mínimo de señal WiFi 5GHz

        # Ajustes para la fibra
        self.minTX = -30
        self.minRX = -30
        self.maxTX = 0
        self.maxRX = 0
        self.test_results = {
            "metadata": {
                "host": host,
                "model": model,
                "timestamp": datetime.now().isoformat(),
                "serial_number": None
            },
            "tests": {}
        }

        self.opcionesTest = {
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
                "ping": True,
                "factory_reset": True,
                "software_update": True,
                "usb_port": True,
                "tx_power": True,
                "rx_power": True,
                "wifi_24ghz_signal": True,
                "wifi_5ghz_signal": True
            }
        }
        
        # Deshabilitar warnings SSL
        requests.packages.urllib3.disable_warnings()
        
        # Mapeo de ModelName a códigos de modelo
        # IMPORTANTE: Orden de prioridad - más específicos primero
        # Las claves más largas y específicas deben ir primero para evitar false positives
        self.model_mapping = {
            # MOD005: HUAWEI EchoLife HG8145V5 SMALL (MÁS ESPECÍFICO - va primero)
            "HUAWEI ECHOLIFE HG8145V5 SMALL": "MOD005",
            "ECHOLIFE HG8145V5 SMALL": "MOD005",
            "HG8145V5 SMALL": "MOD005",
            
            # MOD004: HUAWEI EchoLife HG8145V5 (menos específico que SMALL)
            "HUAWEI ECHOLIFE HG8145V5": "MOD004",
            "ECHOLIFE HG8145V5": "MOD004",
            "HUAWEI HG8145V5": "MOD004",
            "HG8145V5": "MOD004",
            
            # MOD003: HUAWEI HG8145X6-10
            # NOTA: El Huawei HG8145X6-10 reporta "HG6145F1" por firmware (bug del dispositivo)
            # La etiqueta física dice "Huawei OptiXstar HG8145X6-10"
            # En la empresa se conoce coloquialmente como "X6"
            "HUAWEI HG8145X6-10": "MOD003",
            "HG8145X6-10": "MOD003",
            "HUAWEI HG8145X6": "MOD007", # Nuevo modelo, MOD007
            "HG8145X6": "MOD007",
            
            # MOD002: ZTE ZXHN F670L
            "ZTE ZXHN F670L": "MOD002",
            "ZXHN F670L": "MOD002",
            "ZTE F670L": "MOD002",
            "F670L": "MOD002",
            
            # MOD001: FIBERHOME HG6145F
            "FIBERHOME HG6145F": "MOD001",
            "HG6145F": "MOD001",
            "HG6145F1": "MOD008",
            
            # MOD006: GRANDSTREAM HT818
            "GRANDSTREAM HT818": "MOD006",
            "GS-HT818": "MOD006",
            "HT818": "MOD006",
        }
    
    # Configuración de umbrales de señal WiFi Fiberhome
    def _configWifiSignalThresholds(self, min24: int, min5: int):
        """Configura los umbrales mínimos de señal WiFi para los tests"""
        self.minWifi24Signal = min24
        self.minWifi5Signal = min5

    def _configWifiSignalThresholdsMax(self, max24: int, max5: int):
        """Configura los umbrales maximos de señal WiFi para los tests"""
        self.maxWifi24Signal = max24
        self.maxWifi5Signal = max5
    
    def _configFibraThresholds(self, min24: int, min5: int):
        """Configura los umbrales mínimos de señal de fibra para los tests"""
        self.minTX = min24
        self.minRX = min5

    def _configFibraThresholdsMax(self, max24: int, max5: int):
        """Configura los umbrales maximos de señal de fibra para los tests"""
        self.maxTX = max24
        self.maxRX = max5

    def _getMinFibraTx(self):
        return self.minTX
    def _getMaxFibraTx(self):
        return self.maxTX
    def _getMinFibraRx(self):
        return self.minRX
    def _getMaxFibraRx(self):
        return self.maxRX
    # Configuración de umbrales máximos de señal WiFi ZTE/Huawei
    def _configWifiSignalThresholdsPercent(self, min24: int, min5: int):
        """Configura los umbrales mínimos de señal WiFi para los tests"""
        self.minWifi24Percent = min24
        self.minWifi5Percent = min5

    def _getMinWifi24SignalPercent(self) -> int:
        """Retorna el umbral mínimo de señal WiFi en porcentaje"""
        return self.minWifi24Percent
    def _getMinWifi5SignalPercent(self) -> int:
        """Retorna el umbral mínimo de señal WiFi 5GHz en porcentaje"""
        return self.minWifi5Percent 
    def _getMinWifi24Signal(self) -> int:
        """Retorna el umbral mínimo de señal WiFi 2.4GHz"""
        return self.minWifi24Signal
    
    def _getMinWifi5Signal(self) -> int:
        """Retorna el umbral mínimo de señal WiFi 5GHz"""
        return self.minWifi5Signal
    
    def _getMaxWifi24Signal(self) -> int:
        """Retorna el umbral máximo de señal WiFi 2.4GHz"""
        return self.maxWifi24Signal
    
    def _getMaxWifi5Signal(self) -> int:
        """Retorna el umbral máximo de señal WiFi 5GHz"""
        return self.maxWifi5Signal

    def _check_network_configuration(self):
        """
        Verifica que el adaptador Ethernet tenga configuradas las IPs necesarias
        para acceder a todos los modelos de ONT.
        
        Returns:
            tuple: (bool, list) - (configuración_ok, IPs_faltantes)
        """
        import socket
        import subprocess
        
        # IPs necesarias para acceder a todos los modelos
        required_networks = {
            "192.168.100": "Huawei/Fiberhome",
            "192.168.1": "ZTE"
        }
        
        try:
            # Obtener todas las IPs del adaptador usando ipconfig
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=subprocess.CREATE_NO_WINDOW,
                errors='ignore'
            )
            
            output = result.stdout
            
            # Buscar las IPs configuradas
            configured_networks = set()
            for line in output.split('\n'):
                if 'IPv4' in line or 'Dirección IPv4' in line:
                    # Extraer la IP
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip().split('(')[0].strip()
                        # Obtener la red (primeros 3 octetos)
                        network = '.'.join(ip.split('.')[:3])
                        if network in required_networks:
                            configured_networks.add(network)
            
            # Verificar si faltan redes
            missing_networks = []
            for network, description in required_networks.items():
                if network not in configured_networks:
                    missing_networks.append((network, description))
            
            return (len(missing_networks) == 0, missing_networks)
            
        except Exception as e:
            print(f"[WARNING] No se pudo verificar configuración de red: {e}")
            return (True, [])  # Asumir que está ok si no podemos verificar
     
    def _scan_for_device(self, timeout=10):
        """
        Escanea IPs comunes de ONTs para encontrar un dispositivo activo.
        
        Returns:
            tuple: (ip, device_type) si encuentra dispositivo, (None, None) si no
        """
        # IPs comunes basadas en los dispositivos conocidos
        common_ips = [
            "192.168.100.1",  # Fiberhome, Huawei
            "192.168.1.1",    # ZTE
        ]
        
        print("[DISCOVERY] Escaneando IPs comunes...")
        
        for ip in common_ips:
            try:
                print(f"[DISCOVERY] Probando {ip}...", end=" ")
                response = self.session.get(
                    f"http://{ip}",
                    timeout=timeout,
                    verify=False,
                    allow_redirects=True
                )
                
                # Si responde con cualquier código HTTP válido, hay un dispositivo
                if response.status_code < 500:
                    print(f"✓ Responde")
                    # Actualizar el host y detectar tipo
                    self.host = ip
                    self.base_url = f"http://{ip}"
                    self.ajax_url = f"http://{ip}/cgi-bin/ajax"
                    self.type_url = f"http://{ip}/?_type=menuData&_tag="
                    
                    device_type = self._detect_device_type()
                    print(f"[DISCOVERY] ✓ Dispositivo {device_type} encontrado en {ip}")
                    return (ip, device_type)
                    
            except requests.exceptions.Timeout:
                print("✗ Timeout")
                continue
            except requests.exceptions.ConnectionError:
                print("✗ No hay conexión")
                continue
            except Exception as e:
                print(f"✗ Error: {e}")
                continue
        
        print("[DISCOVERY] ✗ No se encontró ningún dispositivo en las IPs comunes")
        return (None, None)
    
    def login(self) -> bool:
        """Realiza login en la ONT via AJAX"""
        print("[AUTH] Intentando autenticacion...")
        
        # Detectar tipo de dispositivo primero
        device_type = self._detect_device_type()
        
        if device_type == "GRANDSTREAM":
            return self._login_grandstream()
        elif device_type == "FIBERHOME" or self.model == "MOD001" or self.model == "MOD008":
            return self._login_fiberhome()  # Fiberhome usa Selenium
        elif device_type == "ZTE" or self.model == "MOD002":
            return self._login_zte(False) # False para indicar que aun no se ha reseteado
        elif device_type == "HUAWEI" or self.model in ["MOD003", "MOD004", "MOD005", "MOD007"]:
            return self._login_huawei()
        else:
            return self._login_ont_standard()
    
    def _detect_device_type(self) -> str:
        """Detecta el tipo de dispositivo (ONT o ATA Grandstream)"""
        try:
            # Intentar acceder a la página principal
            response = self.session.get(
                self.base_url,
                timeout=3,
                verify=False,
                allow_redirects=True
            )
            
            # Preparar versiones del HTML para búsqueda
            raw_html = response.text 
            html_lower = raw_html.lower()
            server_header = response.headers.get('Server', '').lower()
            
            # Normalización básica para detección general (eliminar espacios y saltos)
            html_normalized = html_lower.replace(' ', '').replace('\n', '').replace('\t', '')
            
            # --- 1. DETECCIÓN GRANDSTREAM ---
            if 'grandstream' in html_lower or 'grandstream' in server_header or 'ht818' in html_lower:
                return "GRANDSTREAM"
            
            # --- 2. DETECCIÓN FIBERHOME ---
            if any(k in html_lower for k in ['fiberhome', 'hg6145f', 'user_name', 'loginpp', 'fh-text-security']):
                print("[AUTH] Dispositivo Fiberhome detectado automáticamente")
                if 'hg6145f1' in html_lower:
                    self.model = "MOD008"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                elif not self.model:
                    self.model = "MOD001"
                print(f"[AUTH] Modelo asignado: {self.model}")
                return "FIBERHOME"
            
            # --- 3. DETECCIÓN HUAWEI ---
            if any(k in html_normalized for k in ['huawei', 'hg8145', 'txt_username', 'txt_password']):
                print("[AUTH] Dispositivo Huawei detectado automáticamente")
                
                product_name = ""
                
                # Paso A: Intentar leer <title> (Generalmente limpio y fiable)
                title_match = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE)
                if title_match:
                    product_name = title_match.group(1).upper().strip()
                
                # Paso B: Si el título no contiene el modelo, buscar en JS var ProductName
                # Solo aquí aplicamos la limpieza del guion codificado (\x2d) típica del X6-10
                if "HG8145" not in product_name:
                    js_match = re.search(r"var\s+ProductName\s*=\s*['\"]([^'\"]+)['\"]", raw_html, re.IGNORECASE)
                    if js_match:
                        raw_js = js_match.group(1).upper()
                        # Aquí corregimos el bug del X6-10 (HG8145X6\x2d10 -> HG8145X6-10)
                        product_name = raw_js.replace('\\X2D', '-').replace('\\x2d', '-').strip()

                # Paso C: Asignación de Modelo basada en el nombre encontrado
                if product_name:
                    if 'HG8145X6-10' in product_name:
                        self.model = "MOD003" # Huawei X6-10 (El del bug del guion)
                    elif 'HG8145X6' in product_name:
                        self.model = "MOD007" # Huawei X6 (Nuevo/Normal)
                    elif 'HG8145V5' in product_name:
                        if 'SMALL' in product_name:
                            self.model = "MOD005" # V5 Small
                        else:
                            self.model = "MOD004" # V5 Normal
                    else:
                        # Si es un Huawei desconocido, usamos V5 como base segura
                        self.model = "MOD004"
                else:
                    # Si detectamos Huawei pero no pudimos leer el nombre
                    self.model = "MOD004"

                print(f"[AUTH] Modelo Huawei asignado: {self.model} ({product_name if product_name else 'Indeterminado'})")
                return "HUAWEI"
            
            # --- 4. DETECCIÓN ZTE ---
            if any(k in html_lower for k in ['zte', 'zxhn', 'f670l', 'frm_username', 'frm_password']):
                print("[AUTH] Dispositivo ZTE detectado automáticamente")
                if not self.model:
                    self.model = "MOD002"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "ZTE"
            
            return "ONT"
            
        except Exception as e:
            print(f"[ERROR] Fallo en la detección de dispositivo {e}")
            return "ONT"
                
    def _detect_model(self, model_name: str) -> str:
        """Detecta el codigo de modelo basado en el ModelName"""
        # Normalizar el nombre del modelo
        model_name_clean = model_name.strip()
        model_name_upper = model_name_clean.upper()
        
        # Paso 1: Buscar coincidencia exacta (case-insensitive)
        for key, value in self.model_mapping.items():
            if key.upper() == model_name_upper:
                return value
        
        # Paso 2: Buscar coincidencias más largas primero (más específicas)
        # Ordenar las claves por longitud descendente para priorizar matches más específicos
        sorted_keys = sorted(self.model_mapping.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            key_upper = key.upper()
            # Verificar si el nombre del modelo contiene la clave completa
            if key_upper in model_name_upper:
                return self.model_mapping[key]
        
        # Si no se encuentra, usar el ModelName como codigo
        print(f"[WARN] Modelo desconocido: {model_name}, usando como codigo")
        return f"UNKNOWN_{model_name}"
    
    def _get_model_display_name(self, model_code: str, reported_name: str = None) -> str:
        """Retorna el nombre de display correcto según el código de modelo"""
        display_names = {
            "MOD003": "HG8145X6-10",  # Nombre comercial usado en la empresa (coloquialmente "X6")
            "MOD001": "HG6145F",
            "MOD008": "HG6145F1",
            "MOD002": "F670L",
            "MOD004": "HG8145V5",
            "MOD005": "HG8145V5 SMALL",
            "MOD006": "HT818",
            "MOD007": "HG8145X6",
        }
        
        return display_names.get(model_code, reported_name or model_code)
         
    def setConfig(self):
        from src.backend.endpoints.conexion import cargarConfig
        config = cargarConfig()

        # --- WIFI ---
        wifi_cfg = config.get("wifi", {})

        if wifi_cfg:
            # Umbrales de señal (porcentaje/RSSI) – adapta los defaults a lo que tú quieras
            min24 = float(wifi_cfg.get("rssi24_min", -80))
            min5  = float(wifi_cfg.get("rssi5_min", -80))
            max24 = float(wifi_cfg.get("rssi24_max", -5))
            max5  = float(wifi_cfg.get("rssi5_max", -5))

            # Usar tus setters ya definidos
            self._configWifiSignalThresholds(min24=min24, min5=min5)
            self._configWifiSignalThresholdsMax(max24=max24, max5=max5)

            # porcentaje:
            minWifiPercent24 = int(wifi_cfg.get("min24percent", 60))
            minWifiPercent5  = int(wifi_cfg.get("min5percent", 60))

            self._configWifiSignalThresholdsPercent(minWifiPercent24, minWifiPercent5)

        # --- FIBRA ---
        fibra_cfg = config.get("fibra", {})

        if fibra_cfg:
            mintx = float(fibra_cfg.get("mintx", 0.0))
            maxtx = float(fibra_cfg.get("maxtx", 1.0))
            minrx = float(fibra_cfg.get("minrx", 0.0))
            maxrx = float(fibra_cfg.get("maxrx", 1.0))

            # Ojo con tu implementación: aquí asumo que el primero es TX y el segundo RX
            self._configFibraThresholds(min24=mintx, min5=minrx)
            self._configFibraThresholdsMax(max24=maxtx, max5=maxrx)

    def run_all_tests(self) -> Dict[str, Any]:
        # Mandar a llamar a las configuraciones
        self.setConfig()
        def _cancelled():
            return bool(getattr(self, "stop_event", None)) and self.stop_event.is_set()

        """Ejecuta todos los tests automatizados"""
        print("\n" + "="*60)
        print("ONT/ATA AUTOMATED TEST SUITE")
        print(f"Host: {self.host}")
        if self.model:
            print(f"Modelo especificado: {self.model}")
        print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*60 + "\n")
        
        login_ok = self.login()

        if not login_ok:
            print("[!] Error: No se pudo autenticar")
            if(self.model == "MOD001"):
                return self.test_results
        # Determinar qué tests ejecutar según el tipo de dispositivo
        device_type = self.test_results['metadata'].get('device_type', 'ONT')
        
        # IMPORTANTE Las opciones modificadas aqui solo entran en vigor para el FIBERHOME
        # Tests comunes a todos los dispositivos
        common_tests = [
            #self.test_pwd_pass,
            #self.test_factory_reset,
            #self.test_ping_connectivity,
            # self.test_http_connectivity,
            # self.test_port_scan,
            # self.test_dns_resolution,
            self.test_software_version,
        ]
        
        optTest = self.opcionesTest
        tests_opts = optTest.get("tests", {})
        if tests_opts.get("factory_reset", True):
            common_tests.append(self.test_factory_reset)

        # Tests específicos de ONT
        ont_tests = [
            #self.test_usb_port,
            #self.test_tx_power,
            #self.test_rx_power,
            #self.test_wifi_24ghz,
            #self.test_wifi_5ghz
            #self.test_sft_update
        ]
        
        if tests_opts.get("usb_port", True):
            ont_tests.append(self.test_usb_port)
        if tests_opts.get("tx_power", True) and tests_opts.get("rx_power", True):
            ont_tests.append(self.test_tx_power)
            ont_tests.append(self.test_rx_power)
        if tests_opts.get("wifi_24ghz_signal", True) and tests_opts.get("wifi_5ghz_signal", True):
            ont_tests.append(self.test_wifi_24ghz)
            ont_tests.append(self.test_wifi_5ghz)

        # Tests específicos de ATA (Grandstream HT818)
        ata_tests = [
            self.test_voip_lines,
            self.test_sip_registration,
            self.test_network_settings
        ]
        
        # De momento solo para fiber, se puede agregar condiciones con el operador or "||"
        if(self.model == "MOD001" or self.model == "MOD008"):
            # Ejecutar tests comunes
            def emit(kind, payload):
                if self.out_q:
                    self.out_q.put((kind, payload))
            print(f"\n[*] Ejecutando tests comunes ({len(common_tests)} tests)...")
            for test_func in common_tests:
                if _cancelled():
                    if self.out_q:
                        self.out_q.put(("log", "CANCELADO POR CAMBIO DE MODO"))
                    return self.test_results

                test_name = test_func.__name__.replace('test_', '').replace('_', ' ').title()
                emit("pruebas", f"Ejecutando: {test_name}")
                result = test_func()
                self.test_results["tests"][result["name"]] = result

                emit("test_individual", {"name": result.get("name",""), "status": result.get("status","FAIL")})
            
            if tests_opts.get("software_update", True):
                if self.driver:
                    self.driver.quit()
                    self.driver = None
                emit("pruebas", "Ejecutando: Actualizacion De Software")
                self.test_sft_update() # Se tiene que ejecutar después de lo demás ya que requiere otro login
            # print(json.dumps(self.test_results, indent=2, ensure_ascii=False)) 
        # Ejecutar tests específicos según el tipo
        if device_type == "ATA":
            print(f"\n[*] Dispositivo ATA detectado - Ejecutando tests VoIP ({len(ata_tests)} tests)...")
            for test_func in ata_tests:
                if _cancelled():
                    if self.out_q:
                        self.out_q.put(("log", "CANCELADO POR CAMBIO DE MODO"))
                    return self.test_results

                result = test_func()
                self.test_results["tests"][result["name"]] = result
        else:
            print(f"\n[*] Dispositivo ONT detectado - Ejecutando tests específicos ({len(ont_tests)} tests)...")
            for test_func in ont_tests:
                if _cancelled():
                    if self.out_q:
                        self.out_q.put(("log", "CANCELADO POR CAMBIO DE MODO"))
                    return self.test_results

                def emit(kind, payload):
                    if self.out_q:
                        self.out_q.put((kind, payload))
                test_name = test_func.__name__.replace('test_', '').replace('_', ' ').title()
                emit("pruebas", f"Ejecutando: {test_name}")
                result = test_func()
                self.test_results["tests"][result["name"]] = result

                emit("test_individual", {"name": result.get("name",""), "status": result.get("status","FAIL")})
        return self.test_results

    def _generarCertificado(self):
        # Provisionalmente aqui se va a generar el certificado
        generar = True # bandera para seleccionar si se hace o no el certificado (se fuerza porque no se pasa la fibra)
        # Posteriormente se puede validar con la ultima variable del JSON que contiene si es valido o no
        # Obtener el dict con la info
        res = self._resultados_finales()
        if(generar):
            ruta = generarCertificado(res)
            print(f"\n[REPORT] Certificado generado en: {ruta}")
    
    def ensure_reports_dir(self) -> Path:
        """
        Asegura que exista C:\\ONT\\Reportes diarios y devuelve la ruta.
        Si la carpeta ya existe, no pasa nada.
        """
        base_dir = Path(r"C:\ONT")
        reports_dir = base_dir / "Reportes diarios"
        reports_dir.mkdir(parents=True, exist_ok=True)
        return reports_dir


    def get_daily_report_path(self,d: date | None = None) -> Path:
        """
        Devuelve la ruta del CSV del día.
        Ej: C:\\ONT\\Reportes diarios\\reportes_2025-12-19.csv
        """
        if d is None:
            d = date.today()
        reports_dir = self.ensure_reports_dir()
        filename = f"reportes_{d.isoformat()}.csv"
        return reports_dir / filename

    def getTipoPrueba(self):
        # traer el diccionario de opciones
        opc = self.opcionesTest
        tests_opts = opc.get("tests", {})

        activos = [nombre for nombre, activo in tests_opts.items() if activo]
        # 1) Todos activos -> Retest
        if len(activos) == len(tests_opts) and len(tests_opts) > 0:
            return "Retest"
        # 2) Solo ping activo -> Etiqueta
        if len(activos) == 1 and "ping" in activos:
            return "Etiqueta"
        # 3) Cualquier otra combinación -> Inicial
        return "Inicial"

    # Ya no necesito esta función c:
    def saveBDiaria(self, resultados):
        print("[BASE] Llegando a base diaria")
        # Traer los resultados de la prueba
        # res = resultados
        # # Versión del software
        # version_ont = "BETA"

        # # Encabezados
        # HEADERS = [
        #     "ID",
        #     "SN",
        #     "MAC",
        #     "SSID_24",
        #     "SSID_5",
        #     "PASSWORD",
        #     "MODELO",
        #     "STATUS",
        #     "VERSION_INICIAL",
        #     "VERSION_FINAL",
        #     "TIPO_PRUEBA",
        #     "FECHA",
        #     "VERSION_ONT_TESTER",
        # ]

        # ruta_csv = self.get_daily_report_path()
        # archivo_nuevo = not ruta_csv.exists()

        # # 4) Calcular el siguiente ID
        # if archivo_nuevo:
        #     next_id = 1
        # else:
        #     with ruta_csv.open(newline="", encoding="utf-8") as f:
        #         reader = csv.reader(f)
        #         # saltar encabezado si existe
        #         next(reader, None)
        #         last_id = 0
        #         for row in reader:
        #             if row and row[0].isdigit():
        #                 last_id = int(row[0])
        #         next_id = last_id + 1

        # #Creación de 
        # info  = res.get("info", {})
        # tests = res.get("tests", {})
        # valido = res.get("valido", False)
        # tipo_prueba = self.getTipoPrueba()
        # registro = [
        #     next_id,              # ID
        #     info.get("sn", ""),            # SN
        #     info.get("mac", ""),           # MAC
        #     info.get("wifi24", ""),        # SSID_24
        #     info.get("wifi5", ""),         # SSID_5
        #     info.get("passWifi", ""),      # PASSWORD
        #     info.get("modelo", ""),        # MODELO
        #     "OK" if valido else "FAIL",        # STATUS
        #     "---",   # VERSION_INICIAL
        #     info.get("sftVer", ""),     # VERSION_FINAL
        #     tipo_prueba,   # TIPO_PRUEBA
        #     date.today().strftime("%d-%m-%Y"),     # FECHA
        #     version_ont,          # VERSION_ONT_TESTER
        # ]

        # # Guardar del archivo
        # ruta_csv = self.get_daily_report_path()
        # archivo_nuevo = not ruta_csv.exists()

        # with ruta_csv.open(mode="a", newline="", encoding="utf-8") as f:
        #     writer = csv.writer(f)

        #     # Si es nuevo, escribimos los encabezados primero
        #     if archivo_nuevo:
        #         writer.writerow(HEADERS)

        #     writer.writerow(registro)

def main():
    parser = argparse.ArgumentParser(description="ONT Automated Test Suite")
    parser.add_argument("--host", help="IP de la ONT (opcional, se detecta automáticamente si se omite)")
    parser.add_argument("--model", help="Modelo de la ONT (opcional, se detecta automaticamente)")
    parser.add_argument("--output", help="Directorio de salida (opcional)")
    parser.add_argument("--mode", 
                       choices=['test', 'retest', 'label'], 
                       default='test',
                       help="Modo de operacion: test (todos), retest (solo fallidos), label (generar etiqueta)")
    
    args = parser.parse_args()
    
   # Auto-discovery si no se proporciona --host
    if not args.host:
        print("\n============================================================")
        print("ONT/ATA AUTOMATED TEST SUITE - AUTO-DISCOVERY MODE")
        print("============================================================\n")
        
        # Crear tester temporal para verificar red y escanear
        temp_tester = ONTAutomatedTester(host="0.0.0.0", model=None)
        
        # Verificar configuración de red
        print("[NETWORK] Verificando configuración de red...")
        network_ok, missing_networks = temp_tester._check_network_configuration()
        
        if not network_ok:
            print(f"[WARNING] Faltan {len(missing_networks)} red(es) configurada(s)")
            print("[INFO] Continuando con escaneo en las redes disponibles...\n")
        else:
            print("[OK] Configuración de red correcta - Todas las redes accesibles\n")
        
        ip, device_type = temp_tester._scan_for_device()
        
        if not ip:
            print("\n[ERROR] No se encontró ningún dispositivo ONT.")
            print("[ERROR] Verifica:")
            print("  1. El dispositivo esté encendido y conectado")
            print("  2. La configuración de red (ver instrucciones arriba)")
            print("\nTambién puedes especificar manualmente:")
            print("  python ont_automated_tester.py --host 192.168.100.1")
            return
        
        # Usar el IP y modelo detectados
        args.host = ip
        args.model = temp_tester.model  # El modelo ya fue asignado en _detect_device_type
        print(f"\n[OK] Dispositivo {device_type} detectado: {args.host} (Modelo: {args.model})\n")
    
    # Mostrar info de inicio
    print("=" * 60)
    print("ONT/ATA AUTOMATED TEST SUITE")
    print(f"Host: {args.host}")
    if args.model:
        print(f"Modelo especificado: {args.model}")
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print()
    
    if args.mode == 'label':
        # Modo label: generar etiqueta de identificación
        generate_label(args.host, args.model)
    elif args.mode == 'retest':
        # Modo retest: solo tests fallidos
        run_retest_mode(args.host, args.model, args.output)
    # else:
    # Modo test: todos los tests

    # No importa las pruebas a realizar, la extracción siempre se debe obtener
    """
    INFO: 
    - SN
    - MAC
    - SSID WiFi 2.4GHz
    - SSID WiFi 5GHz
    - Versión Software
    - WiFi Password
    - Modelo
    PRUEBAS:
    - Ping
    - Factory Reset
    - Software Update
    - USB Port
    - TX Power
    - RX Power
    - WiFi 2.4GHz Signal
    - WiFi 5GHz Signal
    """
    tester = ONTAutomatedTester(args.host, args.model)
    opc = tester.opcionesTest
    opc["tests"]["factory_reset"] =     True # Deshabilitar factory reset automatico
    opc["tests"]["software_update"] =   True 
    opc["tests"]["tx_power"] =          False 
    opc["tests"]["rx_power"] =          False 
    opc["tests"]["wifi_24ghz_signal"] = False 
    opc["tests"]["wifi_5ghz_signal"] =  False 
    opc["tests"]["usb_port"] =          False
    tester.run_all_tests() # No hace falta pasar parametros, como pertenece a la misma instancia
    
    # Mostrar reporte en consola
    if(tester.model == "MOD001"):
        print("\n" + tester.generate_report())
        tester.save_results(args.output) # Guardar resultados

    # Para generar certificado verificar si todos los tests se están ejecutando
    todo_tests_on = all(tester.opcionesTest["tests"].values())
    if(todo_tests_on):
        tester._generarCertificado()
    

def monitor_device_connection(ip: str, interval: int = 1, max_failures: int = 1, stop_event = None):
    """
    Monitorea continuamente la conexión con un dispositivo mediante ping.
    Retorna cuando se pierda la conexión o se reciba señal de stop.
    
    Args:
        ip: IP del dispositivo a monitorear
        interval: Segundos entre cada ping
        max_failures: Número de pings fallidos consecutivos antes de considerar desconexión
        stop_event: threading.Event para señalar cancelación
    """
    print(f"\n{'='*60}")
    print(f"MONITOREANDO CONEXION CON {ip}")
    print(f"Intervalo: {interval}s | Max fallos consecutivos: {max_failures}")
    print(f"Presiona Ctrl+C para detener")
    print(f"{'='*60}\n")
    
    consecutive_failures = 0
    ping_count = 0
    
    try:
        while True:
            # Verificar si se solicitó cancelación
            if stop_event and stop_event.is_set():
                print(f"\n[*] Monitoreo cancelado por cambio de modo")
                return True
            
            ping_count += 1
            
            # Ejecutar ping según el sistema operativo
            param = '-n' if platform.system().lower() == 'windows' else '-c'
            command = ['ping', param, '1', '-w', '1000', ip]
            
            try:
                result = subprocess.run(
                    command,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    timeout=2
                )
                
                if result.returncode == 0:
                    # Ping exitoso
                    consecutive_failures = 0
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    # Limpiar línea completa antes de escribir
                    print(f"\r[{timestamp}] ✓ Ping #{ping_count} - Conexión activa con {ip}                    ", end='', flush=True)
                else:
                    # Ping fallido
                    consecutive_failures += 1
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] ✗ Ping #{ping_count} - Fallo {consecutive_failures}/{max_failures}      ")
                    
                    if consecutive_failures >= max_failures:
                        print(f"\n[!] CONEXIÓN PERDIDA después de {consecutive_failures} intentos fallidos")
                        print(f"[*] Total de pings realizados: {ping_count}")
                        return False  # Conexión perdida
                        
            except subprocess.TimeoutExpired:
                consecutive_failures += 1
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] ⏱ Ping #{ping_count} - Timeout {consecutive_failures}/{max_failures}      ")
                
                if consecutive_failures >= max_failures:
                    print(f"\n[!] CONEXIÓN PERDIDA por timeout")
                    print(f"[*] Total de pings realizados: {ping_count}")
                    return False
            
            time.sleep(interval)
            
    except KeyboardInterrupt:
        print(f"\n\n[*] Monitoreo detenido por el usuario")
        print(f"[*] Total de pings realizados: {ping_count}")
        return True  # Usuario interrumpió manualmente

def generate_label(host: str, model: str = None):
    """RF 031: Genera etiqueta imprimible con información del ONT"""
    print("\n" + "="*60)
    print("GENERANDO ETIQUETA DE IDENTIFICACION")
    print("="*60 + "\n")
    
    tester = ONTAutomatedTester(host, model)
    if not tester.login():
        print("[!] Error: No se pudo conectar al ONT")
        return
    
    # Obtener información adicional
    device_info = tester._ajax_get('get_device_name')
    operator_info = tester._ajax_get('get_operator')
    
    serial_logical = operator_info.get('SerialNumber', 'N/A')
    
    # Intentar calcular SN Físico
    serial_physical = tester._calculate_physical_sn(serial_logical)
    if serial_physical:
        sn_physical_line = f"{serial_physical:40}"
        note = "SN Fisico/PON calculado automaticamente"
    else:
        sn_physical_line = "_________________________________________"
        note = "Completar SN Fisico/PON desde la etiqueta fisica del dispositivo"
    
    # Generar etiqueta
    label = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                  ETIQUETA DE IDENTIFICACION ONT              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║                                                              ║
    ║  MODELO:          {device_info.get('ModelName', 'N/A'):40} ║
    ║  CODIGO:          {tester.model:40} ║
    ║  SN LOGICO:       {serial_logical:40} ║
    ║  SN FISICO/PON:   {sn_physical_line} ║
    ║  OPERADOR:        {operator_info.get('operator_name', 'N/A'):40} ║
    ║  IP:              {host:40} ║
    ║  FECHA:           {datetime.now().strftime('%d/%m/%Y %H:%M'):40} ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  CONECTIVIDAD:                                               ║
    ║    • HTTP:        ✓ DISPONIBLE                               ║
    ║    • Telnet:      Puerto 23 abierto                          ║
    ║    • Web UI:      http://{host:30}         ║
    ║    • Usuario:     root                                       ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  NOTA: {note:<57} ║
    ║        (16 caracteres hexadecimales)                         ║
    ║                                                              ║
    ║  NOTAS ADICIONALES:                                          ║
    ║  ___________________________________________________________  ║
    ║  ___________________________________________________________  ║
    ║  ___________________________________________________________  ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    
    print(label)
    
    # Guardar etiqueta en archivo organizado por fecha
    timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
    date_folder = datetime.now().strftime("%d_%m_%y")
    
    # Agregar sufijo _emp para dispositivos empresariales
    device_type = tester.test_results['metadata'].get('device_type', 'ONT')
    if device_type in ['ATA', 'ROUTER', 'SWITCH']:
        date_folder = f"{date_folder}_emp"
    
    label_dir = Path("reports/labels") / date_folder
    label_dir.mkdir(parents=True, exist_ok=True)
    
    serial = operator_info.get('SerialNumber', tester.test_results['metadata'].get('serial_number', 'UNKNOWN'))
    label_file = label_dir / f"{timestamp}_{tester.model}_{serial}_label.txt"
    
    with open(label_file, 'w', encoding='utf-8') as f:
        f.write(label)
    
    print(f"\n[+] Etiqueta guardada en: {label_file}")

def run_retest_mode(host: str, model: str = None, output: str = None):
    """RF 031: Ejecuta solo los tests que fallaron anteriormente"""
    print("\n" + "="*60)
    print("MODO RETEST - Solo tests fallidos")
    print("="*60 + "\n")
    
    # Buscar el último reporte en subdirectorios por fecha
    reports_base_dir = Path("reports/automated_tests")
    if not reports_base_dir.exists():
        print("[!] No se encontraron reportes previos")
        print("[*] Ejecutando suite completo...")
        tester = ONTAutomatedTester(host, model)
        tester.run_all_tests()
        print("\n" + tester.generate_report())
        tester.save_results(output)
        return
    
    # Buscar todos los archivos JSON en subdirectorios
    json_files = []
    for date_dir in sorted(reports_base_dir.iterdir(), reverse=True):
        if date_dir.is_dir():
            json_files.extend(date_dir.glob("*_automated_results.json"))
    
    json_files = sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not json_files:
        print("[!] No se encontraron reportes previos")
        print("[*] Ejecutando suite completo...")
        tester = ONTAutomatedTester(host, model)
        tester.run_all_tests()
        print("\n" + tester.generate_report())
        tester.save_results(output)
        return
    
    last_report = json_files[0]
    print(f"[*] Cargando último reporte: {last_report.parent.name}/{last_report.name}")
    
    with open(last_report, 'r') as f:
        previous_results = json.load(f)
    
    # Identificar tests fallidos
    failed_tests = []
    for test_name, test_data in previous_results.get("tests", {}).items():
        if test_data.get("status") == "FAIL":
            failed_tests.append(test_name)
    
    if not failed_tests:
        print("[✓] Todos los tests pasaron en la ejecución anterior")
        print("[*] Nada que re-testear")
        return
    
    print(f"\n[*] Tests fallidos en ejecución anterior: {len(failed_tests)}")
    for test in failed_tests:
        print(f"    - {test}")
    print()
    
    # Crear tester y ejecutar solo tests fallidos
    tester = ONTAutomatedTester(host, model)
    
    if not tester.login():
        print("[!] Error: No se pudo autenticar")
        return
    
    # Mapeo de nombres de tests a métodos
    test_methods = {
        "PWD_PASS": tester.test_pwd_pass,
        "FACTORY_RESET_PASS": tester.test_factory_reset,
        "PING_CONNECTIVITY": tester.test_ping_connectivity,
        "HTTP_CONNECTIVITY": tester.test_http_connectivity,
        "PORT_SCAN": tester.test_port_scan,
        "DNS_RESOLUTION": tester.test_dns_resolution,
        "USB_PORT": tester.test_usb_port,
        "SOFTWARE_PASS": tester.test_software_version,
        "TX_POWER": tester.test_tx_power,
        "RX_POWER": tester.test_rx_power,
        "WIFI_24GHZ": tester.test_wifi_24ghz,
        "WIFI_5GHZ": tester.test_wifi_5ghz,
        # Tests específicos de ATA
        "VOIP_LINES": tester.test_voip_lines,
        "SIP_REGISTRATION": tester.test_sip_registration,
        "NETWORK_SETTINGS": tester.test_network_settings
    }
    
    # Ejecutar solo tests fallidos
    for test_name in failed_tests:
        if test_name in test_methods:
            result = test_methods[test_name]()
            tester.test_results["tests"][result["name"]] = result
    
    # Mostrar reporte
    print("\n" + tester.generate_report())
    
    # Guardar resultados con prefijo "retest" en subdirectorios por fecha
    timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
    date_folder = datetime.now().strftime("%d_%m_%y")
    
    if output:
        output_dir = Path(output) / date_folder
    else:
        output_dir = Path("reports/automated_tests") / date_folder
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / f"{timestamp}_{tester.model}_retest_results.json"
    txt_file = output_dir / f"{timestamp}_{tester.model}_retest_report.txt"
    
    with open(json_file, 'w') as f:
        json.dump(tester.test_results, f, indent=2)
    
    with open(txt_file, 'w') as f:
        f.write(tester.generate_report())
    
    print(f"\n[+] Resultados guardados en:")
    print(f"    - JSON: {json_file}")
    print(f"    - TXT: {txt_file}")

def pruebaUnitariaONT(opcionesTest, out_q=None, modelo=None, stop_event=None):
    """Ejecuta una "prueba unitaria" de ONT usando las opciones recibidas.

    Nota: esta función está pensada para ser llamada desde el endpoint
    "conexion.iniciar_pruebaUnitariaConexion" y NO forma parte de una
    instancia de ONTAutomatedTester, por eso no recibe "self".
    
    Args:
        opcionesTest: Dict con opciones de pruebas
        out_q: Queue para emitir eventos a la UI
        modelo: Modelo del dispositivo
        stop_event: threading.Event para cancelar la ejecución
    """
    
    # Verificar si ya se solicitó cancelación antes de empezar
    if stop_event and stop_event.is_set():
        return

    '''# Obtener la IP del dispositivo según modelo
    if modelo == "F670L":
        ip = "192.168.1.1"
    else:
        ip = "192.168.100.1"'''
    
    # Modelo desde UI
    modelo_ui = (modelo or "").strip()

    # Mapeo UI -> código interno (para que _resultados_finales funcione)
    MODEL_UI_TO_CODE = {
        "HG6145F": "MOD001",
        "HG6145F1": "MOD008",
        "F670L": "MOD002",
        "HG8145X6-10": "MOD003",
        "HG8145X6": "MOD007",
        "HG8145V5": "MOD004",
        "HG8145V5 SMALL": "MOD005",
    }
    model_code = MODEL_UI_TO_CODE.get(modelo_ui, None)

    # IP por modelo
    ip = "192.168.1.1" if modelo_ui == "F670L" else "192.168.100.1"

    # Instancia de ONTAutomatedTester para esta ejecución puntual
    temp_tester = ONTAutomatedTester(host=ip, model=model_code)

    # Conectar queue y opciones
    temp_tester.out_q = out_q
    temp_tester.opcionesTest = opcionesTest
    temp_tester.stop_event = stop_event

    # Configurar emits hacia la cola de la UI, si existe
    def emit(kind, payload):
        if out_q:
            temp_tester.out_q = out_q
            temp_tester.out_q.put((kind, payload))

    # (Opcional) dejar trazabilidad del modelo que venía de UI
    try:
        temp_tester.test_results["metadata"]["model_ui"] = modelo
        temp_tester.test_results["metadata"]["host"] = ip
    except Exception:
        pass

    '''# Pre-detección para estandarizar "logSuper" también en unitarias (opcional)
    try:
        device_type = temp_tester._detect_device_type()  # Se asigna self.model = MOD00X
        display = temp_tester._get_model_display_name(temp_tester.model, reported_name=modelo) # Se obtiene el nombre real del modelo
        emit("logSuper", display)  # Para que UI muestre el modelo correcto
        emit("log", f"Prueba unitaria en {ip} | Tipo: {device_type} | ModelCode: {temp_tester.model}")
    except Exception as e:
        emit("log", f"[WARN] No se pudo pre-detectar modelo: {e}")'''

    '''En cuanto inicie la unitaria, el modo queda “bloqueado” y aunque el ONT se reinicie, el loop del modo no vuelve a ejecutar etiqueta/test/retest.'''
    tests = (opcionesTest or {}).get("tests", {})
    disruptiva = bool(tests.get("factory_reset") or tests.get("software_update"))

    # Si la unitaria reinicia, NO queremos que el main_loop retome el modo al detectar el reboot.
    # Factory reset / software update suelen tardar varios minutos.
    if disruptiva:
        suppress_mode(ip, seconds=15 * 60, reason="unit_test(factory/software)")

    UNIT_TEST_ACTIVE.set()
    try:
        temp_tester.run_all_tests()
    finally:
        UNIT_TEST_ACTIVE.clear()

    # Ejecutar la prueba unitaria (usa las opciones ya cargadas)
    #temp_tester.run_all_tests()

    # Cancelación post-run
    if stop_event and stop_event.is_set():
        return
    
    # Emit por test usando lo que ya se almacenó en test_results
    try:
        for _, result in temp_tester.test_results.get("tests", {}).items():
            # result típicamente: {"name": "...", "status": "PASS/FAIL", ...}
            emit("test_individual", {"name": result.get("name", ""), "status": result.get("status", "FAIL")})
    except Exception as e:
        emit("log", f"[WARN] No se pudo emitir test_individual: {e}")

    # Emit final "resultados" igual que el main_loop
    try:
        final = temp_tester._resultados_finales()
        emit("resultados", final)
    except Exception as e:
        emit("log", f"[WARN] No se pudo emitir resultados finales: {e}")

    # Solo avisamos al loop principal para que SALTE FASE 2
    # si la prueba unitaria fue disruptiva (reset de fábrica o actualización).
    if disruptiva:
        UNIT_TEST_JUST_FINISHED.set()
    else:
        # Nos aseguramos de no dejar un flag viejo encendido
        UNIT_TEST_JUST_FINISHED.clear()
    emit("resume_monitor", None)

# Función helper para ping único
def _ping_once(ip: str, timeout_ms: int = 1) -> bool:
    """Ping 1 vez"""
    cmd = ["ping", "-n", "1", "-w", str(int(timeout_ms)), ip]
    try:
        r = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
            timeout=max(2, int(timeout_ms / 1000) + 1)
        )
        return r.returncode == 0
    except Exception:
        return False

# Helper para esperar reconexión sin reiniciar ciclo
def wait_for_reconnect(ip: str, grace_s: int = 240, interval_s: float = 2.0, stop_event=None) -> bool:
    """
    Espera a que el ONT vuelva a responder ping (típico reboot).
    True = volvió dentro de la ventana; False = no volvió.
    """
    deadline = time.time() + int(grace_s)
    while time.time() < deadline:
        if stop_event and stop_event.is_set():
            return False
        if _ping_once(ip, timeout_ms=1000):
            return True
        time.sleep(interval_s)
    return False

def main_loop(opciones, out_q = None, stop_event = None, auto_test_on_detect = True, start_in_monitor=False):
    """
    Ciclo principal recursivo:
    1. Escanea red y encuentra dispositivo
    2. Ejecuta pruebas completas
    3. Monitorea conexión con ping
    4. Vuelve a escanear cuando se pierde conexión
    
    Args:
        opciones: Dict con opciones de pruebas
        out_q: Queue para emitir eventos a la UI
        stop_event: threading.Event para cancelar el ciclo
    """
    print("\n" + "="*80)
    print("ONT AUTOMATICO")
    print("="*80 + "\n")
    
    cycle_count = 0
    last_tested_ip = None
    auto_test_default = auto_test_on_detect  # para restaurar al desconectar
    fase2_executed = start_in_monitor # Indica si ya se ejecutó fase2 en esta sesión (se resetea al desconectar)

    def is_etiqueta_mode(opc: dict) -> bool:
        tests = (opc or {}).get("tests", {})
        # Etiqueta = todo OFF excepto ping (ping puede estar True)
        keys = (
            "factory_reset", "software_update", "usb_port",
            "tx_power", "rx_power",
            "wifi_24ghz_signal", "wifi_5ghz_signal",
        )
        return all(not tests.get(k, False) for k in keys)
    
    try:
        while True:
            # Verificar si se solicitó cancelación
            if stop_event and stop_event.is_set():
                print("\n[*] Ciclo cancelado por cambio de modo")
                break
            
            cycle_count += 1
            print(f"\n{'#'*80}")
            print(f"CICLO #{cycle_count}")
            print(f"{'#'*80}\n")
            
            # --- FASE 1: ESCANEO ---
            print("[FASE 1/3] ESCANEO DE RED")
            print("-" * 60)
            
            temp_tester = ONTAutomatedTester(host="0.0.0.0", model=None)

            # Definir la q como globar para poder acceder a ella desde todos lados
            def emit(kind, payload):
                if out_q:
                    temp_tester.out_q = out_q
                    temp_tester.out_q.put((kind, payload))
            
            # Verificar configuración de red
            network_ok = temp_tester._check_network_configuration()
            
            if not network_ok:
                print(f"[WARNING] No se detectaron las redes del ONT.")
                print("[INFO] Continuando con escaneo en las redes disponibles...\n")
            else:
                print("[OK] Configuración de red correcta\n")
            
            ip, device_type = temp_tester._scan_for_device()
            
            if not ip:
                print("\n[!] No se encontró ningún dispositivo")
                print("[*] Reintentando en 1 segundo...\n")
                time.sleep(1)
                continue
            
            detected_model = temp_tester.model
            
            print(f"\n[OK] {device_type} detectado: {ip} (Modelo: {detected_model})")
            # Decir que ya se hizo la conexión
            emit("con", "Dispositivo Conectado")
            # Marcar PING como PASS automáticamente (conexión confirmada por _scan_for_device)
            emit("test_individual", {"name": "ping", "status": "PASS"})
            last_tested_ip = ip

            # Mostrar modelo en UI
            nombre = temp_tester._get_model_display_name(detected_model)
            emit("logSuper", nombre if detected_model else "Por confirmar...")
            
            # --- FASE 2: PRUEBAS / ETIQUETA / MONITOREO ---
            # BLOQUEO: si una prueba unitaria está corriendo o ya se ejecutó fase2 en esta sesión
            if UNIT_TEST_ACTIVE.is_set():
                emit("log", "[SKIP FASE2] Prueba unitaria en ejecución. Paso directo a MONITOREO.")
            elif UNIT_TEST_JUST_FINISHED.is_set():
                UNIT_TEST_JUST_FINISHED.clear()  # Consumir el flag
                emit("log", "Dispositivo detectado. En monitoreo tras unitaria...")
            elif fase2_executed:
                emit("log", "Dispositivo detectado. En monitoreo: esperando acción del usuario...")
                print("[DEBUG FASE2] Branch = FASE2_ALREADY_EXECUTED")
            elif auto_test_on_detect:
                # Modo Testeo/Retesteo: ejecutar pruebas completas
                print(f"\n[FASE 2/3] EJECUCIÓN DE PRUEBAS")
                print("-" * 60)

                emit("log", "Iniciando pruebas automatizadas")

                tester = ONTAutomatedTester(ip, detected_model)
                tester.out_q = out_q
                tester.opcionesTest = opciones
                tester._stop_event = stop_event

                print("Las opciones elegidas son: " + str(opciones))
                emit("pruebas", "Autenticando dispositivo")
                tester.run_all_tests()

                resultados = tester._resultados_finales()
                # Guardar para base diaria y global
                tester.saveBDiaria(resultados)
                emit("resultados", resultados)

                # print("[RESULTADOS] El modelo es: "+str(tester.model))
                if (tester.model == "MOD001" or tester.model == "MOD008"):
                    print("[RESULTADOS] Entrando a opción guardar resultados")
                    print("\n" + tester.generate_report())
                    tester.save_results2("test_mod001_mod008")

                todo_tests_on = all(tester.opcionesTest["tests"].values())
                if todo_tests_on:
                    tester._generarCertificado()

                emit("log", "Pruebas completadas")
                emit("pruebas", "Fin de pruebas")
                print(f"\n[✓] Pruebas completadas para {ip}")

                

                # Marcar que ya se ejecutó fase2 en esta sesión
                fase2_executed = True
                emit("log", "Entrando a MONITOREO: no se volverán a ejecutar pruebas hasta cambio de modo o prueba unitaria.")

            elif is_etiqueta_mode(opciones):
                # Modo Etiqueta: extraer info sin pruebas completas
                print(f"\n[FASE 2/3] EXTRACCIÓN DE ETIQUETA")
                print("-" * 60)

                emit("log", "Extrayendo información (Etiqueta)")

                et = ONTAutomatedTester(ip, detected_model)
                et.out_q = out_q
                et.opcionesTest = opciones

                emit("pruebas", "Extrayendo datos de etiqueta")
                et.run_all_tests()

                resultados = et._resultados_finales()
                # Guardar para base diaria y global
                et.saveBDiaria(resultados)
                emit("resultados", resultados)
                if (et.model == "MOD001" or et.model == "MOD008"):
                    print("[RESULTADOS] Entrando a opción guardar resultados")
                    print("\n" + et.generate_report())
                    et.save_results2("test_mod001_mod008")
                emit("log", "Etiqueta completada")
                emit("pruebas", "Fin etiqueta")

                # Marcar que ya se ejecutó fase2 en esta sesión
                fase2_executed = True

            else:
                # Modo monitoreo puro (después de unitaria o sin modo definido)
                emit("log", "Dispositivo detectado. En monitoreo: esperando acción del usuario...")
            
            
            # FASE 3: MONITOREO
            print(f"\n[FASE 3/3] MONITOREO DE CONEXIÓN")
            print("-" * 60)

            # Monitoreo simple: 1 ping fallido = desconexión = nuevo ciclo de escaneo
            user_interrupted = monitor_device_connection(ip, interval=1, max_failures=1, stop_event=stop_event)

            if user_interrupted:
                # stop_event o Ctrl+C: salir del main_loop
                print("\n[*] Saliendo del ciclo de monitoreo...")
                break

            # Ping perdido = desconexión real → nuevo ciclo de escaneo
            print("\n[*] Dispositivo desconectado. Iniciando nuevo ciclo de escaneo...")
            emit("con", "DESCONECTADO")
            fase2_executed = False  # Resetear para que el próximo dispositivo ejecute fase2
            time.sleep(1)
            # Vuelve al while principal (nuevo ciclo)
                
    except KeyboardInterrupt:
        print("\n\n" + "="*80)
        print("DETENIDO POR EL USUARIO")
        print("="*80)
        print(f"Total de ciclos completados: {cycle_count}")
        if last_tested_ip:
            print(f"Último dispositivo testeado: {last_tested_ip}")
        print("\n[*] Programa finalizado")

#def pruebaUnitariaONT():

if __name__ == "__main__":
    # Verificar si se pasan argumentos de línea de comandos
    if len(sys.argv) > 1:
        # Modo tradicional con argumentos
        main()
    else:
        # Modo recursivo sin argumentos
        main_loop()