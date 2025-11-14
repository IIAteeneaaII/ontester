#!/usr/bin/env python3
"""
ONT Automated Test Suite
Pruebas automatizadas basadas en protocolo de testing
Fecha: 10/11/2025
"""

import argparse
import json
import sys
import socket
import subprocess
import platform
import re
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Selenium para login automático
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("[WARNING] Selenium no disponible. Instala con: pip install selenium webdriver-manager")

class ONTAutomatedTester:
    def __init__(self, host: str, model: str = None):
        self.host = host
        self.model = model  # Puede ser None, se detectará automáticamente
        self.base_url = f"http://{host}"
        self.ajax_url = f"http://{host}/cgi-bin/ajax"
        self.session = requests.Session()
        self.authenticated = False
        self.session_id = None
        self.test_results = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "host": host,
                "model": model,
                "serial_number": None
            },
            "tests": {}
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
            "HUAWEI HG8145X6": "MOD003",
            "HG8145X6": "MOD003",
            "HG6145F1": "MOD003",  # ModelName reportado por software (incorrecto pero real)
            
            # MOD002: ZTE ZXHN F670L
            "ZTE ZXHN F670L": "MOD002",
            "ZXHN F670L": "MOD002",
            "ZTE F670L": "MOD002",
            "F670L": "MOD002",
            
            # MOD001: FIBERHOME HG6145F
            "FIBERHOME HG6145F": "MOD001",
            "HG6145F": "MOD001",
            
            # MOD006: GRANDSTREAM HT818
            "GRANDSTREAM HT818": "MOD006",
            "GS-HT818": "MOD006",
            "HT818": "MOD006",
        }
    
    def _calculate_physical_sn(self, sn_logical: str) -> str:
        """
        Calcula Serial Number Físico a partir del SN Lógico
        
        Patrón detectado:
        - MOD001 (Fiberhome): "FHTT"(HEX) + Suffix ya en HEX
        - Otros modelos: Requieren investigación adicional
        """
        if not sn_logical or len(sn_logical) < 4:
            return None
        
        # MOD001 (Fiberhome HG6145F)
        if sn_logical.startswith("FH"):
            prefix = sn_logical[:4]  # "FHTT"
            suffix = sn_logical[4:]   # Ya en formato HEX
            prefix_hex = ''.join([format(ord(c), '02X') for c in prefix])
            return prefix_hex + suffix
        
        # Otros modelos: algoritmo desconocido
        return None
    
    def _calculate_physical_sn_decimal(self, sn_logical: str) -> str:
        """
        Calcula Serial Number Físico con primeros 2 bytes en DECIMAL
        Formato: DDDD.DDDD.HHHH (decimal.decimal.hex)
        
        Usado para display en reportes de MOD001-005
        """
        if not sn_logical or len(sn_logical) < 4:
            return None
        
        # MOD001 (Fiberhome HG6145F)
        if sn_logical.startswith("FH"):
            prefix = sn_logical[:4]  # "FHTT"
            suffix = sn_logical[4:]   # Ya en formato HEX
            
            # Convertir los primeros 2 caracteres a decimal
            byte1_decimal = ord(prefix[0])  # 'F'
            byte2_decimal = ord(prefix[1])  # 'H'
            
            # Convertir los siguientes 2 caracteres a HEX
            byte3_hex = format(ord(prefix[2]), '02X')  # 'T'
            byte4_hex = format(ord(prefix[3]), '02X')  # 'T'
            
            # Formato: DDDD.DDDD.HHHH + suffix
            return f"{byte1_decimal:04d}.{byte2_decimal:04d}.{byte3_hex}{byte4_hex}{suffix}"
        
        # Otros modelos: algoritmo desconocido
        return None
    
    def _ajax_get(self, method: str, params: Dict = None) -> Dict:
        """Realiza peticion GET via AJAX endpoint"""
        params = params or {}
        params['ajaxmethod'] = method
        params['_'] = str(datetime.now().timestamp())
        
        try:
            response = self.session.get(
                self.ajax_url,
                params=params,
                auth=('root', 'admin'),
                timeout=5
            )
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"raw": response.text, "success": True}
            return {"success": False, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _ajax_post(self, method: str, data: Dict = None) -> Dict:
        """Realiza peticion POST via AJAX endpoint"""
        data = data or {}
        data['ajaxmethod'] = method
        if self.session_id:
            data['sessionid'] = self.session_id
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = self.session.post(
                self.ajax_url,
                data=data,
                auth=('root', 'admin'),
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                try:
                    return response.json()
                except:
                    return {"raw": response.text, "success": True}
            return {"success": False, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def login(self) -> bool:
        """Realiza login en la ONT via AJAX"""
        print("[AUTH] Intentando autenticacion...")
        
        # Detectar tipo de dispositivo primero
        device_type = self._detect_device_type()
        
        if device_type == "GRANDSTREAM":
            return self._login_grandstream()
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
            
            html = response.text.lower()
            server = response.headers.get('Server', '').lower()
            
            # Detectar Grandstream
            if 'grandstream' in html or 'grandstream' in server or 'ht818' in html:
                return "GRANDSTREAM"
            
            # Por defecto, asumir ONT estándar
            return "ONT"
            
        except:
            return "ONT"
    
    def _login_grandstream(self) -> bool:
        """Login específico para dispositivos Grandstream con POST y extracción de STATUS"""
        print("[AUTH] Dispositivo Grandstream detectado")
        
        try:
            # Paso 1: Obtener página de login para extraer gnkey
            response = self.session.get(self.base_url, timeout=5, verify=False)
            
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            gnkey_input = soup.find('input', {'name': 'gnkey'})
            gnkey = gnkey_input['value'] if gnkey_input else '0b82'
            
            # Paso 2: Realizar POST login
            login_data = {
                'username': 'admin',
                'P2': 'admin',
                'Login': 'Login',
                'gnkey': gnkey
            }
            
            response = self.session.post(
                f"{self.base_url}/cgi-bin/dologin",
                data=login_data,
                timeout=5,
                verify=False
            )
            
            # Verificar si el login fue exitoso
            if response.status_code == 200:
                # Verificar que no haya error de login
                if 'not recognized' in response.text or 'Remaining Attempts' in response.text:
                    print("[AUTH] Login fallido - credenciales incorrectas")
                    return False
                
                # Si el HTML contiene información del dispositivo, el login fue exitoso
                if 'Serial Number' in response.text or 'Product Model' in response.text:
                    self.authenticated = True
                    self.model = "MOD006"
                    self.test_results['metadata']['model'] = "MOD006"
                    self.test_results['metadata']['device_name'] = "GRANDSTREAM HT818"
                    self.test_results['metadata']['device_type'] = "ATA"
                    
                    print(f"[AUTH] Login exitoso - Modelo: MOD006 (GRANDSTREAM HT818)")
                    
                    # Extraer información de la página de status
                    grandstream_info = self._extract_grandstream_status_page(response.text)
                    
                    # Agregar información extraída a metadata
                    self.test_results['metadata'].update(grandstream_info)
                    
                    # Imprimir información encontrada
                    if grandstream_info.get('serial_number'):
                        print(f"[AUTH] Serial Number: {grandstream_info['serial_number']}")
                    if grandstream_info.get('mac_address'):
                        print(f"[AUTH] MAC Address: {grandstream_info['mac_address']}")
                    if grandstream_info.get('firmware_version'):
                        print(f"[AUTH] Firmware: {grandstream_info['firmware_version']}")
                    if grandstream_info.get('hardware_version'):
                        print(f"[AUTH] Hardware: {grandstream_info['hardware_version']}")
                    
                    return True
                else:
                    print("[AUTH] Login exitoso pero no se encontró información del dispositivo")
                    self.authenticated = True
                    return True
            else:
                print(f"[AUTH] Autenticación Grandstream fallida: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[AUTH] Error en autenticación Grandstream: {e}")
            return False
    
    def _extract_grandstream_status_page(self, html: str) -> Dict[str, Any]:
        """Extrae información de la página STATUS del Grandstream HT818"""
        info = {
            'extraction_methods_used': ['status_page_post_login'],
            'mac_address': None,
            'serial_number': None,
            'firmware_version': None,
            'hardware_version': None,
            'model_detected': None,
            'device_status': {}
        }
        
        # Patrones de extracción para la página de STATUS
        patterns = {
            'serial_number': r'Serial\s+Number[:\s]*</b></td>\s*<td[^>]*>\s*&nbsp;\s*([A-Z0-9]+)',
            'mac_wan': r'WAN\s*--\s*([0-9A-Fa-f:]{17})',
            'mac_lan': r'LAN\s*--\s*([0-9A-Fa-f:]{17})',
            'product_model': r'Product\s+Model[:\s]*</b></td>\s*<td[^>]*>\s*&nbsp;\s*([A-Z0-9]+)',
            'hardware_version': r'Hardware\s+Version[:\s]*</b></td>\s*<td[^>]*>\s*&nbsp;\s*([^\s<]+)',
            'software_version': r'Program\s*--\s*([0-9\.]+)',
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
            if match:
                value = match.group(1).strip()
                
                if key == 'serial_number':
                    info['serial_number'] = value
                elif key == 'mac_wan':
                    info['mac_address'] = value  # Usar WAN MAC como principal
                    info['mac_wan'] = value
                elif key == 'mac_lan':
                    info['mac_lan'] = value
                elif key == 'product_model':
                    info['model_detected'] = value
                elif key == 'hardware_version':
                    info['hardware_version'] = value
                elif key == 'software_version':
                    info['firmware_version'] = value
        
        # Patrones de fallback más simples si los anteriores no funcionan
        if not info.get('serial_number'):
            # Buscar cualquier secuencia alfanumérica larga que parezca un SN
            alt_sn = re.search(r'>([A-Z0-9]{14,})<', html)
            if alt_sn:
                candidate = alt_sn.group(1)
                if re.match(r'^[A-Z0-9]{10,}$', candidate):
                    info['serial_number'] = candidate
                    print(f"[INFO] Serial Number encontrado (método alternativo)")
        
        if not info.get('model_detected'):
            # Buscar patrón HT seguido de números
            alt_model = re.search(r'\bHT\s*(\d{3})\b', html, re.IGNORECASE)
            if alt_model:
                info['model_detected'] = f"HT{alt_model.group(1)}"
        
        return info
    
    def _extract_grandstream_info(self) -> Dict[str, Any]:
        """Extracción exhaustiva de información de dispositivos Grandstream"""
        info = {
            'extraction_methods_used': [],
            'mac_address': None,
            'serial_number': None,
            'firmware_version': None,
            'hardware_version': None,
            'model_detected': None,
            'ip_address': self.host,
            'uptime': None,
            'device_status': {}
        }
        
        print("[INFO] Iniciando extracción exhaustiva de información Grandstream...")
        
        # Método 1: Parseo de página principal
        try:
            response = self.session.get(
                self.base_url,
                auth=('admin', 'admin'),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                html = response.text
                
                # Buscar MAC address
                mac_match = re.search(r'MAC[:\s]+([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', html, re.IGNORECASE)
                if mac_match:
                    info['mac_address'] = mac_match.group(0).split()[-1]
                    info['extraction_methods_used'].append('HTML_MAC_parsing')
                
                # Buscar modelo
                model_patterns = [
                    r'HT\s*8\d{2}',
                    r'GS-HT\d+',
                    r'Grandstream\s+HT\d+'
                ]
                for pattern in model_patterns:
                    model_match = re.search(pattern, html, re.IGNORECASE)
                    if model_match:
                        info['model_detected'] = model_match.group(0)
                        info['extraction_methods_used'].append('HTML_model_parsing')
                        break
                
                # Buscar versión de firmware
                fw_patterns = [
                    r'Firmware[:\s]+Version[:\s]+([\d.]+)',
                    r'Software[:\s]+Version[:\s]+([\d.]+)',
                    r'Version[:\s]+([\d.]+)'
                ]
                for pattern in fw_patterns:
                    fw_match = re.search(pattern, html, re.IGNORECASE)
                    if fw_match:
                        info['firmware_version'] = fw_match.group(1)
                        info['extraction_methods_used'].append('HTML_firmware_parsing')
                        break
                
                print(f"[INFO] ✓ Método 1: Parseo HTML - {len([x for x in [info['mac_address'], info['model_detected'], info['firmware_version']] if x])} campos extraídos")
        except Exception as e:
            print(f"[INFO] ✗ Método 1: Parseo HTML falló - {e}")
        
        # Método 2: Status page
        status_pages = ['/status.html', '/status.htm', '/device_status.html']
        for page in status_pages:
            try:
                response = self.session.get(
                    f"{self.base_url}{page}",
                    auth=('admin', 'admin'),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200:
                    html = response.text
                    
                    # Buscar información de sistema
                    uptime_match = re.search(r'Uptime[:\s]+([\d\s:]+)', html, re.IGNORECASE)
                    if uptime_match and not info['uptime']:
                        info['uptime'] = uptime_match.group(1).strip()
                        info['extraction_methods_used'].append('status_page_uptime')
                    
                    # Buscar serial number
                    sn_match = re.search(r'Serial[:\s]+Number[:\s]+([A-Z0-9]+)', html, re.IGNORECASE)
                    if sn_match and not info['serial_number']:
                        info['serial_number'] = sn_match.group(1)
                        info['extraction_methods_used'].append('status_page_serial')
                    
                    print(f"[INFO] ✓ Método 2: Status page {page} - información adicional encontrada")
                    break
            except Exception:
                continue
        
        # Método 3: CGI endpoints específicos de Grandstream
        cgi_endpoints = [
            '/cgi-bin/api.values.get',
            '/cgi-bin/api-get_network_info',
            '/cgi-bin/api-sys_operation'
        ]
        
        for endpoint in cgi_endpoints:
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    auth=('admin', 'admin'),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200 and response.text:
                    # Intentar parsear como JSON
                    try:
                        data = response.json()
                        if isinstance(data, dict):
                            # Buscar campos conocidos
                            if 'mac' in data and not info['mac_address']:
                                info['mac_address'] = data['mac']
                                info['extraction_methods_used'].append(f'cgi_{endpoint.split("/")[-1]}')
                            if 'version' in data and not info['firmware_version']:
                                info['firmware_version'] = data['version']
                            if 'serial' in data and not info['serial_number']:
                                info['serial_number'] = data['serial']
                            
                            print(f"[INFO] ✓ Método 3: CGI endpoint {endpoint} - JSON parseado exitosamente")
                    except:
                        # Si no es JSON, intentar parsear como texto
                        if not info['mac_address']:
                            mac_match = re.search(r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', response.text)
                            if mac_match:
                                info['mac_address'] = mac_match.group(0)
                                info['extraction_methods_used'].append(f'cgi_{endpoint.split("/")[-1]}_text')
            except Exception:
                continue
        
        # Método 4: Información de headers HTTP y extracción profunda de MAC
        try:
            response = self.session.get(
                self.base_url,
                auth=('admin', 'admin'),
                timeout=3,
                verify=False
            )
            
            server_header = response.headers.get('Server', '')
            if server_header:
                info['device_status']['web_server'] = server_header
                info['extraction_methods_used'].append('http_headers')
                print(f"[INFO] ✓ Método 4: HTTP Headers - Server: {server_header}")
            
            # Extracción profunda de MAC del HTML (método más confiable para HT818)
            html = response.text
            
            # Intentar obtener frame principal después del login
            try:
                # El HT818 usa frames, buscar la página principal
                frame_match = re.search(r'src=["\']([^"\']+main[^"\']*)["\']', html, re.IGNORECASE)
                if frame_match:
                    main_page = frame_match.group(1)
                    main_response = self.session.get(
                        f"{self.base_url}/{main_page.lstrip('/')}",
                        auth=('admin', 'admin'),
                        timeout=3,
                        verify=False
                    )
                    if main_response.status_code == 200:
                        html = main_response.text
                        print(f"[INFO] ✓ Método 4a: Frame principal encontrado - {main_page}")
            except:
                pass
            
            # Buscar MAC en múltiples formatos con contexto
            mac_patterns = [
                (r'MAC\s*(?:Address)?[:\s=]+([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', 'MAC con etiqueta'),
                (r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})', 'MAC genérico'),
                (r'([0-9A-Fa-f]{2}\.){5}([0-9A-Fa-f]{2})', 'MAC con puntos'),
                (r'\b([0-9A-Fa-f]{12})\b', 'MAC sin separadores'),
            ]
            
            for pattern, desc in mac_patterns:
                mac_matches = re.findall(pattern, html)
                if mac_matches:
                    # Procesar la primera MAC válida encontrada
                    if isinstance(mac_matches[0], tuple):
                        mac = ''.join(mac_matches[0])
                    else:
                        mac = mac_matches[0]
                    
                    # Normalizar a formato estándar XX:XX:XX:XX:XX:XX
                    mac_clean = re.sub(r'[:-.]', '', mac)
                    if len(mac_clean) == 12:
                        mac_formatted = ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)]).upper()
                        if not info['mac_address']:  # Solo si no se encontró antes
                            info['mac_address'] = mac_formatted
                            info['extraction_methods_used'].append(f'html_mac_{desc}')
                            
                            # Generar pseudo-SN basado en MAC (para HT818 sin API de SN)
                            # Formato: HT818-XXXXXXXXXXXX (últimos 12 dígitos del MAC)
                            info['serial_number'] = f"HT818-{mac_clean}"
                            info['serial_number_source'] = 'MAC-derived'
                            
                            print(f"[INFO] ✓ Método 4b: MAC extraído ({desc}) - {mac_formatted}")
                            print(f"[INFO] ℹ  Pseudo-SN generado: {info['serial_number']} (basado en MAC)")
                    break
                    
        except Exception as e:
            print(f"[INFO] ✗ Método 4: Extracción profunda falló - {e}")
        
        # Método 5: Telnet banner (sin conectar completamente)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, 23))
            
            if result == 0:
                info['device_status']['telnet_port'] = 'open'
                info['extraction_methods_used'].append('telnet_scan')
                print("[INFO] ✓ Método 5: Telnet - Puerto 23 abierto")
            sock.close()
        except Exception:
            pass
        
        # Método 6: SSH banner
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, 22))
            
            if result == 0:
                info['device_status']['ssh_port'] = 'open'
                info['extraction_methods_used'].append('ssh_scan')
                print("[INFO] ✓ Método 6: SSH - Puerto 22 abierto")
            sock.close()
        except Exception:
            pass
        
        # Método 7: SIP port (5060)
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((self.host, 5060))
            
            if result == 0:
                info['device_status']['sip_port'] = 'open'
                info['extraction_methods_used'].append('sip_scan')
                print("[INFO] ✓ Método 7: SIP - Puerto 5060 abierto")
            sock.close()
        except Exception:
            pass
        
        # Resumen de extracción
        methods_count = len(set(info['extraction_methods_used']))
        fields_extracted = sum(1 for v in [info['mac_address'], info['serial_number'], 
                                           info['firmware_version'], info['model_detected']] if v)
        
        print(f"[INFO] Extracción completada: {methods_count} métodos usados, {fields_extracted} campos principales extraídos")
        
        return info
    
    def _selenium_login(self, headless: bool = True, timeout: int = 10) -> bool:
        """Automatiza login web usando Selenium para obtener sessionid válido
        
        Args:
            headless: Si True, ejecuta navegador sin interfaz gráfica
            timeout: Tiempo máximo de espera en segundos
            
        Returns:
            bool: True si login exitoso, False si falló
        """
        if not SELENIUM_AVAILABLE:
            print("[ERROR] Selenium no está instalado. Instala con: pip install selenium webdriver-manager")
            return False
        
        driver = None
        try:
            print(f"[SELENIUM] Iniciando login automático a {self.host}...")
            
            # Configurar opciones de Chrome
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless=new')  # Modo headless moderno
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--log-level=3')  # Suprimir logs verbosos
            chrome_options.add_argument(f'--host-resolver-rules=MAP {self.host} 192.168.100.1')
            
            # Deshabilitar warnings de certificado
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--allow-insecure-localhost')
            
            # Inicializar driver con WebDriver Manager
            print("[SELENIUM] Descargando/verificando ChromeDriver...")
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(timeout)
            
            # Navegar a la página principal (el router redirigirá al login)
            # Usar IP directa en lugar de login.html para evitar bloqueo de nginx
            base_url = f"http://{self.host}/"
            print(f"[SELENIUM] Navegando a {base_url}...")
            
            try:
                driver.get(base_url)
            except Exception as e:
                print(f"[ERROR] No se pudo cargar {base_url}: {e}")
                driver.quit()
                return False
            
            # Esperar breve a que cargue la página
            time.sleep(2)
            
            # Verificar si la página cargó correctamente
            if "400" in driver.title or "error" in driver.page_source.lower()[:500]:
                print("[ERROR] La página retornó error 400 - El router bloqueó la petición")
                driver.quit()
                return False
            
            # Esperar a que cargue el formulario
            wait = WebDriverWait(driver, timeout)
            
            # Buscar campos de login (intentar varios selectores comunes)
            # NOTA: Fiberhome usa 'user_name' y 'loginpp' (NO es type=password!)
            username_selectors = [
                (By.ID, 'user_name'),           # Fiberhome específico
                (By.NAME, 'user_name'),         # Fiberhome específico
                (By.ID, 'username'),
                (By.NAME, 'username'),
                (By.ID, 'user'),
                (By.NAME, 'user'),
                (By.ID, 'userName'),
                (By.NAME, 'userName'),
                (By.CSS_SELECTOR, 'input[type="text"]'),
                (By.CSS_SELECTOR, 'input.username'),
                (By.XPATH, '//input[@placeholder="Username" or @placeholder="Usuario"]')
            ]
            
            password_selectors = [
                (By.ID, 'loginpp'),             # Fiberhome específico (type=text con clase especial!)
                (By.NAME, 'loginpp'),           # Fiberhome específico
                (By.CSS_SELECTOR, 'input.fh-text-security-inter'),  # Fiberhome clase especial
                (By.ID, 'password'),
                (By.NAME, 'password'),
                (By.ID, 'pass'),
                (By.NAME, 'pass'),
                (By.ID, 'userPassword'),
                (By.NAME, 'userPassword'),
                (By.CSS_SELECTOR, 'input[type="password"]'),
                (By.CSS_SELECTOR, 'input.password'),
                (By.XPATH, '//input[@placeholder="Password" or @placeholder="Contraseña"]'),
                (By.XPATH, '//input[@type="password"]')
            ]
            
            username_field = None
            password_field = None
            
            # Encontrar campo de usuario
            for by, selector in username_selectors:
                try:
                    username_field = wait.until(EC.presence_of_element_located((by, selector)))
                    print(f"[SELENIUM] Campo username encontrado: {by}='{selector}'")
                    break
                except:
                    continue
            
            if not username_field:
                print("[ERROR] No se encontro campo de usuario en el formulario")
                driver.quit()
                return False
            
            # Encontrar campo de contrasena
            for by, selector in password_selectors:
                try:
                    password_field = driver.find_element(by, selector)
                    print(f"[SELENIUM] Campo password encontrado: {by}='{selector}'")
                    break
                except:
                    continue
            
            if not password_field:
                print("[ERROR] No se encontro campo de contrasena. Guardando screenshot...")
                try:
                    screenshot_path = Path("C:/Users/Admin/Documents/GitHub/ontester/reports/selenium_debug.png")
                    driver.save_screenshot(str(screenshot_path))
                    print(f"[DEBUG] Screenshot guardado: {screenshot_path}")
                except:
                    pass
                driver.quit()
                return False
            
            # Ingresar credenciales
            print("[SELENIUM] Ingresando credenciales...")
            username_field.clear()
            username_field.send_keys('root')
            password_field.clear()
            password_field.send_keys('Jaim3SeLaCome')
            
            # Buscar y hacer clic en botón de login
            button_selectors = [
                (By.ID, 'login_btn'),           # Fiberhome específico
                (By.ID, 'loginBtn'),
                (By.NAME, 'login'),
                (By.CSS_SELECTOR, 'button[type="submit"]'),
                (By.CSS_SELECTOR, 'input[type="submit"]'),
                (By.XPATH, '//button[contains(text(), "Login")]'),
                (By.XPATH, '//button[contains(text(), "Entrar")]')
            ]
            
            login_button = None
            for by, selector in button_selectors:
                try:
                    login_button = driver.find_element(by, selector)
                    print(f"[SELENIUM] Botón login encontrado: {by}='{selector}'")
                    break
                except:
                    continue
            
            if login_button:
                login_button.click()
                print("[SELENIUM] Click en botón de login...")
            else:
                # Si no hay botón, enviar formulario con Enter
                print("[SELENIUM] Enviando formulario con Enter...")
                from selenium.webdriver.common.keys import Keys
                password_field.send_keys(Keys.RETURN)
            
            # Esperar a que cargue la página principal (varios indicadores posibles)
            time.sleep(2)  # Dar tiempo para procesar login
            
            # Extraer cookies
            cookies = driver.get_cookies()
            print(f"[SELENIUM] Cookies obtenidas: {len(cookies)}")
            
            # Buscar sessionid en cookies
            for cookie in cookies:
                if 'sessionid' in cookie.get('name', '').lower():
                    self.session_id = cookie['value']
                    print(f"[SELENIUM] OK - SessionID extraido de cookie: {self.session_id[:8]}...")
                    
                    # Agregar cookie a requests.Session
                    self.session.cookies.set(
                        cookie['name'],
                        cookie['value'],
                        domain=cookie.get('domain', self.host),
                        path=cookie.get('path', '/')
                    )
                    driver.quit()
                    return True
            
            # Si no está en cookies, intentar extraer del HTML
            print("[SELENIUM] SessionID no encontrado en cookies, buscando en HTML...")
            page_source = driver.page_source
            sessionid_match = re.search(r'sessionid["\'\'\s:=]+([a-zA-Z0-9]+)', page_source)
            
            if sessionid_match:
                self.session_id = sessionid_match.group(1)
                print(f"[SELENIUM] OK - SessionID extraido del HTML: {self.session_id[:8]}...")
                driver.quit()
                return True
            
            # Ultimo intento: hacer request AJAX para obtener sessionid
            print("[SELENIUM] Intentando obtener sessionid via AJAX desde navegador...")
            ajax_script = f'''
                return fetch('{self.ajax_url}?ajaxmethod=get_base_info', {{
                    credentials: 'include'
                }})
                .then(r => r.json())
                .then(data => data.sessionid || null)
                .catch(() => null);
            '''
            
            sessionid_from_ajax = driver.execute_script(ajax_script)
            if sessionid_from_ajax:
                self.session_id = sessionid_from_ajax
                print(f"[SELENIUM] OK - SessionID obtenido via AJAX: {self.session_id[:8]}...")
                driver.quit()
                return True
            
            print("[ERROR] No se pudo extraer sessionid después del login")
            driver.quit()
            return False
            
        except Exception as e:
            print(f"[ERROR] Selenium login falló: {type(e).__name__} - {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return False
    
    def _do_login_post(self) -> bool:
        """Realiza login POST completo para obtener sessionid válido"""
        # Estrategia 1: Intentar login via formulario HTML tradicional
        try:
            login_url = f"{self.base_url}/login.html"
            login_data = {
                'username': 'root',
                'password': 'admin',
                'action': 'login'
            }
            
            response = self.session.post(
                login_url,
                data=login_data,
                auth=('root', 'admin'),
                timeout=5,
                verify=False,
                allow_redirects=True
            )
            
            # Buscar sessionid en cookies
            if 'sessionid' in self.session.cookies:
                self.session_id = self.session.cookies['sessionid']
                print(f"[AUTH] Login POST exitoso - SessionID de cookie: {self.session_id[:8]}...")
                return True
            
            # Buscar sessionid en el HTML de respuesta
            if response.status_code == 200:
                sessionid_match = re.search(r'sessionid["\'\s:=]+([a-zA-Z0-9]+)', response.text)
                if sessionid_match:
                    self.session_id = sessionid_match.group(1)
                    print(f"[AUTH] Login POST exitoso - SessionID del HTML: {self.session_id[:8]}...")
                    return True
        except Exception as e:
            print(f"[DEBUG] Estrategia 1 (form login) fall\u00f3: {e}")
        
        # Estrategia 2: Intentar do_login via AJAX POST
        try:
            login_data = {
                'username': 'root',
                'password': 'admin'
            }
            
            response = self._ajax_post('do_login', login_data)
            
            if response.get('result') == 'success' or response.get('sessionid'):
                self.session_id = response.get('sessionid')
                print(f"[AUTH] Login AJAX POST exitoso - SessionID: {self.session_id[:8]}...")
                return True
        except Exception as e:
            print(f"[DEBUG] Estrategia 2 (AJAX do_login) fall\u00f3: {e}")
        
        # Estrategia 3: Acceder a la p\u00e1gina principal autenticada y extraer sessionid
        try:
            response = self.session.get(
                f"{self.base_url}/main.html",
                auth=('root', 'admin'),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                # Buscar sessionid en JavaScript o variables globales
                patterns = [
                    r'var\s+sessionid\s*=\s*["\']([a-zA-Z0-9]+)["\']',
                    r'sessionid["\'\s:=]+["\']?([a-zA-Z0-9]{8,})["\']?',
                    r'session_id["\'\s:=]+["\']?([a-zA-Z0-9]{8,})["\']?'
                ]
                
                for pattern in patterns:
                    match = re.search(pattern, response.text, re.IGNORECASE)
                    if match:
                        self.session_id = match.group(1)
                        print(f"[AUTH] SessionID extraído de main.html: {self.session_id[:8]}...")
                        return True
        except Exception as e:
            print(f"[DEBUG] Estrategia 3 (main.html parsing) fall\u00f3: {e}")
        
        print(f"[AUTH] Todas las estrategias de login POST fallaron")
        return False
    
    def _login_ont_standard(self) -> bool:
        """Login estándar para ONTs via AJAX"""
        selenium_success = False
        
        # ESTRATEGIA 1: Intentar Selenium para login automático (método más confiable)
        if SELENIUM_AVAILABLE:
            print("[AUTH] Intentando login automático con Selenium...")
            if self._selenium_login(headless=True, timeout=15):
                print("[AUTH] OK - Login Selenium exitoso")
                selenium_success = True
                # NO retornar aquí - continuar para extraer info del dispositivo
            else:
                print("[AUTH] WARNING - Selenium fallo, intentando metodos alternativos...")
        else:
            print("[AUTH] WARNING - Selenium no disponible (pip install selenium webdriver-manager)")
        
        # ESTRATEGIA 2: Obtener información del dispositivo (prueba de conectividad)
        device_info = self._ajax_get('get_device_name')
        
        if device_info.get('success') == False:
            print(f"[AUTH] Error en conexion: {device_info.get('error', 'Unknown')}")
            return False
        
        # Si llegamos aqui, Basic Auth funciono
        if device_info.get('ModelName'):
            self.authenticated = True
            model_name = device_info['ModelName']
            self.test_results['metadata']['device_name'] = model_name
            self.test_results['metadata']['device_type'] = "ONT"
            
            # Auto-detectar modelo si no se especificó
            if not self.model:
                detected_model = self._detect_model(model_name)
                self.model = detected_model
                self.test_results['metadata']['model'] = detected_model
                display_name = self._get_model_display_name(detected_model, model_name)
                self.test_results['metadata']['model_display_name'] = display_name
                print(f"[AUTH] Modelo detectado automaticamente: {detected_model} ({display_name})")
            else:
                display_name = self._get_model_display_name(self.model, model_name)
                self.test_results['metadata']['model_display_name'] = display_name
                print(f"[AUTH] Autenticacion exitosa - Modelo: {display_name}")
            
            # Obtener info del operador y serial
            operator_info = self._ajax_get('get_operator')
            if operator_info.get('SerialNumber'):
                serial_logical = operator_info['SerialNumber']
                self.test_results['metadata']['serial_number_logical'] = serial_logical
                self.test_results['metadata']['serial_number'] = serial_logical  # Mantener compatibilidad
                self.test_results['metadata']['operator'] = operator_info.get('operator_name', 'Unknown')
                print(f"[AUTH] Serial Number (Logico): {serial_logical}")
                
                # Calcular SN Físico si es posible
                sn_physical = self._calculate_physical_sn(serial_logical)
                if sn_physical and "?" not in sn_physical:
                    self.test_results['metadata']['serial_number_physical'] = sn_physical
                    print(f"[AUTH] Serial Number (Fisico/PON): {sn_physical} (calculado)")
                else:
                    print(f"[NOTE] El SN fisico/PON debe obtenerse de la etiqueta del dispositivo")
            
            # Obtener sessionid válido para acceder a endpoints protegidos
            # (Solo si Selenium no lo obtuvo ya)
            if not self.session_id:
                print("[AUTH] Obteniendo sessionid para acceso completo...")
                self._do_login_post()
            else:
                print(f"[AUTH] SessionID ya disponible: {self.session_id[:8]}... (de Selenium)")
            
            # Extraer información completa con get_base_info (requiere sessionid)
            base_info = self._extract_base_info()
            
            # Si get_base_info funciona y no teníamos sessionid, extraerlo de su respuesta
            if base_info and base_info.get('raw_data', {}).get('sessionid'):
                if not self.session_id:
                    self.session_id = base_info['raw_data']['sessionid']
                    print(f"[AUTH] SessionID extraído de get_base_info: {self.session_id}")
            
            if base_info:
                print(f"[INFO] Información completa obtenida vía get_base_info")
                
                # Actualizar metadata con información de base_info
                if base_info.get('serial_number_physical'):
                    self.test_results['metadata']['serial_number_physical'] = base_info['serial_number_physical']
                    print(f"[AUTH] Serial Number (Fisico/PON): {base_info['serial_number_physical']} (gponsn)")
                
                if base_info.get('mac_address'):
                    self.test_results['metadata']['mac_address'] = base_info['mac_address']
                    self.test_results['metadata']['mac_source'] = 'get_base_info.brmac'
                    print(f"[AUTH] MAC Address: {base_info['mac_address']} (brmac)")
                
                if base_info.get('hardware_version'):
                    self.test_results['metadata']['hardware_version'] = base_info['hardware_version']
                    print(f"[AUTH] Hardware Version: {base_info['hardware_version']}")
                
                if base_info.get('software_version'):
                    self.test_results['metadata']['software_version'] = base_info['software_version']
                    print(f"[AUTH] Software Version: {base_info['software_version']}")
                
                if base_info.get('usb_status'):
                    print(f"[AUTH] USB Status: {base_info['usb_status']}")
                
                # Guardar información completa para tests posteriores
                self.test_results['metadata']['base_info'] = base_info
                
                # Extraer información WiFi
                print(f"[INFO] Extrayendo información WiFi...")
                # Intentar primero get_allwan_info_broadBand (sin encriptar)
                wifi_info = self._extract_wifi_allwan()
                if not wifi_info:
                    # Fallback a get_wifi_status (encriptado)
                    print(f"[INFO] Intentando método alternativo de WiFi...")
                    wifi_info = self._extract_wifi_info()
                
                if wifi_info:
                    self.test_results['metadata']['base_info']['wifi_info'] = wifi_info
                    if wifi_info.get('ssid_24ghz'):
                        print(f"[AUTH] WiFi 2.4GHz: {wifi_info['ssid_24ghz']}")
                    if wifi_info.get('ssid_5ghz'):
                        print(f"[AUTH] WiFi 5GHz: {wifi_info['ssid_5ghz']}")
            else:
                # Fallback: intentar extraer MAC con método alternativo
                mac_info = self._extract_ont_mac()
                if mac_info:
                    self.test_results['metadata']['mac_address'] = mac_info['mac_address']
                    self.test_results['metadata']['mac_source'] = mac_info['source']
                    print(f"[AUTH] MAC Address: {mac_info['mac_address']} (fuente: {mac_info['source']})")
            
            return True
        
        print("[AUTH] Autenticacion fallida")
        return False
    
    def _extract_ont_mac(self) -> Dict[str, str]:
        """Intenta extraer la MAC address del ONT usando múltiples métodos"""
        
        # Método 1: Tabla ARP del sistema (más confiable para ONTs)
        try:
            import subprocess
            import platform
            
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['arp', '-a', self.host],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if result.returncode == 0:
                    # Buscar MAC en formato Windows (xx-xx-xx-xx-xx-xx)
                    mac_match = re.search(
                        r'([0-9A-Fa-f]{2}[-]){5}([0-9A-Fa-f]{2})',
                        result.stdout
                    )
                    
                    if mac_match:
                        mac = mac_match.group(0)
                        # Convertir guiones a dos puntos
                        mac_formatted = mac.replace('-', ':').upper()
                        return {
                            'mac_address': mac_formatted,
                            'source': 'arp_table'
                        }
            else:
                # Linux/Mac: arp <ip>
                result = subprocess.run(
                    ['arp', self.host],
                    capture_output=True,
                    text=True,
                    timeout=3
                )
                
                if result.returncode == 0:
                    mac_match = re.search(
                        r'([0-9A-Fa-f]{2}[:]){5}([0-9A-Fa-f]{2})',
                        result.stdout
                    )
                    
                    if mac_match:
                        return {
                            'mac_address': mac_match.group(0).upper(),
                            'source': 'arp_table'
                        }
        except Exception as e:
            print(f"[DEBUG] ARP extraction failed: {e}")
        
        # Método 2: Lista de métodos AJAX que podrían contener información de red/MAC
        ajax_methods_to_try = [
            'get_lan_info',
            'get_network_info',
            'get_network_status',
            'get_wan_info',
            'get_eth_info',
            'get_interface_info',
            'get_hardware_info',
            'get_mac_address',
            'get_system_info',
        ]
        
        # Intentar cada método AJAX
        for method in ajax_methods_to_try:
            try:
                response = self._ajax_get(method)
                
                if response and isinstance(response, dict):
                    # Buscar campos que contengan "mac" o "address"
                    for key, value in response.items():
                        key_lower = key.lower()
                        if 'mac' in key_lower and value and isinstance(value, str):
                            # Validar que parece una MAC
                            if re.match(r'^[0-9A-Fa-f:.-]{12,17}$', value):
                                # Normalizar formato
                                mac_clean = re.sub(r'[:-.]', '', value)
                                if len(mac_clean) == 12:
                                    mac_formatted = ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)]).upper()
                                    return {
                                        'mac_address': mac_formatted,
                                        'source': f'ajax_{method}.{key}'
                                    }
            except:
                continue
        
        # Si no se encontró por AJAX, intentar desde la página principal HTML
        try:
            response = self.session.get(self.base_url, timeout=3, verify=False)
            if response.status_code == 200:
                html = response.text
                
                # Buscar patrones de MAC en el HTML
                mac_patterns = [
                    r'MAC[:\s]+([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
                    r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
                ]
                
                for pattern in mac_patterns:
                    mac_matches = re.findall(pattern, html)
                    if mac_matches:
                        if isinstance(mac_matches[0], tuple):
                            mac = ''.join(mac_matches[0])
                        else:
                            mac = mac_matches[0]
                        
                        mac_clean = re.sub(r'[:-.]', '', mac)
                        if len(mac_clean) == 12:
                            mac_formatted = ':'.join([mac_clean[i:i+2] for i in range(0, 12, 2)]).upper()
                            return {
                                'mac_address': mac_formatted,
                                'source': 'html_parsing'
                            }
        except:
            pass
        
        return None
    
    def _extract_base_info(self) -> Dict[str, Any]:
        """Extrae información completa del dispositivo usando get_base_info (requiere login POST)"""
        base_info = self._ajax_get('get_base_info')
        
        if not base_info or base_info.get('session_valid') != 1:
            print("[INFO] get_base_info no disponible (requiere login completo)")
            return None
        
        extracted = {
            'extraction_method': 'ajax_get_base_info',
            'raw_data': base_info
        }
        
        # Información del dispositivo
        if base_info.get('ModelName'):
            extracted['model_name'] = base_info['ModelName']
        if base_info.get('Manufacturer'):
            extracted['manufacturer'] = base_info['Manufacturer']
        if base_info.get('ManufacturerOUI'):
            extracted['manufacturer_oui'] = base_info['ManufacturerOUI']
        
        # Versiones de hardware y software
        if base_info.get('HardwareVersion'):
            extracted['hardware_version'] = base_info['HardwareVersion']
        if base_info.get('SoftwareVersion'):
            extracted['software_version'] = base_info['SoftwareVersion']
        
        # Serial Numbers
        if base_info.get('SerialNumber'):
            extracted['serial_number_logical'] = base_info['SerialNumber']
        if base_info.get('gponsn'):
            # gponsn contiene el Serial Number Físico/PON directamente en HEX
            extracted['serial_number_physical'] = base_info['gponsn']
            print(f"[INFO] Serial Number Físico/PON (gponsn): {base_info['gponsn']}")
        
        # MAC Addresses
        if base_info.get('brmac'):
            extracted['mac_address_br'] = base_info['brmac']
            extracted['mac_address'] = base_info['brmac']  # Usar como principal
        if base_info.get('tr069_mac'):
            extracted['mac_address_tr069'] = base_info['tr069_mac']
        
        # Potencias ópticas TX/RX
        if base_info.get('txpower'):
            extracted['tx_power_dbm'] = base_info['txpower']
        if base_info.get('rxpower'):
            extracted['rx_power_dbm'] = base_info['rxpower']
        
        # Información de sistema
        if base_info.get('uptime'):
            extracted['uptime_seconds'] = base_info['uptime']
        if base_info.get('os_version'):
            extracted['os_version'] = base_info['os_version']
        if base_info.get('compile_time'):
            extracted['compile_time'] = base_info['compile_time']
        
        # Capacidades del hardware
        if base_info.get('lan_port_num'):
            extracted['lan_ports'] = int(base_info['lan_port_num'])
        if base_info.get('usb_port_num'):
            extracted['usb_ports'] = int(base_info['usb_port_num'])
        if base_info.get('voice_port_num'):
            extracted['voice_ports'] = int(base_info['voice_port_num'])
        if base_info.get('wifi_device'):
            extracted['wifi_capable'] = bool(int(base_info['wifi_device']))
        
        # Estado de los puertos LAN
        lan_status = {}
        lan_status_physical = {}  # Solo puertos físicamente conectados (Up)
        for i in range(1, 5):
            key = f'lan_status_{i}'
            if base_info.get(key):
                status = base_info[key]
                lan_status[f'lan{i}'] = status
                # Solo incluir en physical si está Up (realmente conectado)
                if status == 'Up':
                    lan_status_physical[f'lan{i}'] = 'Up'
        
        if lan_status:
            extracted['lan_status'] = lan_status
            extracted['lan_status_physical'] = lan_status_physical  # Solo conectados físicamente
        
        # Estado PON
        if base_info.get('ponmode'):
            extracted['pon_mode'] = base_info['ponmode']
        if base_info.get('pon_reg_state'):
            extracted['pon_registered'] = base_info['pon_reg_state'] == '1'
        if base_info.get('WANAccessType'):
            extracted['wan_access_type'] = base_info['WANAccessType']
        
        # Información del operador/LOID
        if base_info.get('loid'):
            extracted['loid'] = base_info['loid']
        if base_info.get('loid_name'):
            extracted['loid_name'] = base_info['loid_name']
        
        # Estadísticas de tráfico PON
        if base_info.get('ponBytesSent'):
            extracted['pon_bytes_sent'] = int(base_info['ponBytesSent'])
        if base_info.get('ponBytesReceived'):
            extracted['pon_bytes_received'] = int(base_info['ponBytesReceived'])
        
        # Información del transceiver óptico
        if base_info.get('supplyvottage'):
            extracted['supply_voltage'] = base_info['supplyvottage']
        if base_info.get('biascurrent'):
            extracted['bias_current'] = base_info['biascurrent']
        if base_info.get('transceivertemperature'):
            extracted['transceiver_temperature'] = base_info['transceivertemperature']
        
        # Uso de recursos
        if base_info.get('cpu_usage'):
            extracted['cpu_usage_percent'] = int(base_info['cpu_usage'])
        if base_info.get('mem_total') and base_info.get('mem_free'):
            mem_total = int(base_info['mem_total'])
            mem_free = int(base_info['mem_free'])
            extracted['memory_total_kb'] = mem_total
            extracted['memory_free_kb'] = mem_free
            extracted['memory_used_percent'] = round((1 - mem_free/mem_total) * 100, 2) if mem_total > 0 else 0
        if base_info.get('flash_usage'):
            extracted['flash_usage_percent'] = int(base_info['flash_usage'])
        
        # Estado USB
        if base_info.get('usb_status'):
            extracted['usb_status'] = base_info['usb_status']
        
        # Build version
        if base_info.get('build_version'):
            extracted['build_version'] = base_info['build_version']
        
        # Vendor
        if base_info.get('vendor'):
            extracted['vendor'] = base_info['vendor']
        
        # ADVERTENCIA: Validar estado PON (puede indicar fibra conectada)
        # Esto es importante porque el usuario puede afirmar que no hay fibra
        # pero el estado PON puede contradecir esa afirmación
        pon_reg_state = base_info.get('pon_reg_state')
        rx_power = base_info.get('rxpower')
        
        if pon_reg_state == '5' and rx_power:
            try:
                rx_val = float(rx_power)
                # Si RX power > -28 dBm, hay señal óptica real
                if rx_val > -28:
                    extracted['pon_warning'] = {
                        'status': 'REGISTERED_WITH_SIGNAL',
                        'message': 'ONT registrado en OLT con señal óptica válida',
                        'note': 'Estado indica fibra FÍSICAMENTE CONECTADA (verificar físicamente)',
                        'pon_reg_state': pon_reg_state,
                        'rx_power_dbm': rx_power,
                        'interpretation': f'RX={rx_power}dBm indica conexión activa (normal: -15 a -25 dBm)'
                    }
                    print(f"[WARN] PON registrado (state={pon_reg_state}) con RX={rx_power}dBm - Indica fibra conectada")
            except ValueError:
                pass
        
        return extracted
    
    def _decrypt_wifi_credential(self, encrypted_hex: str) -> str:
        """Desencripta SSIDs y passwords WiFi que vienen en formato hexadecimal encriptado"""
        try:
            # Los dispositivos Fiberhome usan una clave fija para encriptar WiFi credentials
            # La clave está hardcoded en el firmware: "mC8eC0cUc/mC8eC0c="
            from Crypto.Cipher import AES
            from Crypto.Util.Padding import unpad
            import base64
            
            # Clave de encriptación fija de Fiberhome
            key = b'mC8eC0cUc/mC8eC0c='
            
            # Convertir de hex a bytes
            encrypted_bytes = bytes.fromhex(encrypted_hex)
            
            # Desencriptar usando AES-ECB
            cipher = AES.new(key[:16], AES.MODE_ECB)  # Usar solo los primeros 16 bytes
            decrypted = cipher.decrypt(encrypted_bytes)
            
            # Remover padding PKCS7
            decrypted = unpad(decrypted, AES.block_size)
            
            # Decodificar a string UTF-8
            return decrypted.decode('utf-8', errors='ignore').rstrip('\x00')
        except Exception as e:
            # Si falla la desencriptación, devolver el valor original
            print(f"[DEBUG] No se pudo desencriptar credential: {e}")
            return encrypted_hex
    
    def _extract_wifi_allwan(self) -> Dict[str, Any]:
        """Extrae información WiFi desde get_allwan_info_broadBand (método preferido - sin encriptar)"""
        try:
            response = self._ajax_get('get_allwan_info_broadBand')
            
            if not response or response.get('session_valid') != 1:
                return None
            
            wifi_info = {}
            wifi_obj = response.get('wifi_obj_enable', {})
            
            # Extraer SSIDs configurados
            # ssid1-4: 2.4GHz, ssid5-8: 5GHz (típicamente)
            ssids_24ghz = []
            ssids_5ghz = []
            
            for i in range(1, 9):
                ssid_key = f'ssid{i}'
                config_key = f'ConfigActive{i}'
                
                ssid = wifi_obj.get(ssid_key, '')
                active = wifi_obj.get(config_key, '0')
                
                if ssid and ssid != '':
                    wifi_entry = {
                        'ssid': ssid,
                        'enabled': active == '1',
                        'index': i
                    }
                    
                    # ssid1-4 típicamente son 2.4GHz, ssid5-8 son 5GHz
                    if i <= 4:
                        ssids_24ghz.append(wifi_entry)
                    else:
                        ssids_5ghz.append(wifi_entry)
            
            # Usar el primer SSID activo de cada banda
            if ssids_24ghz:
                primary_24 = next((s for s in ssids_24ghz if s['enabled']), ssids_24ghz[0])
                wifi_info['ssid_24ghz'] = primary_24['ssid']
                wifi_info['enabled_24ghz'] = primary_24['enabled']
            
            if ssids_5ghz:
                primary_5 = next((s for s in ssids_5ghz if s['enabled']), ssids_5ghz[0])
                wifi_info['ssid_5ghz'] = primary_5['ssid']
                wifi_info['enabled_5ghz'] = primary_5['enabled']
            
            wifi_info['wifi_5g_capable'] = response.get('wifi_5g_enable') == 1
            wifi_info['wifi_device_count'] = response.get('wifi_device', 0)
            wifi_info['wifi_port_num'] = response.get('wifi_port_num', 0)
            wifi_info['extraction_method'] = 'get_allwan_info_broadBand'
            
            return wifi_info
            
        except Exception as e:
            print(f"[DEBUG] Error extrayendo WiFi desde get_allwan_info_broadBand: {e}")
            return None
    
    def _extract_wifi_info(self) -> Dict[str, Any]:
        """Extrae información WiFi completa (SSIDs, passwords, canales) usando endpoints específicos (fallback)"""
        wifi_info = {}
        
        if not self.session_id:
            print("[DEBUG] No hay sessionid, no se puede obtener info WiFi")
            return wifi_info
        
        # Intentar get_wifi_info para WiFi 2.4GHz
        try:
            wifi_24_response = self._ajax_get('get_wifi_info')
            if wifi_24_response.get('session_valid') == 1:
                if wifi_24_response.get('SSID'):
                    wifi_info['ssid_24ghz'] = wifi_24_response['SSID']
                if wifi_24_response.get('PreSharedKey'):
                    wifi_info['password_24ghz'] = wifi_24_response['PreSharedKey']
                if wifi_24_response.get('Channel'):
                    wifi_info['channel_24ghz'] = wifi_24_response['Channel']
                if wifi_24_response.get('Enable'):
                    wifi_info['enabled_24ghz'] = wifi_24_response['Enable'] == '1'
        except Exception as e:
            print(f"[DEBUG] Error obteniendo WiFi 2.4GHz: {e}")
        
        # Intentar get_5g_wifi_info para WiFi 5GHz
        try:
            wifi_5g_response = self._ajax_get('get_5g_wifi_info')
            if wifi_5g_response.get('session_valid') == 1:
                if wifi_5g_response.get('SSID'):
                    wifi_info['ssid_5ghz'] = wifi_5g_response['SSID']
                if wifi_5g_response.get('PreSharedKey'):
                    wifi_info['password_5ghz'] = wifi_5g_response['PreSharedKey']
                if wifi_5g_response.get('Channel'):
                    wifi_info['channel_5ghz'] = wifi_5g_response['Channel']
                if wifi_5g_response.get('Enable'):
                    wifi_info['enabled_5ghz'] = wifi_5g_response['Enable'] == '1'
        except Exception as e:
            print(f"[DEBUG] Error obteniendo WiFi 5GHz: {e}")
        
        # get_wifi_status devuelve array con todas las redes WiFi
        try:
            wifi_status = self._ajax_get('get_wifi_status')
            if wifi_status.get('session_valid') == 1 and wifi_status.get('wifi_status'):
                wifi_networks = wifi_status['wifi_status']
                
                for network in wifi_networks:
                    # Solo procesar redes habilitadas
                    if network.get('Enable') != '1':
                        continue
                    
                    # Detectar si es 2.4GHz o 5GHz por el standard
                    standard = network.get('Standard', '').lower()
                    is_5ghz = 'ac' in standard or 'ax' in standard or 'a' == standard
                    
                    # Extraer y desencriptar SSID
                    ssid_encrypted = network.get('SSID', '')
                    ssid_decrypted = self._decrypt_wifi_credential(ssid_encrypted) if ssid_encrypted else 'N/A'
                    
                    # Extraer y desencriptar password
                    psk_encrypted = network.get('PreSharedKey', '')
                    psk_decrypted = self._decrypt_wifi_credential(psk_encrypted) if psk_encrypted else 'N/A'
                    
                    # Canal en uso
                    channel = network.get('channelIsInUse', network.get('Channel', 'Auto'))
                    
                    # Asignar a la banda correcta
                    if is_5ghz:
                        if 'ssid_5ghz' not in wifi_info:  # Solo la primera red 5GHz activa
                            wifi_info['ssid_5ghz'] = ssid_decrypted
                            wifi_info['password_5ghz'] = psk_decrypted
                            wifi_info['channel_5ghz'] = channel
                            wifi_info['enabled_5ghz'] = True
                            wifi_info['standard_5ghz'] = network.get('Standard')
                    else:
                        if 'ssid_24ghz' not in wifi_info:  # Solo la primera red 2.4GHz activa
                            wifi_info['ssid_24ghz'] = ssid_decrypted
                            wifi_info['password_24ghz'] = psk_decrypted
                            wifi_info['channel_24ghz'] = channel
                            wifi_info['enabled_24ghz'] = True
                            wifi_info['standard_24ghz'] = network.get('Standard')
        except Exception as e:
            print(f"[DEBUG] Error obteniendo WiFi status: {e}")
        
        return wifi_info
    
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
            "MOD002": "F670L",
            "MOD004": "HG8145V5",
            "MOD005": "HG8145V5 SMALL",
            "MOD006": "HT818"
        }
        
        return display_names.get(model_code, reported_name or model_code)
    
    def test_pwd_pass(self) -> Dict[str, Any]:
        """Test 1: Autenticacion y obtencion de serial number"""
        print("[TEST] PWD PASS - Autenticacion")
        
        result = {
            "name": "PWD_PASS",
            "status": "FAIL",
            "details": {}
        }
        
        if not self.authenticated:
            result["details"]["error"] = "No autenticado"
            return result
        
        # Detectar tipo de dispositivo
        device_type = self.test_results['metadata'].get('device_type', 'ONT')
        
        if device_type == "ATA":
            # Dispositivos ATA (Grandstream): usar MAC/pseudo-SN si está disponible
            serial_from_metadata = self.test_results['metadata'].get('serial_number')
            mac_address = self.test_results['metadata'].get('mac_address')
            
            if serial_from_metadata:
                result["status"] = "PASS"
                result["details"]["serial_number"] = serial_from_metadata
                result["details"]["source"] = self.test_results['metadata'].get('serial_number_source', 'extracted')
                
                if mac_address:
                    result["details"]["mac_address"] = mac_address
                    
                result["details"]["note"] = "HT818 no expone SN por API. SN derivado de MAC o manual."
                print(f"[TEST] Serial/MAC encontrado: {serial_from_metadata}")
            else:
                result["details"]["error"] = "No se pudo obtener serial number o MAC"
                result["details"]["recommendation"] = "Etiquetar dispositivo con SN físico manualmente"
        else:
            # Dispositivos ONT: usar metodo AJAX get_operator
            operator_info = self._ajax_get('get_operator')
            
            if operator_info.get('SerialNumber'):
                result["status"] = "PASS"
                result["details"]["serial_number"] = operator_info['SerialNumber']
                result["details"]["operator"] = operator_info.get('operator_name', 'Unknown')
                result["details"]["method"] = "AJAX get_operator"
            else:
                result["details"]["error"] = "No se pudo obtener serial number"
        
        return result
    
    def test_factory_reset(self) -> Dict[str, Any]:
        """Test 2: Verificar capacidad de factory reset (no destructivo)"""
        print("[TEST] FACTORY RESET - Verificacion")
        
        result = {
            "name": "FACTORY_RESET_PASS",
            "status": "SKIP",
            "details": {"reason": "Test no destructivo - requiere verificacion manual"}
        }
        
        return result
    
    def test_usb_port(self) -> Dict[str, Any]:
        """Test 3: Deteccion de puerto USB"""
        print("[TEST] USB PORT - Deteccion")
        
        result = {
            "name": "USB_PORT",
            "status": "FAIL",
            "details": {}
        }
        
        # Verificar capacidades desde get_base_info
        base_info = self.test_results['metadata'].get('base_info')
        if base_info:
            usb_ports = base_info.get('usb_ports', 0)
            usb_status = base_info.get('usb_status')
            
            if usb_ports > 0:
                result["status"] = "PASS"
                result["details"]["method"] = "AJAX get_base_info"
                result["details"]["usb_ports_detected"] = usb_ports
                result["details"]["hardware_capability"] = f"{usb_ports} puerto(s) USB"
                
                if usb_status:
                    result["details"]["usb_status"] = usb_status
                    result["details"]["note"] = f"Estado: {usb_status}"
                    
                return result
        
        # Si no hay base_info, el test falla
        result["details"]["error"] = "No se pudo obtener información de hardware"
        result["details"]["note"] = "get_base_info no disponible"
        
        return result
        
        # Si no hay base_info, el test falla
        result["details"]["error"] = "No se pudo obtener información de hardware"
        result["details"]["note"] = "get_base_info no disponible"
        
        return result
    
    def test_software_version(self) -> Dict[str, Any]:
        """Test 4: Verificacion de version de software"""
        print("[TEST] SOFTWARE PASS - Version")
        
        result = {
            "name": "SOFTWARE_PASS",
            "status": "FAIL",
            "details": {}
        }
        
        # Prioridad 1: Usar get_base_info si está disponible (más completo)
        base_info = self.test_results['metadata'].get('base_info')
        if base_info:
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_base_info"
            
            if base_info.get('model_name'):
                result["details"]["model_name"] = base_info['model_name']
            if base_info.get('manufacturer'):
                result["details"]["manufacturer"] = base_info['manufacturer']
            if base_info.get('hardware_version'):
                result["details"]["hardware_version"] = base_info['hardware_version']
            if base_info.get('software_version'):
                result["details"]["software_version"] = base_info['software_version']
            if base_info.get('serial_number_logical'):
                result["details"]["serial_number"] = base_info['serial_number_logical']
            
            return result
        
        # Prioridad 2: Usar metodo AJAX get_device_name (fallback)
        device_info = self._ajax_get('get_device_name')
        
        if device_info.get('ModelName'):
            result["status"] = "PASS"
            result["details"]["model_name"] = device_info['ModelName']
            result["details"]["method"] = "AJAX get_device_name"
            
            # Intentar obtener mas info del operador
            operator_info = self._ajax_get('get_operator')
            if operator_info.get('operator_name'):
                result["details"]["operator"] = operator_info['operator_name']
                result["details"]["serial"] = operator_info.get('SerialNumber', 'Unknown')
        else:
            result["details"]["error"] = "No se pudo obtener informacion del dispositivo"
        
        return result
    
    def test_tx_power(self) -> Dict[str, Any]:
        """Test 5: Medicion de potencia de transmision optica"""
        print("[TEST] TX POWER - Potencia optica TX")
        
        result = {
            "name": "TX_POWER",
            "status": "FAIL",
            "details": {}
        }
        
        # Prioridad 1: Usar datos de get_base_info si están disponibles
        base_info = self.test_results['metadata'].get('base_info')
        if base_info and base_info.get('tx_power_dbm'):
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_base_info"
            result["details"]["tx_power_dbm"] = base_info['tx_power_dbm']
            result["details"]["note"] = "Datos obtenidos de get_base_info"
            return result
        
        # Prioridad 2: Intentar metodo AJAX get_pon_info
        pon_info = self._ajax_get('get_pon_info')
        
        if pon_info.get('session_valid') == 1:
            # Tiene datos validos
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_pon_info"
            result["details"]["data"] = pon_info
        elif pon_info.get('session_valid') == 0:
            result["details"]["error"] = "Requiere session valida (login completo)"
            result["details"]["note"] = "Basic Auth insuficiente - necesita do_login"
        else:
            result["details"]["error"] = "Metodo no accesible"
        
        return result
    
    def test_rx_power(self) -> Dict[str, Any]:
        """Test 6: Medicion de potencia de recepcion optica"""
        print("[TEST] RX POWER - Potencia optica RX")
        
        result = {
            "name": "RX_POWER",
            "status": "FAIL",
            "details": {}
        }
        
        # Prioridad 1: Usar datos de get_base_info si están disponibles
        base_info = self.test_results['metadata'].get('base_info')
        if base_info and base_info.get('rx_power_dbm'):
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_base_info"
            result["details"]["rx_power_dbm"] = base_info['rx_power_dbm']
            result["details"]["note"] = "Datos obtenidos de get_base_info"
            return result
        
        # Prioridad 2: Usa el mismo metodo que TX (get_pon_info devuelve ambos)
        pon_info = self._ajax_get('get_pon_info')
        
        if pon_info.get('session_valid') == 1:
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_pon_info"
            result["details"]["data"] = pon_info
        elif pon_info.get('session_valid') == 0:
            result["details"]["error"] = "Requiere session valida (login completo)"
            result["details"]["note"] = "Basic Auth insuficiente - necesita do_login"
        else:
            result["details"]["error"] = "Metodo no accesible"
        
        return result
    
    def test_wifi_24ghz(self) -> Dict[str, Any]:
        """Test 7: Validacion de WiFi 2.4 GHz"""
        print("[TEST] WiFi 2.4 GHz - Verificacion")
        
        result = {
            "name": "WIFI_24GHZ",
            "status": "FAIL",
            "details": {}
        }
        
        # Prioridad 1: Usar datos de get_base_info si están disponibles
        base_info = self.test_results['metadata'].get('base_info')
        if base_info and base_info.get('wifi_info'):
            wifi_info = base_info['wifi_info']
            if 'ssid_24ghz' in wifi_info:
                result["status"] = "PASS"
                result["details"]["method"] = "AJAX get_base_info"
                result["details"]["ssid"] = wifi_info.get('ssid_24ghz')
                result["details"]["password"] = wifi_info.get('password_24ghz', 'N/A')
                result["details"]["channel"] = wifi_info.get('channel_24ghz', 'N/A')
                result["details"]["enabled"] = wifi_info.get('enabled_24ghz', False)
                return result
        
        # Prioridad 2: Intentar metodo AJAX get_wifi_status
        wifi_status = self._ajax_get('get_wifi_status')
        
        if wifi_status.get('session_valid') == 1:
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_wifi_status"
            result["details"]["data"] = wifi_status
        elif wifi_status.get('session_valid') == 0:
            result["details"]["error"] = "Requiere session valida (login completo)"
            result["details"]["note"] = "Basic Auth insuficiente - necesita do_login"
        else:
            result["details"]["error"] = "Metodo no accesible"
        
        return result
    
    def test_wifi_5ghz(self) -> Dict[str, Any]:
        """Test 8: Validacion de WiFi 5 GHz"""
        print("[TEST] WiFi 5.0 GHz - Verificacion")
        
        result = {
            "name": "WIFI_5GHZ",
            "status": "FAIL",
            "details": {}
        }
        
        # Prioridad 1: Usar datos de get_base_info si están disponibles
        base_info = self.test_results['metadata'].get('base_info')
        if base_info and base_info.get('wifi_info'):
            wifi_info = base_info['wifi_info']
            if 'ssid_5ghz' in wifi_info:
                result["status"] = "PASS"
                result["details"]["method"] = "AJAX get_base_info"
                result["details"]["ssid"] = wifi_info.get('ssid_5ghz')
                result["details"]["password"] = wifi_info.get('password_5ghz', 'N/A')
                result["details"]["channel"] = wifi_info.get('channel_5ghz', 'N/A')
                result["details"]["enabled"] = wifi_info.get('enabled_5ghz', False)
                return result
        
        # Prioridad 2: Usa el mismo metodo que 2.4GHz (get_wifi_status devuelve ambas bandas)
        wifi_status = self._ajax_get('get_wifi_status')
        
        if wifi_status.get('session_valid') == 1:
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_wifi_status"
            result["details"]["data"] = wifi_status
        elif wifi_status.get('session_valid') == 0:
            result["details"]["error"] = "Requiere session valida (login completo)"
            result["details"]["note"] = "Basic Auth insuficiente - necesita do_login"
        else:
            result["details"]["error"] = "Metodo no accesible"
        
        return result
    
    # ==================== GRANDSTREAM HT818 SPECIFIC TESTS ====================
    
    def test_voip_lines(self) -> Dict[str, Any]:
        """Test específico para HT818: Estado de líneas VoIP"""
        print("[TEST] VOIP LINES - Estado de líneas telefónicas")
        
        result = {
            "name": "VOIP_LINES",
            "status": "SKIP",
            "details": {"reason": "Solo aplicable a dispositivos ATA"}
        }
        
        if self.test_results['metadata'].get('device_type') != "ATA":
            return result
        
        result["status"] = "PASS"
        result["details"] = {
            "device_type": "ATA",
            "test_applicable": True,
            "note": "Test ejecutado - verificar líneas FXS manualmente"
        }
        
        # Intentar obtener información de líneas
        endpoints_to_try = [
            '/cgi-bin/api-get_line_status',
            '/status.html'
        ]
        
        for endpoint in endpoints_to_try:
            try:
                response = self.session.get(
                    f"{self.base_url}{endpoint}",
                    auth=('admin', 'admin'),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200:
                    result["details"][f"endpoint_{endpoint}"] = "accessible"
                    
                    # Buscar información de líneas en el HTML
                    html = response.text.lower()
                    if 'line 1' in html or 'fxs 1' in html:
                        result["details"]["lines_detected"] = True
                        result["details"]["method"] = endpoint
            except Exception as e:
                result["details"][f"endpoint_{endpoint}_error"] = str(e)
        
        return result
    
    def test_sip_registration(self) -> Dict[str, Any]:
        """Test específico para HT818: Estado de registro SIP"""
        print("[TEST] SIP REGISTRATION - Estado de registro SIP")
        
        result = {
            "name": "SIP_REGISTRATION",
            "status": "SKIP",
            "details": {"reason": "Solo aplicable a dispositivos ATA"}
        }
        
        if self.test_results['metadata'].get('device_type') != "ATA":
            return result
        
        # Verificar puerto SIP
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sip_result = sock.connect_ex((self.host, 5060))
            sock.close()
            
            if sip_result == 0:
                result["status"] = "PASS"
                result["details"]["sip_port_5060"] = "open"
                result["details"]["note"] = "Puerto SIP accesible - verificar registro en servidor VoIP"
            else:
                result["status"] = "FAIL"
                result["details"]["sip_port_5060"] = "closed"
                result["details"]["error"] = "Puerto SIP no accesible"
        except Exception as e:
            result["status"] = "FAIL"
            result["details"]["error"] = str(e)
        
        return result
    
    def test_network_settings(self) -> Dict[str, Any]:
        """Test específico para HT818: Configuración de red"""
        print("[TEST] NETWORK SETTINGS - Configuración de red")
        
        result = {
            "name": "NETWORK_SETTINGS",
            "status": "FAIL",
            "details": {}
        }
        
        if self.test_results['metadata'].get('device_type') != "ATA":
            result["status"] = "SKIP"
            result["details"]["reason"] = "Solo aplicable a dispositivos ATA"
            return result
        
        # Intentar obtener configuración de red
        try:
            response = self.session.get(
                f"{self.base_url}/cgi-bin/api-get_network_info",
                auth=('admin', 'admin'),
                timeout=3,
                verify=False
            )
            
            if response.status_code == 200:
                result["status"] = "PASS"
                result["details"]["method"] = "api-get_network_info"
                
                # Intentar parsear respuesta
                try:
                    data = response.json()
                    result["details"]["network_info"] = data
                except:
                    # Si no es JSON, buscar patrones en texto
                    text = response.text
                    
                    ip_match = re.search(r'IP[:\s]+(\d+\.\d+\.\d+\.\d+)', text, re.IGNORECASE)
                    if ip_match:
                        result["details"]["ip_address"] = ip_match.group(1)
                    
                    mask_match = re.search(r'Mask[:\s]+(\d+\.\d+\.\d+\.\d+)', text, re.IGNORECASE)
                    if mask_match:
                        result["details"]["subnet_mask"] = mask_match.group(1)
                    
                    gateway_match = re.search(r'Gateway[:\s]+(\d+\.\d+\.\d+\.\d+)', text, re.IGNORECASE)
                    if gateway_match:
                        result["details"]["gateway"] = gateway_match.group(1)
            else:
                result["details"]["error"] = f"HTTP {response.status_code}"
        except Exception as e:
            result["details"]["error"] = str(e)
        
        # Si falló el método anterior, intentar con metadata
        if result["status"] == "FAIL" and self.test_results['metadata']:
            meta = self.test_results['metadata']
            if meta.get('ip_address'):
                result["status"] = "PASS"
                result["details"]["ip_address"] = meta['ip_address']
                result["details"]["method"] = "metadata"
                result["details"]["note"] = "Información de red obtenida de metadata del dispositivo"
        
        return result
    
    # ==================== NETWORK CONNECTIVITY TESTS ====================
    
    def test_ping_connectivity(self) -> Dict[str, Any]:
        """RF 002: Test de ping al ONT"""
        print("[TEST] CONNECTIVITY - Ping")
        
        result = {
            "name": "PING_CONNECTIVITY",
            "status": "FAIL",
            "details": {}
        }
        
        is_windows = platform.system() == "Windows"
        param = "-n" if is_windows else "-c"
        timeout_param = "-w" if is_windows else "-W"
        
        try:
            cmd = ["ping", param, "4", timeout_param, "2000", self.host]
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if output.returncode == 0:
                result["status"] = "PASS"
                result["details"]["reachable"] = True
                
                # Parsear latencia en Windows
                if is_windows:
                    latency_match = re.search(r'Media = (\d+)ms', output.stdout)
                    if latency_match:
                        result["details"]["avg_latency_ms"] = int(latency_match.group(1))
                    else:
                        # Buscar tiempo= o time=
                        times = re.findall(r'tiempo[=<](\d+)ms|time[=<](\d+)ms', output.stdout, re.IGNORECASE)
                        if times:
                            latencies = [int(t[0] or t[1]) for t in times]
                            result["details"]["avg_latency_ms"] = sum(latencies) // len(latencies)
            else:
                result["details"]["reachable"] = False
                result["details"]["error"] = "Host no alcanzable"
        except Exception as e:
            result["details"]["error"] = str(e)
        
        return result
    
    def test_http_connectivity(self) -> Dict[str, Any]:
        """RF 002: Test de conectividad HTTP"""
        print("[TEST] CONNECTIVITY - HTTP")
        
        result = {
            "name": "HTTP_CONNECTIVITY",
            "status": "FAIL",
            "details": {}
        }
        
        try:
            start = time.time()
            response = requests.get(
                self.base_url,
                timeout=5,
                verify=False,
                auth=('root', 'admin')
            )
            elapsed_ms = (time.time() - start) * 1000
            
            result["status"] = "PASS"
            result["details"]["http_accessible"] = True
            result["details"]["response_time_ms"] = round(elapsed_ms, 2)
            result["details"]["status_code"] = response.status_code
        except Exception as e:
            result["details"]["error"] = str(e)
        
        return result
    
    def test_port_scan(self) -> Dict[str, Any]:
        """RF 004: Test de escaneo de puertos"""
        print("[TEST] CONNECTIVITY - Port Scan")
        
        result = {
            "name": "PORT_SCAN",
            "status": "PASS",
            "details": {"ports": {}}
        }
        
        common_ports = [80, 443, 22, 23, 8080]
        
        for port in common_ports:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                
                start = time.time()
                result_code = sock.connect_ex((self.host, port))
                elapsed_ms = (time.time() - start) * 1000
                
                sock.close()
                
                port_open = (result_code == 0)
                result["details"]["ports"][port] = {
                    "open": port_open,
                    "response_time_ms": round(elapsed_ms, 2) if port_open else None
                }
            except Exception as e:
                result["details"]["ports"][port] = {
                    "open": False,
                    "error": str(e)
                }
        
        return result
    
    def test_dns_resolution(self) -> Dict[str, Any]:
        """RF 003: Test de resolución DNS"""
        print("[TEST] CONNECTIVITY - DNS Resolution")
        
        result = {
            "name": "DNS_RESOLUTION",
            "status": "FAIL",
            "details": {"resolved_hosts": []}
        }
        
        test_domains = ["google.com", "cloudflare.com"]
        success_count = 0
        
        for domain in test_domains:
            try:
                ip = socket.gethostbyname(domain)
                result["details"]["resolved_hosts"].append({
                    "domain": domain,
                    "ip": ip,
                    "success": True
                })
                success_count += 1
            except socket.gaierror:
                result["details"]["resolved_hosts"].append({
                    "domain": domain,
                    "success": False
                })
        
        if success_count > 0:
            result["status"] = "PASS"
            result["details"]["dns_working"] = True
        
        return result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todos los tests automatizados"""
        print("\n" + "="*60)
        print("ONT/ATA AUTOMATED TEST SUITE")
        print(f"Host: {self.host}")
        if self.model:
            print(f"Modelo especificado: {self.model}")
        print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Intentar login primero (obtiene serial y model name, auto-detecta modelo)
        if not self.login():
            print("[!] Error: No se pudo autenticar")
            return self.test_results
        
        # Determinar qué tests ejecutar según el tipo de dispositivo
        device_type = self.test_results['metadata'].get('device_type', 'ONT')
        
        # Tests comunes a todos los dispositivos
        common_tests = [
            self.test_pwd_pass,
            self.test_factory_reset,
            self.test_ping_connectivity,
            self.test_http_connectivity,
            self.test_port_scan,
            self.test_dns_resolution,
            self.test_software_version,
        ]
        
        # Tests específicos de ONT
        ont_tests = [
            self.test_usb_port,
            self.test_tx_power,
            self.test_rx_power,
            self.test_wifi_24ghz,
            self.test_wifi_5ghz
        ]
        
        # Tests específicos de ATA (Grandstream HT818)
        ata_tests = [
            self.test_voip_lines,
            self.test_sip_registration,
            self.test_network_settings
        ]
        
        # Ejecutar tests comunes
        print(f"\n[*] Ejecutando tests comunes ({len(common_tests)} tests)...")
        for test_func in common_tests:
            result = test_func()
            self.test_results["tests"][result["name"]] = result
        
        # Ejecutar tests específicos según el tipo
        if device_type == "ATA":
            print(f"\n[*] Dispositivo ATA detectado - Ejecutando tests VoIP ({len(ata_tests)} tests)...")
            for test_func in ata_tests:
                result = test_func()
                self.test_results["tests"][result["name"]] = result
        else:
            print(f"\n[*] Dispositivo ONT detectado - Ejecutando tests fibra óptica ({len(ont_tests)} tests)...")
            for test_func in ont_tests:
                result = test_func()
                self.test_results["tests"][result["name"]] = result
        
        return self.test_results
    
    def generate_report(self) -> str:
        """Genera reporte en formato texto"""
        lines = []
        
        # Obtener información del dispositivo
        # Usar model_display_name si está disponible (nombre comercial correcto)
        device_name = self.test_results['metadata'].get('model_display_name') or \
                     self.test_results['metadata'].get('device_name', 'Unknown')
        device_type = self.test_results['metadata'].get('device_type', 'ONT')
        mac_address = self.test_results['metadata'].get('mac_address', 'No disponible')
        serial_number = self.test_results['metadata'].get('serial_number', 'No disponible')
        
        # Para MOD001-005 (ONTs), mostrar SN físico/PON calculado (todo en hexadecimal)
        if device_type == "ONT" and self.model and self.model.startswith("MOD00") and self.model <= "MOD005":
            serial_physical = self.test_results['metadata'].get('serial_number_physical')
            if serial_physical:
                serial_number = serial_physical
        
        lines.append("="*60)
        lines.append(f"REPORTE DE PRUEBAS AUTOMATIZADAS - {device_type}")
        lines.append("="*60)
        lines.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Modelo: {device_name} ({self.model})")
        lines.append(f"Host: {self.host}")
        lines.append(f"MAC Address: {mac_address}")
        lines.append(f"Serie: {serial_number}")
        lines.append("")
        lines.append("RESULTADOS:")
        lines.append("-"*60)
        
        pass_count = 0
        fail_count = 0
        skip_count = 0
        
        for test_name, test_data in self.test_results["tests"].items():
            status = test_data["status"]
            symbol = "[OK]" if status == "PASS" else "[X]" if status == "FAIL" else "[-]"
            lines.append(f"{symbol} {test_name}: {status}")
            
            if status == "PASS":
                pass_count += 1
            elif status == "FAIL":
                fail_count += 1
            else:
                skip_count += 1
        
        lines.append("")
        lines.append("-"*60)
        lines.append(f"RESUMEN: {pass_count} PASS | {fail_count} FAIL | {skip_count} SKIP")
        lines.append("="*60)
        
        return "\n".join(lines)
    
    def save_results(self, output_dir: str = None):
        """Guarda los resultados en archivos organizados por fecha"""
        timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
        date_folder = datetime.now().strftime("%d_%m_%y")
        
        # Determinar si es dispositivo empresarial
        device_type = self.test_results['metadata'].get('device_type', 'ONT')
        is_enterprise = device_type in ['ATA', 'ROUTER', 'SWITCH']
        
        # Agregar sufijo _emp para dispositivos empresariales
        if is_enterprise:
            date_folder = f"{date_folder}_emp"
        
        if output_dir is None:
            base_dir = Path(__file__).parent.parent / "reports" / "automated_tests"
            output_dir = base_dir / date_folder
        else:
            output_dir = Path(output_dir) / date_folder
        
        # Crear directorio por fecha si no existe
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar JSON
        json_file = output_dir / f"{timestamp}_{self.model}_automated_results.json"
        with open(json_file, "w") as f:
            json.dump(self.test_results, f, indent=2)
        
        # Guardar reporte de texto
        txt_file = output_dir / f"{timestamp}_{self.model}_automated_report.txt"
        with open(txt_file, "w") as f:
            f.write(self.generate_report())
        
        print(f"\n[+] Resultados guardados en:")
        print(f"    - JSON: {json_file}")
        print(f"    - TXT: {txt_file}")

def main():
    parser = argparse.ArgumentParser(description="ONT Automated Test Suite")
    parser.add_argument("--host", required=True, help="IP de la ONT")
    parser.add_argument("--model", help="Modelo de la ONT (opcional, se detecta automaticamente)")
    parser.add_argument("--output", help="Directorio de salida (opcional)")
    parser.add_argument("--mode", 
                       choices=['test', 'retest', 'label'], 
                       default='test',
                       help="Modo de operacion: test (todos), retest (solo fallidos), label (generar etiqueta)")
    
    args = parser.parse_args()
    
    if args.mode == 'label':
        # Modo label: generar etiqueta de identificación
        generate_label(args.host, args.model)
    elif args.mode == 'retest':
        # Modo retest: solo tests fallidos
        run_retest_mode(args.host, args.model, args.output)
    else:
        # Modo test: todos los tests
        tester = ONTAutomatedTester(args.host, args.model)
        tester.run_all_tests()
        
        # Mostrar reporte en consola
        print("\n" + tester.generate_report())
        
        # Guardar resultados
        tester.save_results(args.output)

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

if __name__ == "__main__":
    main()
