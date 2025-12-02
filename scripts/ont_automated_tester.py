#!/usr/bin/env python3
"""
ONT Automated Test Suite
Pruebas automatizadas basadas en protocolo de testing
Fecha: 10/11/2025
"""

import argparse
import json
import os
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
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from urllib.parse import urljoin
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

class ONTAutomatedTester:
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
        
        self.test_results = {
            "metadata": {
                "host": host,
                "model": model,
                "timestamp": datetime.now().isoformat(),
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
            return {" success": False, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
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
    
    def _show_network_setup_guide(self, missing_networks):
        """Muestra instrucciones para configurar IP secundaria"""
        print("\n" + "="*70)
        print("⚠️  CONFIGURACIÓN DE RED REQUERIDA")
        print("="*70)
        print("\nPara detectar automáticamente TODOS los modelos de ONT, el adaptador")
        print("Ethernet DEBE tener IPs estáticas configuradas en múltiples redes:\n")
        
        for network, description in missing_networks:
            print(f"  • {network}.x - Para {description}")
        
        print("\n" + "-"*70)
        print("📋 CONFIGURACIÓN COMPLETA (Una vez):")
        print("-"*70)
        print("\n1. Ve a: Panel de Control > Redes e Internet > Conexiones de red")
        print("2. Click derecho en 'Ethernet' > Propiedades")
        print("3. Selecciona 'Protocolo de Internet versión 4 (TCP/IPv4)' > Propiedades")
        print("4. Marca 'Usar la siguiente dirección IP'")
        print("\n5. Configura la IP PRINCIPAL:\n")
        print("   ┌─────────────────────────────────────┐")
        print("   │ Dirección IP:     192.168.100.15   │")
        print("   │ Máscara subred:   255.255.255.0    │")
        print("   │ Puerta enlace:    (dejar vacío)    │")
        print("   └─────────────────────────────────────┘")
        print("\n6. Click en 'Opciones avanzadas...'")
        print("7. En 'Configuración IP', click 'Agregar...' para IP SECUNDARIA:\n")
        print("   ┌─────────────────────────────────────┐")
        print("   │ IP:      192.168.1.15               │")
        print("   │ Máscara: 255.255.255.0              │")
        print("   └─────────────────────────────────────┘")
        print("\n8. Click 'Aceptar' en todas las ventanas")
        print("9. Vuelve a ejecutar este script")
        
        print("\n" + "="*70)
        print("💡 IMPORTANTE: Sin IPs estáticas, el adaptador queda en 169.254.x.x")
        print("   (auto-asignación) y NO podrá comunicarse con ningún ONT.")
        print("\n💡 Con ambas IPs configuradas, detectará automáticamente CUALQUIER")
        print("   modelo (Huawei, Fiberhome, ZTE) sin cambios manuales.")
        print("="*70 + "\n")
    
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
        elif device_type == "FIBERHOME" or self.model == "MOD001":
            return self._login_fiberhome()  # Fiberhome usa Selenium
        elif device_type == "ZTE" or self.model == "MOD002":
            return self._login_zte(False) # False para indicar que aun no se ha reseteado
        elif device_type == "HUAWEI" or self.model in ["MOD003", "MOD004", "MOD005"]:
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
            
            html = response.text.lower()
            server = response.headers.get('Server', '').lower()
            
            # Detectar Grandstream
            if 'grandstream' in html or 'grandstream' in server or 'ht818' in html:
                return "GRANDSTREAM"
            
            # Detectar Fiberhome (buscar elementos específicos)
            if any(keyword in html for keyword in ['fiberhome', 'hg6145f', 'user_name', 'loginpp', 'fh-text-security']):
                print("[AUTH] Dispositivo Fiberhome detectado automáticamente")
                if not self.model:
                    self.model = "MOD001"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "FIBERHOME"
            
            # Detectar Huawei (buscar elementos específicos en el HTML)
            if any(keyword in html for keyword in ['huawei', 'hg8145', 'echolife', 'txt_username', 'txt_password']):
                print("[AUTH] Dispositivo Huawei detectado automáticamente")
                # Intentar detectar modelo específico
                if not self.model:
                    if 'hg8145v5' in html:
                        if 'small' in html:
                            self.model = "MOD005"
                        else:
                            self.model = "MOD004"
                    elif 'hg8145x6' in html or 'hg6145f1' in html:
                        self.model = "MOD003"
                    else:
                        # Default to MOD004 for unknown Huawei
                        self.model = "MOD004"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "HUAWEI"
            
            # Detectar ZTE
            if any(keyword in html for keyword in ['zte', 'zxhn', 'f670l', 'frm_username', 'frm_password']):
                print("[AUTH] Dispositivo ZTE detectado automáticamente")
                if not self.model:
                    self.model = "MOD002"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "ZTE"
            
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
            password_field.send_keys('admin')
            
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
    
    # Funcion extrema para encontrar el boton de Status
    def find_status_link(self, driver, timeout=10):
        """
        Busca el <a id="statusMgr"> en el documento principal y en todos los frames.
        Devuelve el WebElement o None si no lo encuentra.
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            button_locators = [
            (By.ID, "statusMgr"),
            (By.CSS_SELECTOR, "a#statusMgr"),
            (By.CSS_SELECTOR, "a[menupage='statusMgr']"),
            (By.CSS_SELECTOR, "a[title='Status']"),
            (By.LINK_TEXT, "Status"),
        ]

        end_time = time.time() + timeout

        while time.time() < end_time:
            # 1) Documento principal
            driver.switch_to.default_content()
            for by, sel in button_locators:
                try:
                    el = driver.find_element(by, sel)
                    if el.is_displayed():
                        print(f"[SELENIUM] Status encontrado en documento principal con {by}='{sel}'")
                        return el
                except NoSuchElementException:
                    pass

            # 2) Buscar en cada frame
            frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
            for idx, frame in enumerate(frames):
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)
                for by, sel in button_locators:
                    try:
                        el = driver.find_element(by, sel)
                        if el.is_displayed():
                            print(f"[SELENIUM] Status encontrado en frame #{idx} con {by}='{sel}'")
                            return el
                    except NoSuchElementException:
                        continue

            time.sleep(0.5)

        return None

    def _login_zte(self, reset) -> bool:
        # funcion de inicio de sesión zte (ip diferente -> 192.168.1.1)
        # Este login / peticiones no se hacen mediante ajax ya que el modelo no lo soporta
        print("[DEBUG] El valor de reset recibido es: "+str(reset))
        # Vereficar selenium (prob se usará siemr}pre, es sencillo de usar)
        if SELENIUM_AVAILABLE:
            #Login con selenium, pero sin acceder a cookies
            driver = None
            headless = True
            timeout = 10
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
                chrome_options.add_argument(f'--host-resolver-rules=MAP {self.host} 192.168.1.1')
                chrome_options.page_load_strategy = "eager"  # <- No esperar recursos innecesarios, solo con el DOM principal
                
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
                    print(f"[ERROR] No se pudo cargar VAMOS A SEGUIR PARA ESTE MODELO {base_url}: {e} ")
                    # driver.quit()
                    # return False
                
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
                    (By.ID, 'Frm_Username'),        #ZTE
                    (By.NAME, 'Frm_Username'),      #ZTE
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
                    (By.ID, 'Frm_Password'),        #ZTE
                    (By.NAME, 'Frm_Password'),      #ZTE
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
                password_field.send_keys('admin')
                
                # Buscar y hacer clic en botón de login
                button_selectors = [
                    (By.ID, 'login_btn'),           # Fiberhome específico
                    (By.ID, 'LoginId'),             #ZTE
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
                    driver.execute_script("arguments[0].click();", login_button)
                    login_button.click()
                    print("[SELENIUM] Click en botón de login...")
                else:
                    # Si no hay botón, enviar formulario con Enter
                    print("[SELENIUM] Enviando formulario con Enter...")
                    from selenium.webdriver.common.keys import Keys
                    password_field.send_keys(Keys.RETURN)
                
                # Esperar a que cargue la página principal (varios indicadores posibles)
                time.sleep(5)  # Dar tiempo para procesar login

                if (reset is False):
                    # Antes de ejecutar las demás pruebas hay que resetear de fabrica
                    resetZTE = self._reset_factory_zte(driver)
                    print("[INFO] Esperando a que el ZTE reinicie tras Factory Reset...")
                    time.sleep(100)  # espera
                    if (resetZTE):
                        reset = True
                        self._login_zte(True) # Es necesario volver a loggearse después del reset
                        driver.quit()
                        return True
                    else:
                        print("[WARNING] No se pudo resetear, saltando pruebas")
                        driver.quit()
                        return False
                #Petición extra:
                # Utilizando selenium para darle click a un boton || Tactica extrema, no intentar en casa
                button_selectors = [
                    (By.ID, 'mgrAndDiag'),         # ZTE
                    (By.LINK_TEXT, "Management & Diagnosis")
                ]
                
                mgmt = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.LINK_TEXT, "Management & Diagnosis"))
                )
                mgmt.click()
                print("[SELENIUM] Click en Management & Diagnosis")
                
                time.sleep(3)

                # Debug EXTREMO
                # with open("zte_after_mgmt.html", "w", encoding="utf-8") as f:
                #     f.write(driver.page_source)
                # print("[DEBUG] HTML guardado como zte_after_mgmt.html")
                # 2) Ahora buscar el Status
                status = self.find_status_link(driver, timeout=10)
                if status is None:
                    raise RuntimeError("[SELENIUM] No se encontró el botón Status en ningún frame ni en el documento principal")

                # 3) Hacer click
                driver.switch_to.default_content()  # por si el elemento está en un frame, Selenium ya sabe su contexto
                status.click()
                print("[SELENIUM] Click en Status")

                # Hay que hacer click en todos los botones que llevan a los comandos 
                

                cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
                print("[SELENIUM] Cookies obtenidas:", cookies)

                # set cookies 
                # driver.quit()
                self.session.headers.update({
                    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/142.0.0.0 Safari/537.36"),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": "http://192.168.1.1/",
                    "Connection": "keep-alive",
                    "X-Requested-With": "XMLHttpRequest",
                })
                self.session.cookies.update(cookies)

                #Mandar a llamar a las peticiones desde aqui para no cerrar el driver

                self.zte_info(driver)
                # driver.get(xml_url)
                # raw = driver.page_source
                # start = raw.find("<ajax_response_xml_root")
                # end   = raw.rfind("</ajax_response_xml_root>") + len("</ajax_response_xml_root>")
                # xml = raw[start:end]
                # print(xml)
                
                driver.quit()
                return True
            except Exception as e:
                print(f"[ERROR] Selenium login falló: {type(e).__name__} - {e}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
                return False

    def _login_fiberhome(self) -> bool:
        """
        Login específico para Fiberhome usando Selenium.
        Soporta navegación a reset de fábrica y skip wizard.
        """
        if not SELENIUM_AVAILABLE:
            print("[ERROR] Selenium no está disponible para Fiberhome")
            return False

        driver = None
        headless = True
        try:
            print(f"[SELENIUM] Iniciando login Fiberhome a {self.host}...")
            
            # Configurar opciones de Chrome
            chrome_options = Options()
            if headless:
                chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--allow-insecure-localhost')
            
            # Evitar detección de automatización
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Deshabilitar guardado de contraseñas
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            }
            chrome_options.add_experimental_option("prefs", prefs)

            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Guardar referencia al driver
            self.driver = driver
            
            # 1. Navegar al login
            login_url = f"http://{self.host}/html/login_inter.html"
            print(f"[SELENIUM] Navegando a {login_url}...")
            driver.get(login_url)
            
            # Esperar a que cargue
            wait = WebDriverWait(driver, 10)
            
            # 2. Ingresar credenciales
            # Fiberhome suele usar 'user_name' y 'loginpp' o 'password'
            try:
                user_field = wait.until(EC.presence_of_element_located((By.ID, "user_name")))
                print("[SELENIUM] Campo username encontrado: id='user_name'")
                user_field.clear()
                user_field.send_keys('root')
                
                try:
                    pass_field = driver.find_element(By.ID, "loginpp")
                    print("[SELENIUM] Campo password encontrado: id='loginpp'")
                except:
                    pass_field = driver.find_element(By.ID, "password")
                    print("[SELENIUM] Campo password encontrado: id='password'")
                
                pass_field.clear()
                pass_field.send_keys('admin')
                
                # 3. Click Login
                # Intentar varios IDs comunes para el botón
                login_btn = None
                for btn_id in ["login_btn", "login", "LoginId"]:
                    try:
                        login_btn = driver.find_element(By.ID, btn_id)
                        print(f"[SELENIUM] Botón login encontrado: id='{btn_id}'")
                        break
                    except:
                        continue
                
                if login_btn:
                    login_btn.click()
                else:
                    print("[ERROR] No se encontró botón de login")
                    return False
                
            except TimeoutException:
                print("[ERROR] No se encontraron campos de login Fiberhome")
                return False
            
            # 4. Verificar login exitoso
            time.sleep(3)
            if "login_inter.html" not in driver.current_url:
                print("[AUTH] Login Fiberhome exitoso (URL cambió)")
                
                # Intentar saltar wizard si existe
                self.fh_maybe_skip_initial_guide(driver)
                
                # Obtener cookies para requests
                selenium_cookies = driver.get_cookies()
                for cookie in selenium_cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                
                return True
            else:
                print("[ERROR] Login fallido, seguimos en login page")
                return False
                
        except Exception as e:
            print(f"[ERROR] Excepción en login Fiberhome: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return False

    def fh_maybe_skip_initial_guide(self, driver):
        """Intenta saltar el wizard de configuración inicial de Fiberhome"""
        print("[SELENIUM] Verificando wizard inicial Fiberhome...")
        try:
            # Buscar botones comunes de "Next", "Skip", "Cancel" en iframes o main
            # Esto es especulativo ya que no tenemos info del wizard Fiberhome
            # Pero implementamos la estructura para agregarlo fácilmente
            pass
        except Exception as e:
            print(f"[DEBUG] Error verificando wizard: {e}")

    def _reset_factory_fiberhome(self):
        """
        Realiza reset de fábrica para Fiberhome.
        Ruta: Management -> Device Management -> Device Reboot -> Restore
        """
        print("[RESET] Iniciando Factory Reset Fiberhome...")
        if not self.driver:
            print("[ERROR] No hay driver de Selenium activo")
            return False
            
        driver = self.driver
        wait = WebDriverWait(driver, 10)
        
        try:
            # Asegurar que estamos en el frame correcto o main content
            driver.switch_to.default_content()
            
            # 1. Click en Management (Top Menu)
            print("[RESET] Buscando menú Management...")
            try:
                mgmt_link = self.find_element_anywhere(driver, By.XPATH, "//a[contains(text(), 'Management')]")
                if mgmt_link:
                    mgmt_link.click()
                    time.sleep(1)
                else:
                    print("[ERROR] No se encontró menú Management")
                    return False
            except Exception as e:
                print(f"[ERROR] Falló click en Management: {e}")
                return False
                
            # 2. Click en Device Management (Left Menu)
            print("[RESET] Buscando Device Management...")
            try:
                dev_mgmt = self.find_element_anywhere(driver, By.XPATH, "//a[contains(text(), 'Device Management')]")
                if dev_mgmt:
                    dev_mgmt.click()
                    time.sleep(1)
                else:
                    print("[ERROR] No se encontró Device Management")
                    return False
            except Exception as e:
                print(f"[ERROR] Falló click en Device Management: {e}")
                return False

            # 3. Click en Device Reboot / Restore (Sub Menu)
            print("[RESET] Buscando menú Restore/Reboot...")
            try:
                # Intentar "Restore" primero (según screenshot breadcrumb)
                restore_link = self.find_element_anywhere(driver, By.XPATH, "//a[contains(text(), 'Restore')]")
                if restore_link:
                    restore_link.click()
                else:
                    # Intentar "Device Reboot"
                    reboot_link = self.find_element_anywhere(driver, By.XPATH, "//a[contains(text(), 'Device Reboot')]")
                    if reboot_link:
                        reboot_link.click()
                    else:
                        print("[ERROR] No se encontró menú Restore ni Device Reboot")
                        return False
                time.sleep(1)
            except Exception as e:
                print(f"[ERROR] Falló navegación a Restore: {e}")
                return False
                
            # 4. Click en botón Restore
            print("[RESET] Buscando botón Restore...")
            try:
                # Buscar en frames porque el contenido suele estar en un iframe
                restore_btn = self.find_element_anywhere(driver, By.ID, "Restart_button")
                if not restore_btn:
                    # Intentar por value
                    restore_btn = self.find_element_anywhere(driver, By.XPATH, "//input[@value='Restore']")
                
                if restore_btn:
                    print("[RESET] Botón Restore encontrado, haciendo click...")
                    restore_btn.click()
                    
                    # 5. Confirmar alerta
                    try:
                        WebDriverWait(driver, 3).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        print(f"[RESET] Alerta detectada: {alert.text}")
                        alert.accept()
                        print("[RESET] Alerta aceptada. Reinicio en curso...")
                        return True
                    except TimeoutException:
                        print("[WARNING] No apareció alerta de confirmación, verificando si se reinició...")
                        return True
                else:
                    print("[ERROR] No se encontró el botón Restore")
                    return False
                    
            except Exception as e:
                print(f"[ERROR] Error al hacer click en Restore: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Excepción general en reset Fiberhome: {e}")
            return False

    def _login_huawei(self) -> bool:
        #  función de inicio de sesión para huawei
        if SELENIUM_AVAILABLE:
            #login con selenium
            driver = None
            headless = True
            timeout = 5

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
                chrome_options.page_load_strategy = "eager"  # <- No esperar recursos innecesarios, solo con el DOM principal
                
                # Deshabilitar warnings de certificado
                chrome_options.add_argument('--ignore-certificate-errors')
                chrome_options.add_argument('--allow-insecure-localhost')

                # Deshabilitar gestor de contraseñas y alertas de seguridad
                prefs = {
                    "credentials_enable_service": False,
                    "profile.password_manager_enabled": False,
                    "safebrowsing.enabled": False,
                    "profile.default_content_setting_values.notifications": 2
                }
                chrome_options.add_experimental_option("prefs", prefs)
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])

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
                    print(f"[ERROR] No se pudo cargar {base_url}: {e} ")
                    driver.quit()
                    return False

                # Esperar a que cargue la pagina
                time.sleep(2)
                # Verificar si la página cargó correctamente
                if "400" in driver.title or "error" in driver.page_source.lower()[:500]:
                    print("[ERROR] La página retornó error 400 - El router bloqueó la petición")
                    driver.quit()
                    return False
                
                # Esperar a que cargue el formulario
                wait = WebDriverWait(driver, timeout)

                # Buscar campos de login (intentar varios selectores comunes)
                username_selectors = [
                    (By.ID, 'user_name'),           # Fiberhome específico
                    (By.NAME, 'user_name'),         # Fiberhome específico
                    (By.ID, 'username'),
                    (By.ID, 'Frm_Username'),        #ZTE
                    (By.NAME, 'Frm_Username'),      #ZTE
                    (By.ID, 'txt_Username'),        #HUAWEI
                    (By.NAME, 'txt_Username'),      #HUAWEI
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
                    (By.ID, 'Frm_Password'),        #ZTE
                    (By.NAME, 'Frm_Password'),      #ZTE
                    (By.ID, 'txt_Password'),        #HUAWEI
                    (By.NAME, 'txt_Password'),      #HUAWEI
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

                username_fiel = None
                password_fiel = None

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
                    driver.quit()
                    return False

                # Ingresar credenciales
                print("[SELENIUM] Ingresando credenciales...")
                username_field.clear()
                username_field.send_keys('root')
                password_field.clear()
                password_field.send_keys('admin')

                # Pequeña pausa para que el JS termine de armar el DOM
                time.sleep(0.5)
                # Buscar y hacer clic en botón de login
                button_selectors = [
                    (By.ID, 'login_btn'),           # Fiberhome específico
                    (By.ID, 'LoginId'),             #ZTE
                    (By.ID, 'loginbutton'),         #HUAWEI
                    (By.NAME, 'login'),
                    (By.CSS_SELECTOR, 'button[type="submit"]'),
                    (By.CSS_SELECTOR, 'input[type="submit"]'),
                    (By.XPATH, '//button[contains(text(), "Login")]'),
                    (By.XPATH, '//button[contains(text(), "Entrar")]')
                ]

                # 4) Comprobar si realmente existe el botón en el HTML
                page_html = driver.page_source
                if 'id="loginbutton"' not in page_html and "loginbutton" not in page_html:
                    # Guardamos HTML para inspección
                    debug_path = Path("debug_huawei_login_notfound.html")
                    debug_path.write_text(page_html, encoding="utf-8")
                    print("[SELENIUM] No se encontró ningún 'loginbutton' en el HTML.")
                    print(f"[SELENIUM] HTML guardado en {debug_path}")
                    # return False

                # 5) Click al botón con JS directamente
                driver.execute_script("""
                    var btn = document.getElementById('loginbutton');
                    if (btn) { btn.click(); } else { console.log('loginbutton no encontrado'); }
                """)
                print("[SELENIUM] Click en botón login vía JS")

                # 6) Esperar a que cargue el menú principal
                try:
                    wait.until(
                        EC.presence_of_element_located((By.ID, "name_Systeminfo"))
                    )
                    print("[SELENIUM] Login HG8145V5 completado, menú System Information visible.")
                    # return True
                except TimeoutException:
                    print("[SELENIUM] WARNING: No apareció 'name_Systeminfo' tras login (puede que el login haya fallado).")
                    # Guardamos la pantalla resultante para revisar
                    after_path = Path("debug_huawei_after_login.html")
                    after_path.write_text(driver.page_source, encoding="utf-8")
                    print(f"[SELENIUM] HTML tras login guardado en {after_path}")
                    # return False

                # return True

                
                # Esperar a que cargue la página principal (varios indicadores posibles)
                time.sleep(5)  # Dar tiempo para procesar login
                cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
                print("[SELENIUM] Cookies obtenidas:", cookies)

                self.session.headers.update({
                    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/142.0.0.0 Safari/537.36"),
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": "http://192.168.1.1/",
                    "Connection": "keep-alive",
                    "X-Requested-With": "XMLHttpRequest",
                })
                self.session.cookies.update(cookies)

                # Antes de hacer la extraccion hay que confirmar si no es la primera vez conectando el Huawei
                salto = self.hw_maybe_skip_initial_guide(driver)
                if(salto):
                    print("[INFO] Se saltó la pagina de configuración inicial")
                    #hacer sesion otra vez
                    #temp_bool = self._login_huawei()
                else:
                    print("[INFO] No se saltó la página de configuración inicial o no se encontraron los skips")
                # Peticiones desde aqui para no cerrar el driver
                
                self.huawei_info(driver)

                driver.quit()
                return True
            except Exception as e:
                print(f"[ERROR] Selenium login falló: {type(e).__name__} - {e}")
                if driver:
                    try:
                        driver.quit()
                    except:
                        pass
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
        
        # Lógica específica para Fiberhome (MOD001)
        if self.model == "MOD001" or self.test_results['metadata'].get('device_type') == "FIBERHOME":
            print("[TEST] Ejecutando secuencia de Factory Reset para Fiberhome...")
            
            # Asegurar que tenemos driver de Selenium activo
            if not self.driver:
                print("[TEST] Driver no activo (login previo fue AJAX?). Iniciando login Fiberhome para obtener driver...")
                if not self._login_fiberhome():
                    result["status"] = "FAIL"
                    result["details"]["error"] = "No se pudo iniciar driver Selenium para reset"
                    return result

            if self._reset_factory_fiberhome():
                print("[TEST] Reset enviado. Esperando reinicio (aprox 120s)...")
                time.sleep(60) # Esperar a que baje la interfaz
                
                # Esperar a que vuelva el ping
                print("[TEST] Esperando respuesta de ping...")
                start_wait = time.time()
                while time.time() - start_wait < 300: # 5 min timeout
                    response = subprocess.run(
                        ['ping', '-n', '1', '-w', '1000', self.host],
                        capture_output=True
                    )
                    if response.returncode == 0:
                        print("[TEST] Dispositivo responde a ping. Esperando servicios (30s)...")
                        time.sleep(30)
                        break
                    time.sleep(5)
                
                # Re-login y Skip Wizard
                print("[TEST] Intentando re-login y skip wizard...")
                if self.login():
                    result["status"] = "PASS"
                    result["details"]["reset_performed"] = True
                    result["details"]["relogin_success"] = True
                    result["details"]["wizard_skipped"] = True # Asumido si login pasa (login llama a skip)
                else:
                    result["status"] = "FAIL"
                    result["details"]["error"] = "No se pudo hacer login después del reset"
            else:
                result["status"] = "FAIL"
                result["details"]["error"] = "Falló la ejecución del comando de reset"
                
            return result

        result = {
            "name": "FACTORY_RESET_PASS",
            "status": "SKIP",
            "details": {"reason": "Test no destructivo para este modelo - requiere verificacion manual"}
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
        
        # A partir de aqui es donde se tiene que hacer la verificacion de modelos
        # Primero el login 
        if (self.model == "MOD001"):
            #FIBER
            # Intentar login primero (obtiene serial y model name, auto-detecta modelo)
            if not self.login():
                print("[!] Error: No se pudo autenticar")
                return self.test_results
        elif (self.model == "MOD002"):
            #ZTE
            if not self.login():
                print("[X] ERROR: No se inició sesion en modelo ZTE")

        if not self.login():
                print("[!] Error: No se pudo autenticar (modelo general)")
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
        
        # De momento solo para fiber, se puede agregar condiciones con el operador or "||"
        if(self.model == "MOD001"):
            # Ejecutar tests comunes
            print(f"\n[*] Ejecutando tests comunes ({len(common_tests)} tests)...")
            for test_func in common_tests:
                result = test_func()
                self.test_results["tests"][result["name"]] = result
        elif (self.model == "MOD002"):
            # Extraer info primero
            print("En teoría ya se extrajo info del ZTE")
            # self.zte_info()
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
    
    # Parsear a json ZTE
    def parse_zte_status_xml(self, xml_text: str) -> dict:
        root = ET.fromstring(xml_text)

        data = {}

        # 1) Bloque de error (igual que antes)
        data["error"] = {
            "param": root.findtext("IF_ERRORPARAM"),
            "type":  root.findtext("IF_ERRORTYPE"),
            "str":   root.findtext("IF_ERRORSTR"),
            "id":    root.findtext("IF_ERRORID"),
        }

        # 2) Cualquier nodo que tenga <Instance> lo tratamos como contenedor
        for child in root:
            # saltar tags IF_...
            if child.tag.startswith("IF_"):
                continue

            instances = child.findall("Instance")
            if not instances:
                continue  # este nodo no es de datos

            # Nombre lógico: para OBJ_DEVINFO_ID → DEVINFO
            # para ID_WAN_COMFIG → WAN_COMFIG
            tag_name = child.tag
            name = (
                tag_name
                .replace("OBJ_", "")
                .replace("_ID", "")
                .replace("ID_", "")
            )

            inst_list = []
            for inst in instances:
                inst_dict = {}
                children = list(inst)

                # Recorremos de 2 en 2: ParaName, ParaValue...
                for i in range(0, len(children), 2):
                    name_el = children[i]
                    val_el  = children[i+1] if i+1 < len(children) else None

                    if name_el.tag != "ParaName" or val_el is None or val_el.tag != "ParaValue":
                        continue

                    key = (name_el.text or "").strip()
                    val = (val_el.text or "").strip()

                    # intento simple de castear números
                    if val.isdigit():
                        val = int(val)

                    inst_dict[key] = val

                if inst_dict:
                    inst_list.append(inst_dict)

            if not inst_list:
                continue

            # si solo hay una instancia → dict; si hay varias → lista
            if len(inst_list) == 1:
                data[name] = inst_list[0]
            else:
                data[name] = inst_list

        return data

    # CLICKS MASIVOS PARA EL ZTE:
    def click_anywhere(self, driver, selectors, desc, timeout=10):
        """
        Busca un elemento usando varios selectores, en el documento principal
        y en todos los frames/iframes. Si lo encuentra, hace click.
        selectors: lista de (By, selector)
        desc: texto descriptivo para logs
        """
        end_time = time.time() + timeout

        while time.time() < end_time:
            # 1) Documento principal
            driver.switch_to.default_content()
            for by, sel in selectors:
                try:
                    el = driver.find_element(by, sel)
                    if el.is_displayed():
                        print(f"[SELENIUM] {desc} encontrado en documento principal con {by}='{sel}'")
                        driver.execute_script("arguments[0].click();", el)
                        return True
                except NoSuchElementException:
                    continue
                except Exception as e:
                    print(f"[SELENIUM] Error al buscar {desc} en documento principal ({by}='{sel}'): {e}")

            # 2) Todos los frames/iframes
            frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
            for idx, frame in enumerate(frames):
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(frame)
                except Exception:
                    continue

                for by, sel in selectors:
                    try:
                        el = driver.find_element(by, sel)
                        if el.is_displayed():
                            print(f"[SELENIUM] {desc} encontrado en frame #{idx} con {by}='{sel}'")
                            driver.execute_script("arguments[0].click();", el)
                            driver.switch_to.default_content()
                            return True
                    except NoSuchElementException:
                        continue
                    except Exception as e:
                        print(f"[SELENIUM] Error al buscar {desc} en frame #{idx} ({by}='{sel}'): {e}")
            time.sleep(0.5)

        print(f"[SELENIUM] No se encontró {desc} en {timeout}s")
        return False

    def nav_lan(self, driver):
        # Volver a la interfaz principal (ya con sesión iniciada)
        driver.get(self.base_url)  # http://192.168.1.1
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "localnet"),
                (By.CSS_SELECTOR, "a[menupage='localNetStatus']"),
                (By.LINK_TEXT, "Local Network"),
            ],
            desc="Local Network (LAN)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo navegar a Local Network (LAN)")
        
        # Paso 2: Status
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "localNetStatus"),
                (By.CSS_SELECTOR, "a[menupage='localNetStatus']"),
                (By.LINK_TEXT, "Status"),
                (By.CSS_SELECTOR, "a[title='Status']"),
            ],
            desc="WLAN menu",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en WLAN")
        print("[SELENIUM] LAN debería estar habilitado ahora")

    def info_zte_basic(self, driver):
        print("Esta sobra c:\n")

    def nav_fibra(self, driver):
        # Volver a la interfaz principal (ya con sesión iniciada)
        driver.get(self.base_url)  # http://192.168.1.1
        # Paso 1: Internet (la sección padre)
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "internet"),
                (By.CSS_SELECTOR, "a[menupage='ponopticalinfo']"),
                (By.LINK_TEXT, "Internet"),
            ],
            desc="Internet (padre de PON)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en Internet (para PON)")

        # Paso 2: PON Inform
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "ponopticalinfo"),
                (By.CSS_SELECTOR, "p[menupage='ponopticalinfo']"),
                (By.XPATH, "//p[contains(text(),'PON Inform')]"),
            ],
            desc="PON Inform",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en PON Inform")
        print("[SELENIUM] PON/Fibra debería estar habilitado ahora")

    def nav_mac(self, driver):
        # Volver a la interfaz principal (ya con sesión iniciada)
        driver.get(self.base_url)  # http://192.168.1.1
        print("La url es: ",self.base_url)
        # Paso 1: Internet (igual que en fibra)
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "internet"),
                (By.CSS_SELECTOR, "a[title='Internet']"),
                (By.LINK_TEXT, "Internet"),
            ],
            desc="Internet (padre de WAN)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en Internet (para WAN)")

        # Paso 2: WAN
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "ethWanStatus"),
                (By.CSS_SELECTOR, "p[menupage='ethWanStatus']"),
                (By.XPATH, "//p[contains(text(),'WAN')]"),
            ],
            desc="WAN (ethWanStatus)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en WAN")

        # Paso 3: expandir "WAN Connection Status" (si aplica)
        self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "EthStateDevBar"),
                (By.XPATH, "//h1[contains(text(),'WAN Connection Status')]"),
            ],
            desc="WAN Connection Status",
            timeout=5
        )
        print("[SELENIUM] WAN/MAC debería estar habilitado ahora")

    def nav_wifi(self, driver):
        # Volver a la interfaz principal (ya con sesión iniciada)
        driver.get(self.base_url)  # http://192.168.1.1
        # Paso 1: Local Network
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "localnet"),
                (By.CSS_SELECTOR, "a[menupage='localNetStatus']"),
                (By.LINK_TEXT, "Local Network"),
            ],
            desc="Local Network (para WLAN)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en Local Network (para WLAN)")

        # Paso 2: WLAN
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "wlanConfig"),
                (By.CSS_SELECTOR, "a[menupage='wlanBasic']"),
                (By.LINK_TEXT, "WLAN"),
                (By.CSS_SELECTOR, "a[title='WLAN']"),
            ],
            desc="WLAN menu",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en WLAN")

        # Paso 3: expandir "WLAN SSID Configuration" (si aplica)
        self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "WLANSSIDConfBar"),
                (By.XPATH, "//h1[contains(text(),'WLAN SSID Configuration')]"),
            ],
            desc="WLAN SSID Configuration",
            timeout=5
        )
        print("[SELENIUM] WLAN/SSID debería estar habilitado ahora")

    def nav_usb(self, driver):
        # Volver a la interfaz principal (ya con sesión iniciada)
        driver.get(self.base_url)  # http://192.168.1.1
        # Paso 1: Home
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "homePage"),
                (By.CSS_SELECTOR, "a[menupage='homePage']"),
                (By.LINK_TEXT, "Home"),
            ],
            desc="Home (para USB)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en Home (para USB)")

        # Paso 2: USB Devices
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "home_category_usb"),
                (By.CSS_SELECTOR, "#home_category_usb a"),
                (By.XPATH, "//div[@id='home_category_usb']//a[contains(text(),'USB Devices')]"),
            ],
            desc="USB Devices (home_category_usb)",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en USB Devices")

        print("[SELENIUM] USB Devices debería estar habilitado ahora")

    # Función en caso de que sea la primera vez conectando un Huawei
    def hw_maybe_skip_initial_guide(self, driver, timeout=10):
        """
        Si el wizard inicial de Huawei está presente, intenta saltarlo usando los 3 pasos específicos:
        1. guidesyscfg (Skip)
        2. guideskip (Skip)
        3. nextpage (Return to Home Page)
        """
        print("[SELENIUM] Verificando si aparece el wizard de configuración inicial (Huawei)...")
        try:
            driver.switch_to.default_content()
            
            # Definir los pasos a ejecutar en orden
            steps = [
                {"id": "guidesyscfg", "desc": "Paso 1: Skip Network Config"},
                {"id": "guideskip", "desc": "Paso 2: Skip User Config"},
                {"id": "nextpage", "desc": "Paso 3: Return to Home Page"}
            ]
            
            wizard_found = False
            
            for step in steps:
                print(f"[SELENIUM] Buscando paso del wizard: {step['desc']} (ID: {step['id']})...")
                try:
                    # Buscar el elemento usando búsqueda recursiva en frames
                    # Usamos find_element_anywhere que ya implementamos recursivo
                    element = self.find_element_anywhere(
                        driver, 
                        By.ID, 
                        step["id"], 
                        desc=step["desc"],
                        timeout=5  # Aumentamos timeout a 5s para dar tiempo a cargar
                    )
                    
                    if element:
                        print(f"[SELENIUM] Wizard detectado - Ejecutando {step['desc']}...")
                        wizard_found = True
                        
                        # Hacer click
                        try:
                            element.click()
                        except:
                            driver.execute_script("arguments[0].click();", element)
                            
                        time.sleep(2) # Esperar un poco más entre pasos
                    else:
                        print(f"[SELENIUM] No se encontró el elemento {step['id']} ({step['desc']}).")
                        # Si no se encuentra, quizás ya pasamos ese paso
                        pass
                        
                except Exception as e:
                    print(f"[WARN] Error intentando ejecutar {step['desc']}: {e}")

            if wizard_found:
                print("[SELENIUM] Secuencia de salto de wizard finalizada.")
                # Asegurar que vamos a la página principal
                time.sleep(2)
                return True
            else:
                print("[INFO] No se detectó ningún paso del wizard de configuración inicial.")
                # Debug adicional: imprimir URL actual
                print(f"[DEBUG] URL actual: {driver.current_url}")
                return False

        except Exception as e:
            print(f"[WARN] Error general en hw_maybe_skip_initial_guide: {e}")
            return False
            return False
    
    def _reset_factory_huawei(self, driver) -> bool:
        """
        Realiza el factory reset en dispositivos Huawei.
        1. Busca el botón RESET en la página principal (Home Page).
        2. Al hacer click, se despliega un menú/sección.
        3. Busca y clickea el botón 'Restore Defaults'.
        """
        print("[SELENIUM] Iniciando proceso de Factory Reset (Huawei)...")
        try:
            # 1. Asegurarse de estar en la Home Page
            driver.switch_to.default_content()
            
            # 2. Buscar el botón inicial "RESET"
            print("[SELENIUM] Buscando botón RESET en Home Page...")
            reset_menu_btn = self.find_element_anywhere(
                driver,
                By.XPATH,
                "//div[contains(text(), 'RESET')] | //span[contains(text(), 'RESET')] | //a[contains(text(), 'RESET')]",
                desc="RESET Menu Button",
                timeout=5
            )
            
            if not reset_menu_btn:
                print("[WARN] No se encontró RESET por texto, intentando selectores alternativos...")
                reset_menu_btn = self.find_element_anywhere(
                    driver,
                    By.CSS_SELECTOR,
                    "div.reset-button, #reset_btn, .icon-reset", 
                    desc="RESET Menu Button (Alt)",
                    timeout=3
                )

            if not reset_menu_btn:
                print("[ERROR] No se encontró el botón RESET")
                return False

            # Hacer click para desplegar el menú
            print("[SELENIUM] Click en botón RESET...")
            try:
                reset_menu_btn.click()
            except:
                driver.execute_script("arguments[0].click();", reset_menu_btn)
            
            time.sleep(3) # Esperar a que se despliegue

            # 3. Buscar el botón "Restore Defaults"
            # Busqueda amplia por texto "Restore"
            print("[SELENIUM] Buscando botón 'Restore Defaults'...")
            
            # Intentar varios selectores
            restore_selectors = [
                (By.XPATH, "//button[contains(text(), 'Restore Defaults')]"),
                (By.XPATH, "//input[@value='Restore Defaults']"),
                (By.XPATH, "//div[contains(text(), 'Restore Defaults')]"),
                (By.XPATH, "//button[contains(text(), 'Restore')]"),
                (By.ID, "RestoreDefaults"),
                (By.ID, "RestoreDefault"),
                (By.NAME, "RestoreDefaults")
            ]
            
            restore_btn = None
            
            # Usar find_element_anywhere para cada selector
            for by, sel in restore_selectors:
                restore_btn = self.find_element_anywhere(driver, by, sel, desc=f"Restore Btn ({sel})", timeout=1)
                if restore_btn:
                    break
            
            if restore_btn:
                print("[SELENIUM] Botón 'Restore Defaults' encontrado. Ejecutando reset...")
                try:
                    restore_btn.click()
                except:
                    driver.execute_script("arguments[0].click();", restore_btn)
                
                # 4. Manejar la alerta de confirmación
                try:
                    WebDriverWait(driver, 5).until(EC.alert_is_present())
                    alert = driver.switch_to.alert
                    print(f"[SELENIUM] Alerta de confirmación detectada: {alert.text}")
                    alert.accept()
                    print("[SELENIUM] Alerta aceptada. El dispositivo se está reiniciando a fábrica.")
                    return True
                except TimeoutException:
                    print("[WARN] No apareció alerta de confirmación, verificando si la acción se ejecutó...")
                    return True
            else:
                print("[ERROR] No se encontró el botón 'Restore Defaults' después de hacer click en RESET")
                # Debug: Imprimir source del frame donde estaba RESET si es posible
                return False
        except Exception as e:
            print(f"[ERROR] Falló el proceso de Factory Reset: {e}")
            return False

    def _reset_factory_zte(self, driver) -> bool:
        print("[SELENIUM] Iniciando proceso de Factory Reset ZTE...")

        wait = WebDriverWait(driver, 10)

        def click_with_retry(locator, desc, retries=3, delay=1.0) -> bool:
            for intento in range(1, retries + 1):
                try:
                    elem = wait.until(EC.element_to_be_clickable(locator))
                    elem.click()
                    return True
                except StaleElementReferenceException:
                    print(f"[SELENIUM] {desc}: StaleElementReference, reintentando "
                        f"({intento}/{retries})...")
                    time.sleep(delay)
            return False

        try:
            driver.switch_to.default_content()

            # 1) Top menu
            print("[SELENIUM] Top Menu 'Management & Diagnosis'...")
            if not click_with_retry((By.ID, "mgrAndDiag"),
                                    "Top menu 'Management & Diagnosis'"):
                print("[ERROR] No se pudo clicar el menú superior 'Management & Diagnosis'")
                return False

            # 2) Menú lateral
            print("[SELENIUM] Buscando menú lateral 'System Management'...")
            if not click_with_retry((By.ID, "devMgr"),
                                    "Menú lateral 'System Management'"):
                print("[ERROR] No se pudo clicar el menú lateral 'System Management'")
                return False

            # 3) Pestaña Device Management
            print("[SELENIUM] Pestaña 'Device Management' encontrada. Haciendo click...")
            if not click_with_retry((By.ID, "rebootAndReset"),
                                    "Pestaña 'Device Management'"):
                print("[ERROR] No se pudo clicar la pestaña 'Device Management'")
                return False

            # 4) Expandir sección Factory Reset (sin guardar el WebElement)
            print("[SELENIUM] Esperando sección 'Factory Reset Management'...")
            header_loc = (By.ID, "ResetManagBar")
            wait.until(EC.presence_of_element_located(header_loc))

            print("[SELENIUM] Sección 'Factory Reset Management' colapsada. Expandiendo...")
            for intento in range(1, 4):
                try:
                    driver.find_element(*header_loc).click()
                    break
                except StaleElementReferenceException:
                    print(f"[SELENIUM] Encabezado 'Factory Reset' stale, reintentando "
                        f"({intento}/3)...")
                    time.sleep(0.8)

            # 5) Ahora esperamos directamente el botón Btn_reset como señal de que ya está expandido
            print("[SELENIUM] Buscando botón 'Factory Reset' (Btn_reset)...")
            if not click_with_retry((By.ID, "Btn_reset"), "Botón 'Factory Reset'"):
                print("[ERROR] No se pudo localizar un botón 'Factory Reset' cliqueable.")
                return False

            # 6) Diálogo de confirmación (OK)
            print("[SELENIUM] Esperando diálogo de confirmación 'Are you sure to restore factory defaults?'...")
            confirm_loc = (By.ID, "confirmOK")
            try:
                confirm_btn = WebDriverWait(driver, 8).until(
                    EC.element_to_be_clickable(confirm_loc)
                )
                confirm_btn.click()
                print("[SELENIUM] Botón 'OK' de confirmación clickeado.")
            except TimeoutException:
                print("[ERROR] No apareció el botón de confirmación 'OK' (id=confirmOK).")
                return False
            except StaleElementReferenceException:
                if not click_with_retry(confirm_loc, "Botón 'OK' de confirmación", retries=2):
                    print("[ERROR] No se pudo hacer click en el botón 'OK' de confirmación (stale).")
                    return False

            print("[SELENIUM] Factory Reset enviado. El equipo empezará a reiniciarse.")
            return True

        except Exception as e:
            print(f"[ERROR] Falló el proceso de Factory Reset ZTE: {e}")
            return False


    # Funcion para buscar en todos los frames para Huawei (Recursiva)
    def find_element_anywhere(self, driver, by, sel, desc="", timeout=10):
        """
        Busca un elemento en el documento principal y en todos los iframes recursivamente.
        Retorna el elemento si lo encuentra, manteniendo el driver en el contexto del frame donde se encontró.
        """
        # Helper recursivo
        def search_in_frames(drv, current_depth=0):
            # 1. Buscar en el contexto actual
            try:
                el = drv.find_element(by, sel)
                if el.is_displayed():
                    return el
            except:
                pass
            
            if current_depth > 3: # Limite de profundidad para evitar loops infinitos
                return None

            # 2. Buscar en sub-frames
            frames = drv.find_elements(By.TAG_NAME, "iframe")
            # También buscar 'frame' si es un frameset
            frames.extend(drv.find_elements(By.TAG_NAME, "frame"))
            
            for i, frame in enumerate(frames):
                try:
                    drv.switch_to.frame(frame)
                    found = search_in_frames(drv, current_depth + 1)
                    if found:
                        return found
                    drv.switch_to.parent_frame()
                except:
                    try:
                        drv.switch_to.parent_frame()
                    except:
                        pass
            return None

        # Inicio de la búsqueda
        try:
            driver.switch_to.default_content()
            
            # Intentar esperar un poco si se pide timeout
            start_time = time.time()
            while time.time() - start_time < timeout:
                driver.switch_to.default_content()
                found_el = search_in_frames(driver)
                if found_el:
                    print(f"[SELENIUM] {desc} encontrado con {by}='{sel}'")
                    return found_el
                time.sleep(0.5)
                
            return None
            
        except Exception as e:
            # print(f"[DEBUG] Error buscando {desc}: {e}")
            return None

    #Funciones de parseo de info Huawei
    def parse_table_label_value(self, driver, table_selector):
        """
        Parsea una tabla simple de 2 columnas (label / value) en un dict.
        table_selector: CSS selector del <table> que quieres leer.
        """
        table = driver.find_element(By.CSS_SELECTOR, table_selector)
        rows = table.find_elements(By.TAG_NAME, "tr")

        result = {}
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) >= 2:
                label = cells[0].text.strip().rstrip(":")
                value = cells[1].text.strip()
                if label:  # evita filas vacías
                    result[label] = value
        return result

    def parse_hw_device(self, driver):
        # Usamos el helper para encontrar los <td> en el frame correcto
        model_el = self.find_element_anywhere(
            driver, By.ID, "td1_2", desc="Modelo (td1_2)"
        )
        sn_el = self.find_element_anywhere(
            driver, By.ID, "td3_2", desc="Serial (td3_2)"
        )
        sw_el = self.find_element_anywhere(
            driver, By.ID, "td5_2", desc="Software version (td5_2)"
        )

        model = model_el.text.strip()

        sn_raw = sn_el.text.strip()
        serial_number = sn_raw.split()[0] if sn_raw else sn_raw

        sw_version = sw_el.text.strip()

        # Actualizar metadata global
        self.test_results["metadata"]["model"] = model
        self.test_results["metadata"]["serial_number"] = serial_number

        return {
            "model": model,
            "serial_number": serial_number,
            "serial_raw": sn_raw,
            "software_version": sw_version,
        }

    def parse_hw_optical(self, driver):
        def get_optical(bindtext_value):
            td_title = self.find_element_anywhere(
                driver,
                By.XPATH, f"//td[@bindtext='{bindtext_value}']",
                desc="TX and RX"
            )
            td_val = td_title.find_element(By.XPATH, "following-sibling::td[1]")
            return td_val.text.strip()

        tx = get_optical("amp_optic_txpower")   # "-- dBm" ó " -20.5 dBm", etc.
        rx = get_optical("amp_optic_rxpower")

        return {
            "tx_optical_power": tx,
            "rx_optical_power": rx,
        }

    def parse_hw_lan(self, driver):
        """
        Lee la tabla de puertos LAN (Eth Port).
        Busca filas <tr class="tabal_01"> en el frame que tenga la tabla.
        """
        ports = []

        # Siempre empezamos desde el documento principal
        driver.switch_to.default_content()

        # Revisamos primero el documento principal
        try:
            # tabal_01 y tabal_02
            rows = driver.find_elements(
                By.XPATH,
                "//tr[contains(@class,'tabal_01') or contains(@class,'tabal_02')]"
            )
            if rows:
                print(f"[SELENIUM] Fila LAN encontrada en documento principal ({len(rows)} filas)")
                for row in rows:
                    try:
                        tds = row.find_elements(By.TAG_NAME, "td")
                        if len(tds) >= 4:
                            ports.append({
                                "port":   tds[0].text.strip(),
                                "mode":   tds[1].text.strip(),
                                "speed":  tds[2].text.strip(),
                                "status": tds[3].text.strip(),
                            })
                    except Exception as e:
                        print(f"[SELENIUM] Error leyendo una fila LAN (doc principal): {e}")
                driver.switch_to.default_content()
                return {"ports": ports}
        except Exception:
            pass  # si falla, probamos en frames

        # Si no hubo nada en el doc principal, probamos en todos los frames
        frames = driver.find_elements(By.CSS_SELECTOR, "frame, iframe")
        for idx, frame in enumerate(frames):
            try:
                driver.switch_to.default_content()
                driver.switch_to.frame(frame)

                # tabal_01 y tabal_02
                rows = driver.find_elements(
                    By.XPATH,
                    "//tr[contains(@class,'tabal_01') or contains(@class,'tabal_02')]"
                )
                if not rows:
                    continue

                print(f"[SELENIUM] Fila LAN encontrada en frame #{idx} ({len(rows)} filas)")
                for row in rows:
                    try:
                        tds = row.find_elements(By.TAG_NAME, "td")
                        if len(tds) >= 4:
                            ports.append({
                                "port":   tds[0].text.strip(),
                                "mode":   tds[1].text.strip(),  # Full-duplex / Half-duplex
                                "speed":  tds[2].text.strip(),  # 1000 Mbit/s, etc.
                                "status": tds[3].text.strip(),  # Up / Down
                            })
                    except Exception as e:
                        print(f"[SELENIUM] Error leyendo una fila LAN en frame #{idx}: {e}")

                # Si ya encontramos y parseamos filas en este frame, salimos del bucle
                driver.switch_to.default_content()
                break

            except Exception as e:
                print(f"[SELENIUM] Error al procesar frame #{idx} para LAN: {e}")
                driver.switch_to.default_content()
                continue

        driver.switch_to.default_content()

        if not ports:
            print("[SELENIUM] No se pudo cargar la tabla de puertos LAN.")
        return {"ports": ports}

    def parse_hw_wifi_band(self, driver, band_label):
        # 1) Siempre buscamos el SSID; sabemos que este id existe
        ssid_el = self.find_element_anywhere(
            driver,
            By.ID,
            "wlan_ssidinfo_table_0_1",
            desc=f"SSID {band_label}",
        )
        ssid = ssid_el.text.strip()

        # 2) Intento 1: status por id=LANStatusVal
        try:
            status_el = self.find_element_anywhere(
                driver,
                By.ID,
                "LANStatusVal",
                desc=f"Status {band_label}",
            )
            status_txt = status_el.text.strip()
        except NoSuchElementException:
            # 3) Fallback: tomar la celda anterior en la misma fila del SSID
            try:
                row = ssid_el.find_element(By.XPATH, "./ancestor::tr[1]")
                tds = row.find_elements(By.TAG_NAME, "td")
                status_txt = ""
                if len(tds) >= 2:
                    # Asumimos que la última columna es el SSID
                    # y la penúltima es el status (Enabled/Disabled)
                    status_txt = tds[-2].text.strip()
                print(f"[WARN] Status id='LANStatusVal' no encontrado, usando columna vecina ({band_label})")
            except Exception as e:
                print(f"[WARN] No se pudo derivar status para {band_label}: {e}")
                status_txt = ""

        return {
            "band": band_label,
            "status": status_txt,
            "ssid": ssid,
        }

    def parse_hw_wifi24(self, driver):
        return self.parse_hw_wifi_band(driver, "2.4GHz")

    def parse_hw_wifi5(self, driver):
        return self.parse_hw_wifi_band(driver, "5GHz")

    def parse_hw_wifi24_pass(self, driver):
        # Asegúrate de que el checkbox para mostrar la contraseña 2.4GHz esté siendo clickeado
        try:
            show_pass_el = self.find_element_anywhere(
                driver,
                By.ID,
                "hidewlWpaPsk",  # id correcto para mostrar la contraseña
                desc="Checkbox de mostrar contraseña 2.4GHz"
            )
            driver.execute_script("arguments[0].click();", show_pass_el)

            # Esperar el campo de contraseña
            pwd_el = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "twlWpaPsk"))
            )
            password = pwd_el.get_attribute("value").strip()

            return {
                "band": "2.4GHz",
                "password": password,
            }
        except TimeoutException:
            print("[SELENIUM] No se pudo encontrar la contraseña WiFi 2.4GHz")
            return {"band": "2.4GHz", "password": "N/A"}

    def parse_hw_wifi5_pass(self, driver):
        # Asegúrate de que el checkbox para mostrar la contraseña 5GHz esté siendo clickeado
        try:
            show_pass_el = self.find_element_anywhere(
                driver,
                By.ID,
                "hidewlWpaPsk",  # id correcto para mostrar la contraseña
                desc="Checkbox de mostrar contraseña 5GHz"
            )
            driver.execute_script("arguments[0].click();", show_pass_el)

            # Esperar el campo de contraseña
            pwd_el = WebDriverWait(driver, 10).until(
                EC.visibility_of_element_located((By.ID, "twlWpaPsk"))
            )
            password = pwd_el.get_attribute("value").strip()

            return {
                "band": "5GHz",
                "password": password,
            }
        except TimeoutException:
            print("[SELENIUM] No se pudo encontrar la contraseña WiFi 5GHz")
            return {"band": "5GHz", "password": "N/A"}

    def parse_hw_mac(self, driver):
        """
        Lee la MAC mostrada en la pantalla 'Home Network Information'
        (Home Network -> wlancoverinfo.asp).
        Devuelve la MAC como string 'XX:XX:XX:XX:XX:XX' o None.
        """
        timeout = 10
        try:
            # Asegúrate de estar en el documento principal
            driver.switch_to.default_content()

            # 1) Cambiar al iframe donde se carga la página de Home Network
            frame = WebDriverWait(driver, timeout).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "menuIframe"))
            )
            print("[SELENIUM] Cambiado a iframe 'menuIframe' para leer Home Network / MAC.")

            # 2) Esperar a que al menos exista el título de la página
            try:
                WebDriverWait(driver, timeout).until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//*[contains(normalize-space(text()), 'Home Network Information')]")
                    )
                )
            except Exception:
                # No es crítico, algunos firmwares pueden no mostrar exactamente ese texto
                print("[SELENIUM] No se encontró el título 'Home Network Information', continúo de todos modos.")

            # 3) Intentar varias veces leer una MAC válida del texto renderizado
            mac_regex = re.compile(r"MAC[:：]\s*([0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5})")
            mac_value = None

            for attempt in range(6):  # ~6 intentos x 2s ≈ 12s
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text
                except Exception:
                    body_text = ""

                match = mac_regex.search(body_text or "")
                if match:
                    candidate = match.group(1).upper()
                    print(f"[SELENIUM] MAC candidata encontrada en texto renderizado: {candidate}")

                    # Filtrar MAC de plantilla (todo ceros)
                    if candidate != "00:00:00:00:00:00":
                        mac_value = candidate
                        break
                    else:
                        print("[SELENIUM] MAC es 00:00:00:00:00:00 (valor por defecto), reintentando...")

                time.sleep(2)

            if mac_value:
                print(f"[SELENIUM] MAC final leída en Home Network: {mac_value}")
                return mac_value

            print("[SELENIUM] No se pudo obtener una MAC distinta de 00:00:00:00:00:00 en Home Network.")
            return None

        except Exception as e:
            print(f"[SELENIUM] Error leyendo MAC en Home Network: {e}")
            return None
        finally:
            # Volver al documento principal por si el flujo sigue
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    def read_hw_usb_status(self, driver, timeout=10):
        """
        Lee el estado de USB en la página 'USB Application'.

        Devuelve un dict con:
        {
            "connected": True/False,
            "status": "usb conectado" | "usb desconectado",
            "value": "<valor del option>",
            "label": "<texto del option>"
        }
        """

        try:
            # Por si llegas desde otro flujo, garantizamos estar en el iframe correcto
            driver.switch_to.default_content()
            WebDriverWait(driver, timeout).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "menuIframe"))
            )

            select_el = WebDriverWait(driver, timeout).until(
                EC.presence_of_element_located((By.ID, "SrvClDevType"))
            )

            # Primer <option> del select (es el que muestra el estado actual)
            option_el = select_el.find_element(By.XPATH, "./option[1]")
            value = (option_el.get_attribute("value") or "").strip()
            label = (option_el.text or "").strip()

            print(f"[SELENIUM] USB option leída: value='{value}', text='{label}'")

            # Lógica de estado:
            # - Sin USB: value == "" y texto contiene "No USB Device"
            # - Con USB: cualquier otro caso (nombre de dispositivo, /mnt/usb/..., etc.)
            if (not value) and ("no usb device" in label.lower()):
                connected = False
                status_str = "usb desconectado"
            else:
                connected = True
                status_str = "usb conectado"

            print(f"[SELENIUM] Estado USB: {status_str}")

            return {
                "connected": connected,
                "status": status_str,
                "value": value,
                "label": label,
            }

        except Exception as e:
            print(f"[SELENIUM] Error leyendo estado USB: {e}")
            return {
                "connected": None,
                "status": "error",
                "value": None,
                "label": None,
            }
        finally:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass

    # FUNCIONES PARA NAVEGACION DE HUAWEI
    def nav_hw_info(self, driver):
        """System Information -> Device (información básica)"""

        # 1) Menú principal "System Information"
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_Systeminfo"),
                (By.NAME, "m1div_deviceinfo"),
                (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        # 2) Submenú "Device"
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_deviceinfo"),
                (By.XPATH, "//div[@id='name_deviceinfo']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Device']"),
            ],
            "Huawei Device (System Information)",
        )

    def nav_hw_optical(self, driver):
        """System Information -> Optical (fibra)"""

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_Systeminfo"),
                (By.NAME, "m1div_deviceinfo"),
                (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_opticinfo"),
                (By.XPATH, "//div[@id='name_opticinfo']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Optical']"),
            ],
            "Huawei Optical",
        )

    def nav_hw_lan(self, driver):
        """System Information -> Eth Port (información de LAN / conexiones Ethernet)"""

        # 1) Navegar a "System Information"
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_Systeminfo"),
                (By.NAME, "m1div_deviceinfo"),
                (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        # 2) Submenú "Eth Port"
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_ethinfo"),
                (By.XPATH, "//div[@id='name_ethinfo']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Eth Port']"),
            ],
            "Huawei Eth Port",
        )

        # Esperar que la tabla de LAN esté cargada
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//tr[contains(@class,'tabal_01')]"))
            )
            print("[SELENIUM] LAN / Ethernet data disponible")
        except TimeoutException:
            print("[SELENIUM] LAN / Ethernet data no disponible después de 10s")

    def nav_hw_wifi_24(self, driver):
        """System Information -> WLAN (2.4 GHz)"""

        # Ir a WLAN
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_Systeminfo"),
                (By.NAME, "m1div_deviceinfo"),
                (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlaninfo"),
                (By.XPATH, "//div[@id='name_wlaninfo']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei WLAN (menú WLAN)",
        )    

    def nav_hw_wifi_5(self, driver):
        """System Information -> WLAN (5 GHz)"""

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_Systeminfo"),
                (By.NAME, "m1div_deviceinfo"),
                (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlaninfo"),
                (By.XPATH, "//div[@id='name_wlaninfo']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei WLAN (menú WLAN)",
        )

        # Seleccionar radio 5G (value=2)
        self.click_anywhere(
            driver,
            [
                (By.CSS_SELECTOR, "input[name='WlanMethod'][value='2']"),
                (By.XPATH, "//input[@name='WlanMethod' and @value='2']"),
            ],
            "Huawei WLAN 5G (radio)",
        )

    def nav_hw_mac(self, driver):
        """System Information -> Home Network (tabla de MAC / clientes)"""

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_Systeminfo"),
                (By.NAME, "m1div_deviceinfo"),
                (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlancoverinfo"),
                (By.XPATH, "//div[@id='name_wlancoverinfo']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Home Network']"),
            ],
            "Huawei Home Network",
        )

    def nav_hw_show_pass_24(self, driver):
        """Advanced -> WLAN -> 2.4G Basic Network Settings, mostrar contraseña"""

        # Menú Advanced (WAN)
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_addconfig"),
                (By.NAME, "m1div_wan"),
                (By.XPATH, "//div[@id='name_addconfig' or @name='m1div_wan' or normalize-space(.)='Advanced']"),
            ],
            "Huawei Advanced (WAN)",
        )

        # Submenú WLAN
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlanconfig"),
                (By.XPATH, "//div[@id='name_wlanconfig']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei Advanced WLAN config",
        )

        # Tercer nivel: 2.4G Basic Network...
        self.click_anywhere(
            driver,
            [
                (By.ID, "wlan2basic"),
                (By.NAME, "m3div_WlanBasic2G"),
                (By.XPATH, "//div[@id='wlan2basic' or @name='m3div_WlanBasic2G']"),
            ],
            "Huawei 2.4G Basic Network",
        )

    def nav_hw_show_pass_5(self, driver):
        """Advanced -> WLAN -> 5G Basic Network Settings, mostrar contraseña"""

        # Menú Advanced (WAN)
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_addconfig"),
                (By.NAME, "m1div_wan"),
                (By.XPATH, "//div[@id='name_addconfig' or @name='m1div_wan' or normalize-space(.)='Advanced']"),
            ],
            "Huawei Advanced (WAN)",
        )

        # Submenú WLAN
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlanconfig"),
                (By.XPATH, "//div[@id='name_wlanconfig']"),
                (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei Advanced WLAN config",
        )

        # Tercer nivel: 5G Basic Network...
        self.click_anywhere(
            driver,
            [
                (By.ID, "wlan5basic"),
                (By.NAME, "m3div_WlanBasic5G"),
                (By.XPATH, "//div[@id='wlan5basic' or @name='m3div_WlanBasic5G']"),
            ],
            "Huawei 5G Basic Network",
        )

    def nav_hw_usb(self, driver, timeout=15):
        """
        Navega en el HG8145V5 a:
        Advanced  ->  Application  ->  USB Application

        Deja el driver dentro del iframe 'menuIframe' donde está la página
        'USB Application', listo para leer el select SrvClDevType.
        """
        try:
            driver.switch_to.default_content()
            wait = WebDriverWait(driver, timeout)

            # 1) Menú principal: Advanced
            adv_menu = wait.until(EC.element_to_be_clickable((
                By.XPATH,
                "//div[@id='name_addconfig' or @name='m1div_wan' or normalize-space(.)='Advanced']"
            )))
            print("[SELENIUM] Huawei Advanced (WAN) encontrado en documento principal.")
            adv_menu.click()

            # 2) Menú secundario: Application
            app_menu = wait.until(EC.element_to_be_clickable((By.ID, "name_application")))
            print("[SELENIUM] Huawei Application encontrado en documento principal con id='name_application'")
            app_menu.click()

            # 3) Menú terciario: USB Application
            usb_menu = wait.until(EC.element_to_be_clickable((By.ID, "usbapplication")))
            print("[SELENIUM] Huawei USB Application encontrado en documento principal con id='usbapplication'")
            usb_menu.click()

            # 4) Cambiar al iframe del contenido
            driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "menuIframe")))
            print("[SELENIUM] iframe 'menuIframe' disponible para USB Application.")

            # 5) Esperar el select de USB
            wait.until(EC.presence_of_element_located((By.ID, "SrvClDevType")))
            print("[SELENIUM] Select USB 'SrvClDevType' encontrado en página USB Application.")

            # return True

        except Exception as e:
            print(f"[SELENIUM] Error navegando a USB Application: {e}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            #return False

    def huawei_info(self, driver):
        # Funciones para dar los clicks necesarios para "desbloquear" la info
        funciones = [
            self.nav_hw_info,
            self.nav_hw_optical,
            self.nav_hw_lan,
            self.nav_hw_wifi_24,
            self.nav_hw_wifi_5,
            self.nav_hw_mac,
            self.nav_hw_show_pass_24,
            self.nav_hw_show_pass_5,
            self.nav_hw_usb,
        ]

        # Descripcion || navegacion (clicks) || extracción
        tests = [
            ("hw_device",  self.nav_hw_info,       self.parse_hw_device),
            ("hw_optical", self.nav_hw_optical,    self.parse_hw_optical),
            ("hw_lan",     self.nav_hw_lan,        self.parse_hw_lan),
            ("hw_wifi24",  self.nav_hw_wifi_24,    self.parse_hw_wifi24),
            ("hw_wifi5",   self.nav_hw_wifi_5,     self.parse_hw_wifi5),
            ("hw_mac",     self.nav_hw_mac,        self.parse_hw_mac),
            ("hw_wifi24_pass", self.nav_hw_show_pass_24, self.parse_hw_wifi24_pass),
            ("hw_wifi5_pass",  self.nav_hw_show_pass_5,  self.parse_hw_wifi5_pass),
            ("hw_usb",  self.nav_hw_usb, self.read_hw_usb_status)
        ]
        
        # Recorrer todas las funciones de clicks + extraer el DOM
        # Usar try/except para cada paso para evitar que un fallo detenga todo el proceso
        for name, nav_func, parse_func in tests:
            try:
                nav_func(driver)             # hace los clicks
                data = parse_func(driver)    # lee sólo lo que nos interesa
                self.test_results["tests"][name] = { # Pasar al test_results
                    "name": name,
                    "data": data,
                }
            except Exception as e:
                print(f"[WARN] Error en extracción de {name}: {type(e).__name__} - {e}")
                self.test_results["tests"][name] = {
                    "name": name,
                    "data": None,
                    "error": str(e)
                }

        self.save_results2("test_hg8145v5")
        #print(self.test_results)

    def zte_info(self, driver):
        # acceder a la info de zte 
        guid = str(int(time.time() * 1000))
        info = f"{self.base_url}/?_type=menuData&_tag=devmgr_statusmgr_lua.lua&_={guid}"
        # Sft version, model name, SN
        xml_url = f"{self.base_url}/?_type=menuData&_tag=devmgr_statusmgr_lua.lua&_={guid}"
        # USB
        xml_usb = f"{self.base_url}/?_type=menuData&_tag=usb_homepage_lua.lua&_={guid}"
        # LAN
        xml_lan = f"{self.base_url}/?_type=menuData&_tag=status_lan_info_lua.lua&_={guid}"
        # wifi
        xml_wifi = f"{self.base_url}/?_type=menuData&_tag=wlan_wlansssidconf_lua.lua&_={guid}"
        # fibra optica
        xml_fibra = f"{self.base_url}/?_type=menuData&_tag=optical_info_lua.lua&_={guid}"
        # MAC
        xml_mac = f"{self.base_url}/?_type=menuData&_tag=wan_internetstatus_lua.lua&TypeUplink=2&pageType=1&_={guid}"

        urls_xml = [
            xml_url,   # devmgr_statusmgr_lua
            xml_usb,   # usb_homepage_lua
            xml_lan,   # status_lan_info_lua
            xml_wifi,  # wlan_wlansssidconf_lua
            xml_fibra, # optical_info_lua
            xml_mac,   # wan_internetstatus_lua
        ]

        funciones = [
            self.info_zte_basic,
            self.nav_usb,
            self.nav_lan,
            self.nav_wifi,
            self.nav_fibra,
            self.nav_mac,
        ]
        
        #Update para generar reportes
        pruebas = [
            ("basic", self.info_zte_basic, xml_url),
            ("usb",   self.nav_usb,        xml_usb),
            ("lan",   self.nav_lan,        xml_lan),
            ("wifi",  self.nav_wifi,       xml_wifi),
            ("fibra", self.nav_fibra,      xml_fibra),
            ("mac",   self.nav_mac,        xml_mac),
        ]

        resultado_prueba = {
            "router_ip": self.base_url,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "tests": {}  # aquí vamos a meter basic, usb, lan, wifi, fibra, mac
        }
        
        try:
            print("Opcion 1:\n")
            xml_final = ""
            for name, func, url in pruebas:
                # 1) Navegación con Selenium para habilitar el endpoint
                func(driver)
                # 2) Obtener el XML 
                driver.get(url)
                raw = driver.page_source
                start = raw.find("<ajax_response_xml_root")
                end   = raw.rfind("</ajax_response_xml_root>") + len("</ajax_response_xml_root>")
                xml_final = raw[start:end]

                # 3) Parsear XML con tu función
                parsed = self.parse_zte_status_xml(xml_final)

                # 4) Actualizar metadata (modelo y serie) si vienen en DEVINFO
                devinfo = parsed.get("DEVINFO")
                if devinfo:
                    sn = devinfo.get("SerialNumber")
                    model_from_xml = devinfo.get("ModelName")
                    if sn:
                        self.test_results["metadata"]["serial_number"] = sn
                    if model_from_xml:
                        self.test_results["metadata"]["model"] = model_from_xml

                # 5) Armar el objeto resultado de esta prueba
                result = {
                    "name": name,
                    "status": parsed.get("error", {}).get("str") == "SUCC",
                    "details": parsed,          # aquí va el json parseado de ese XML
                }

                # 6) Guardarlo en self.test_results (igual que tu patrón test_func)
                self.test_results["tests"][result["name"]] = result

            #Guardar a archivo
            self.save_results2("test_mod002")
        except Exception as e:
            print("No success :c", e)
        
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
            # Huawei info data has different structure: {"name": ..., "data": ...}
            # Regular test results have: {"status": "PASS/FAIL", ...}
            status = test_data.get("status", "SKIP")  # Default to SKIP if no status
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

        print("\n" + "+"*60)
        print("REPORTE DE INFO \n")
        #Inicializar variables:
        sn = ""
        mac = ""
        modelo = ""
        dn = ""
        sft = ""
        w2 = ""
        w5 = ""
        # Obtencion de valores para mostrarlo en corto:
        if (self.model == "MOD001"):
            # Extraer metadata de forma segura
            metadata = self.test_results.get('metadata', {})
            base_info = metadata.get('base_info', {})
            wifi_info = base_info.get('wifi_info', {})
            
            sn = metadata.get('serial_number_physical', '')
            mac = metadata.get('mac_address', '')
            modelo = metadata.get('model', '')
            dn = metadata.get('device_name', '')
            sft =base_info.get('software_version', '')
            w2 = wifi_info.get('ssid_24ghz', '')
            w5 = wifi_info.get('ssid_5ghz', '')
        elif (self.model == "MOD002"):
            # TODO; la información está muy dispersa
            print("En proceso\n")
        print("El numero de serie es: ", sn)
        print("La mac es: ", mac)
        print("El modelo es (nuestra nomenclatura): ",modelo)
        print("El modelo es (real): ",dn)
        print("La versión de software es: ",sft)
        print("El nombre de la red wifi 2.4 es: ", w2)
        print("El nombre de la red wifi 5 es: ", w5)

        if (self.model == "MOD001"):
            print("\nREPORTE DE PRUEBAS \n")
            ping = self.test_results['tests']['PING_CONNECTIVITY'].get('status')
            factory_reset = self.test_results['tests']['FACTORY_RESET_PASS'].get('status')
            sftUpdate = "SKIP"
            usb_port = self.test_results['tests']['USB_PORT']['details'].get('usb_status')
            tx = self.test_results['tests']['TX_POWER']['details'].get('tx_power_dbm') # VALORES BUENOS => mientras sea positivo  """
            rx = self.test_results['tests']['RX_POWER']['details'].get('rx_power_dbm') # FALTA CONFIRMACION DE VALORES (entre -8 y -28)"""
            wifi2 = self.test_results['tests']['WIFI_24GHZ'].get('status')
            wifi5 = self.test_results['tests']['WIFI_5GHZ'].get('status')
            print("Prueba de ping: ", ping)
            print("Factory reset: ",factory_reset)
            print("Software update: ", sftUpdate)
            print("Prueba de puertos usb: ",usb_port)
            txpass = False
            rxpass = False
            if(float(tx) > 0):
                txpass = True
            if(float(rx) > -28): # ASEGURARSE DEL VALOR """
                rxpass = True
            print("Prueba tx: ", txpass)
            print("Prueba rx: ", rxpass)
            print("Prueba wifi 2.4: ", wifi2)
            print("Prueba wifi 5: ",wifi5)
        print("\n" + "+"*60)

    def save_results2(self, base_dir: str):
        """
        Guarda self.test_results en:
            base_dir/YYYY-MM-DD/HHMMSS_model_sn.json

        - base_dir: carpeta raíz del modelo (p.ej. 'test_mod002', 'test_hg8145v5')
        """
        meta = self.test_results.get("metadata", {})

        today = datetime.now().strftime("%Y-%m-%d")
        out_dir = Path(base_dir) / today
        out_dir.mkdir(parents=True, exist_ok=True)

        ts    = datetime.now().strftime("%H%M%S")
        model = meta.get("model", "unknown_model")
        sn    = meta.get("serial_number") or "noSN"

        # Limpiar SN para que no meta espacios / caracteres raros en el filename
        sn_clean = "".join(c for c in sn if c.isalnum() or c in ("-", "_"))

        filename = f"{ts}_{model}_{sn_clean}.json"
        out_file = out_dir / filename

        with out_file.open("w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)

        print(f"[RESULT] Reporte guardado en: {out_file}")
        return str(out_file)

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
            temp_tester._show_network_setup_guide(missing_networks)
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
    else:
        # Modo test: todos los tests
        tester = ONTAutomatedTester(args.host, args.model)
        tester.run_all_tests()
        
        # Mostrar reporte en consola
        if(args.model != "MOD003" and args.model != "MOD004" and args.model != "MOD005"):
            print("\n" + tester.generate_report())
            tester.save_results(args.output) # Guardar resultados
    

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
