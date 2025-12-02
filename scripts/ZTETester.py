#!/usr/bin/env python3
"""
ONT Automated Test Suite - ZTE F670L
Pruebas automatizadas para ZTE ZXHN F670L (MOD002)
Basado en ont_automated_tester.py
Fecha: 18/11/2025
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
from typing import Dict, Any

class ZTETester:
    def __init__(self, host: str):
        self.host = host
        self.model = "MOD002"
        self.base_url = f"http://{host}"
        self.ajax_url = f"http://{host}/cgi-bin/ajax"
        self.current_username = None
        self.current_password = None
        self.session = requests.Session()
        self.authenticated = False
        
        self.test_results = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "host": host,
                "model": "MOD002",
                "device_name": "ZTE ZXHN F670L",
                "serial_number": None,
                "device_type": "ONT"
            },
            "tests": {}
        }
        
        # Deshabilitar warnings SSL y proxy
        requests.packages.urllib3.disable_warnings()
        self.session.trust_env = False
        
        # Tags menuData conocidos del ZTE F670L (capturados del navegador)
        self.known_menudata_tags = {
            # Información del dispositivo
            'device_info': [
                'status_devicestatus_lua.lua',
                'devmgr_statusmgr_lua.lua',
                'dev_info_lua.lua',
                'system_info_lua.lua'
            ],
            # Información óptica PON/GPON
            'optical': [
                'optical_info_lua.lua',
                'status_opticalmgr_lua.lua',
                'optical_status_lua.lua',
                'pon_status_lua.lua',
                'gpon_info_lua.lua'
            ],
            # WiFi 2.4GHz y 5GHz
            'wifi': [
                'wireless_info_lua.lua',
                'wlan_info_lua.lua',
                'status_wlanmgr_lua.lua',
                'wifi_status_lua.lua',
                'wireless_basic_lua.lua',
                'wireless_security_lua.lua',
                'wireless_advanced_lua.lua'
            ],
            # Información de red WAN/LAN
            'network': [
                'wan_conn_info_lua.lua',
                'status_wanmgr_lua.lua',
                'wan_status_lua.lua',
                'lan_info_lua.lua',
                'status_lanmgr_lua.lua',
                'network_info_lua.lua',
                'dhcp_info_lua.lua'
            ],
            # VoIP y telefonía
            'voip': [
                'voip_status_lua.lua',
                'voip_basic_lua.lua',
                'sip_status_lua.lua'
            ],
            # USB y servicios
            'services': [
                'usb_info_lua.lua',
                'service_status_lua.lua',
                'upnp_status_lua.lua'
            ]
        }
        
        print(f"[*] ZTE Tester inicializado para {host}")

    # ==================== MÉTODOS DE AUTENTICACIÓN ===================="

    def _menudata_get(self, tag: str, verbose: bool = False) -> Dict:
        """Realiza petición GET usando el sistema menuData del ZTE"""
        params = {
            '_type': 'menuData',
            '_tag': tag,
            '_': str(int(datetime.now().timestamp() * 1000))  # Timestamp en milisegundos
        }
        
        try:
            response = self.session.get(
                self.base_url + "/",
                params=params,
                auth=(self.current_username or 'user', self.current_password or 'user'),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                try:
                    # Intentar parsear como JSON
                    data = response.json()
                    if verbose:
                        print(f"[DEBUG] {tag}: JSON response with {len(data)} keys")
                    return data
                except:
                    # Si no es JSON, retornar el texto raw
                    if verbose:
                        print(f"[DEBUG] {tag}: Raw text response ({len(response.text)} chars)")
                    return {"raw": response.text, "success": True}
            
            if verbose:
                print(f"[DEBUG] {tag}: HTTP {response.status_code}")
            return {"success": False, "status": response.status_code, "text": response.text}
        except Exception as e:
            if verbose:
                print(f"[DEBUG] {tag}: Error - {str(e)}")
            return {"success": False, "error": str(e)}

    def explore_menudata_tags(self, category: str = None, verbose: bool = True) -> Dict[str, Any]:
        """Explora todos los tags menuData conocidos o de una categoría específica"""
        results = {}
        
        if category and category in self.known_menudata_tags:
            tags_to_test = {category: self.known_menudata_tags[category]}
        else:
            tags_to_test = self.known_menudata_tags
        
        print(f"\n[*] Explorando tags menuData...")
        
        for cat_name, tag_list in tags_to_test.items():
            print(f"\n[*] Categoría: {cat_name.upper()}")
            results[cat_name] = {}
            
            for tag in tag_list:
                response = self._menudata_get(tag, verbose=verbose)
                
                if response and response.get('success') != False:
                    results[cat_name][tag] = {
                        'accessible': True,
                        'has_data': bool(response.get('raw') or len(response) > 1)
                    }
                    
                    if verbose:
                        # Mostrar preview de datos encontrados
                        if 'raw' in response:
                            raw_content = response['raw']
                            # Mostrar primeras líneas del contenido
                            lines = raw_content.split('\n')[:5]
                            preview = '\n      '.join(lines)
                            print(f"  ✓ {tag} ({len(raw_content)} chars):")
                            print(f"      {preview}")
                        else:
                            keys = [k for k in response.keys() if k not in ['success', 'raw']]
                            print(f"  ✓ {tag}: Keys: {keys[:5]}..." if len(keys) > 5 else f"  ✓ {tag}: Keys: {keys}")
                else:
                    results[cat_name][tag] = {'accessible': False}
                    if verbose:
                        error = response.get('error', response.get('status', 'Unknown'))
                        print(f"  ✗ {tag}: {error}")
        
        return results

    def _do_session_login(self, username: str, password: str) -> bool:
        """Realiza login POST para obtener sesión válida"""
        # Intentar diferentes endpoints de login conocidos para ZTE
        login_endpoints = [
            '/cgi-bin/luci',
            '/login.cgi',
            '/cgi-bin/login',
            '/',
        ]
        
        for endpoint in login_endpoints:
            try:
                # Parámetros comunes de login para ZTE
                login_data = {
                    'username': username,
                    'psd': password,
                    'password': password,
                    'action': 'login',
                    'submit': 'Login'
                }
                
                print(f"[DEBUG] Intentando login POST a {endpoint}")
                response = self.session.post(
                    self.base_url + endpoint,
                    data=login_data,
                    timeout=5,
                    verify=False,
                    allow_redirects=True
                )
                
                # Verificar si obtuvimos cookies de sesión
                if response.cookies:
                    print(f"[DEBUG] Cookies recibidas: {list(response.cookies.keys())}")
                    # Probar si la sesión funciona
                    test_response = self._menudata_get('status_devicestatus_lua.lua')
                    if test_response.get('raw') and 'SessionTimeout' not in test_response.get('raw', ''):
                        print(f"[AUTH] ✓ Sesión establecida via {endpoint}")
                        return True
                        
            except Exception as e:
                print(f"[DEBUG] Error en {endpoint}: {e}")
                continue
        
        return False

    def login(self) -> bool:
        """Realiza login en el ZTE usando sesión POST + menuData"""
        print("[AUTH] Intentando autenticación ZTE...")
        
        # Credenciales específicas para ZTE F670L
        # NOTA: Priorizar root/admin ya que user/user puede autenticar pero con permisos limitados
        credentials_to_try = [
            ('root', 'admin'),     # Credencial con permisos completos
            ('user', 'user'),      # Credencial con permisos limitados
            ('admin', 'admin')     # Alternativa
        ]
        
        # Tags de menuData para probar autenticación
        test_tags = [
            'devmgr_statusmgr_lua.lua',
            'dev_info_lua.lua',
            'status_devicestatus_lua.lua'
        ]
        
        for username, password in credentials_to_try:
            print(f"[AUTH] Probando: {username}/{password}")
            
            self.current_username = username
            self.current_password = password
            self.session.auth = (username, password)
            
            # Primero intentar login con sesión POST (requerido por ZTE)
            if self._do_session_login(username, password):
                print(f"[AUTH] ✓ Login con sesión exitoso: {username}/{password}")
                self.authenticated = True
                
                # Intentar extraer información del dispositivo
                self._extract_device_info()
                return True
            
            # Si falló el login por sesión, intentar Basic Auth directo
            print(f"[AUTH] Probando Basic Auth directo...")
            for tag in test_tags:
                device_info = self._menudata_get(tag)
                
                if device_info.get('success') != False and 'SessionTimeout' not in device_info.get('raw', ''):
                    # Si obtenemos respuesta válida (JSON o raw SIN SessionTimeout), el login fue exitoso
                    print(f"[AUTH] ✓ Login Basic Auth exitoso con {username}/{password}")
                    self.authenticated = True
                    
                    # Intentar extraer información del dispositivo
                    if isinstance(device_info, dict):
                        # Buscar ModelName en diferentes ubicaciones
                        model_name = None
                        
                        # Buscar en respuesta JSON directa
                        if 'ModelName' in device_info:
                            model_name = device_info['ModelName']
                        elif 'model' in device_info:
                            model_name = device_info['model']
                        
                        # Buscar en raw response
                        if not model_name and 'raw' in device_info:
                            raw_text = device_info['raw']
                            # Buscar patrones comunes
                            patterns = [
                                r'"ModelName":"([^"]+)"',
                                r'<ModelName>([^<]+)</ModelName>',
                                r'"model":"([^"]+)"'
                            ]
                            for pattern in patterns:
                                match = re.search(pattern, raw_text)
                                if match:
                                    model_name = match.group(1)
                                    break
                        
                        if model_name:
                            self.test_results['metadata']['device_name'] = model_name
                            print(f"[AUTH] Modelo detectado: {model_name}")
                    
                    # Intentar obtener más información
                    self._extract_device_info()
                    
                    return True
            
            print(f"[AUTH] ✗ Falló con {username}/{password}")
        
        print("[AUTH] ✗ Todas las credenciales fallaron")
        return False

    def _extract_device_info(self):
        """Extrae información adicional del dispositivo usando menuData"""
        print("[INFO] Extrayendo información del dispositivo...")
        
        # Tags de menuData conocidos para ZTE
        menudata_tags = [
            # Información del dispositivo
            'devmgr_statusmgr_lua.lua',
            'dev_info_lua.lua',
            'status_devicestatus_lua.lua',
            
            # Información óptica
            'optical_info_lua.lua',
            'status_opticalmgr_lua.lua',
            'optical_status_lua.lua',
            
            # Información de red
            'wan_conn_info_lua.lua',
            'status_wanmgr_lua.lua',
            'wan_status_lua.lua',
            
            # Información del sistema
            'system_info_lua.lua',
            'status_systemmgr_lua.lua',
            
            # Información LAN
            'lan_info_lua.lua',
            'status_lanmgr_lua.lua'
        ]
        
        extracted_count = 0
        
        for tag in menudata_tags:
            response = self._menudata_get(tag)
            
            if response and response.get('success') != False:
                # Intentar extraer información del JSON o raw
                data_to_parse = response
                
                # Si tenemos raw, intentar parsearlo
                if 'raw' in response and isinstance(response['raw'], str):
                    raw_text = response['raw']
                    
                    # Patrones de extracción
                    patterns = {
                        'serial_number': [
                            r'"SerialNumber":"([^"]+)"',
                            r'<SerialNumber>([^<]+)</SerialNumber>',
                            r'"serialNumber":"([^"]+)"'
                        ],
                        'hardware_version': [
                            r'"HardwareVersion":"([^"]+)"',
                            r'<HardwareVersion>([^<]+)</HardwareVersion>',
                            r'"hardwareVersion":"([^"]+)"'
                        ],
                        'software_version': [
                            r'"SoftwareVersion":"([^"]+)"',
                            r'<SoftwareVersion>([^<]+)</SoftwareVersion>',
                            r'"softwareVersion":"([^"]+)"'
                        ],
                        'rx_power': [
                            r'"rxpower":"([^"]+)"',
                            r'"RxPower":"([^"]+)"',
                            r'<RxPower>([^<]+)</RxPower>'
                        ],
                        'tx_power': [
                            r'"txpower":"([^"]+)"',
                            r'"TxPower":"([^"]+)"',
                            r'<TxPower>([^<]+)</TxPower>'
                        ]
                    }
                    
                    for key, pattern_list in patterns.items():
                        if not self.test_results['metadata'].get(key):
                            for pattern in pattern_list:
                                match = re.search(pattern, raw_text, re.IGNORECASE)
                                if match:
                                    value = match.group(1)
                                    self.test_results['metadata'][key] = value
                                    print(f"[INFO] {key.replace('_', ' ').title()}: {value}")
                                    extracted_count += 1
                                    break
                
                # También buscar en el dict directamente
                elif isinstance(data_to_parse, dict):
                    field_mappings = {
                        'SerialNumber': 'serial_number',
                        'HardwareVersion': 'hardware_version',
                        'SoftwareVersion': 'software_version',
                        'rxpower': 'rx_power',
                        'txpower': 'tx_power'
                    }
                    
                    for src_key, dst_key in field_mappings.items():
                        if src_key in data_to_parse and not self.test_results['metadata'].get(dst_key):
                            value = data_to_parse[src_key]
                            self.test_results['metadata'][dst_key] = value
                            print(f"[INFO] {dst_key.replace('_', ' ').title()}: {value}")
                            extracted_count += 1
        
        print(f"[INFO] Información extraída: {extracted_count} campos")

    # ==================== TESTS ====================

    def test_pwd_pass(self) -> Dict[str, Any]:
        """Test de autenticación"""
        print("[TEST] PWD_PASS - Autenticación")
        
        result = {
            "name": "PWD_PASS",
            "status": "PASS" if self.authenticated else "FAIL",
            "details": {}
        }
        
        if self.authenticated:
            result["details"]["message"] = f"Autenticación exitosa con {self.current_username}/{self.current_password}"
            if self.test_results['metadata'].get('serial_number'):
                result["details"]["serial_number"] = self.test_results['metadata']['serial_number']
        else:
            result["details"]["error"] = "No se pudo autenticar"
        
        return result

    def test_device_info(self) -> Dict[str, Any]:
        """Test de información del dispositivo"""
        print("[TEST] DEVICE_INFO - Información del dispositivo")
        
        result = {
            "name": "DEVICE_INFO",
            "status": "FAIL",
            "details": {}
        }
        
        if not self.authenticated:
            result["status"] = "SKIP"
            result["details"]["reason"] = "No autenticado"
            return result
        
        # Verificar que tenemos información básica
        has_serial = bool(self.test_results['metadata'].get('serial_number'))
        has_model = bool(self.test_results['metadata'].get('device_name'))
        
        if has_serial and has_model:
            result["status"] = "PASS"
            result["details"]["serial_number"] = self.test_results['metadata']['serial_number']
            result["details"]["model"] = self.test_results['metadata']['device_name']
            
            if self.test_results['metadata'].get('hardware_version'):
                result["details"]["hardware_version"] = self.test_results['metadata']['hardware_version']
            if self.test_results['metadata'].get('software_version'):
                result["details"]["software_version"] = self.test_results['metadata']['software_version']
        else:
            result["details"]["error"] = "Información incompleta"
            result["details"]["has_serial"] = has_serial
            result["details"]["has_model"] = has_model
        
        return result

    def test_optical_power(self) -> Dict[str, Any]:
        """Test de potencia óptica usando menuData"""
        print("[TEST] OPTICAL_POWER - Potencias TX/RX")
        
        result = {
            "name": "OPTICAL_POWER",
            "status": "FAIL",
            "details": {}
        }
        
        if not self.authenticated:
            result["status"] = "SKIP"
            result["details"]["reason"] = "No autenticado"
            return result
        
        # Tags conocidos para información óptica en ZTE
        optical_tags = [
            'optical_info_lua.lua',
            'status_opticalmgr_lua.lua',
            'optical_status_lua.lua',
            'devmgr_statusmgr_lua.lua',  # A veces incluye info óptica
            'status_devicestatus_lua.lua'
        ]
        
        rx_power = None
        tx_power = None
        
        for tag in optical_tags:
            response = self._menudata_get(tag)
            
            if response and response.get('success') != False:
                # Buscar en el dict directamente
                if 'rxpower' in response:
                    rx_power = response['rxpower']
                if 'txpower' in response:
                    tx_power = response['txpower']
                
                # Buscar en raw si existe
                if 'raw' in response and isinstance(response['raw'], str):
                    raw = response['raw']
                    
                    # Patrones para extracción de potencia
                    if not rx_power:
                        rx_patterns = [
                            r'"rxpower":"([^"]+)"',
                            r'"RxPower":"([^"]+)"',
                            r'<RxPower>([^<]+)</RxPower>',
                            r'rxPower["\s:]+([+-]?\d+\.?\d*)'
                        ]
                        for pattern in rx_patterns:
                            match = re.search(pattern, raw, re.IGNORECASE)
                            if match:
                                rx_power = match.group(1)
                                break
                    
                    if not tx_power:
                        tx_patterns = [
                            r'"txpower":"([^"]+)"',
                            r'"TxPower":"([^"]+)"',
                            r'<TxPower>([^<]+)</TxPower>',
                            r'txPower["\s:]+([+-]?\d+\.?\d*)'
                        ]
                        for pattern in tx_patterns:
                            match = re.search(pattern, raw, re.IGNORECASE)
                            if match:
                                tx_power = match.group(1)
                                break
                
                # Si encontramos alguna potencia, consideramos éxito
                if rx_power or tx_power:
                    result["status"] = "PASS"
                    result["details"]["tag"] = tag
                    
                    if rx_power:
                        result["details"]["rx_power"] = str(rx_power)
                        self.test_results['metadata']['rx_power'] = str(rx_power)
                    if tx_power:
                        result["details"]["tx_power"] = str(tx_power)
                        self.test_results['metadata']['tx_power'] = str(tx_power)
                    
                    break
        
        if result["status"] == "FAIL":
            result["details"]["error"] = "No se pudo obtener información de potencia óptica"
        
        return result

    def test_factory_reset(self) -> Dict[str, Any]:
        """Test de capacidad de factory reset (no destructivo)"""
        print("[TEST] FACTORY_RESET - Verificación")
        
        result = {
            "name": "FACTORY_RESET_PASS",
            "status": "SKIP",
            "details": {"reason": "Test no destructivo - requiere verificación manual"}
        }
        
        return result

    def test_usb_port(self) -> Dict[str, Any]:
        """Test de detección de puerto USB"""
        print("[TEST] USB_PORT - Detección")
        
        result = {
            "name": "USB_PORT",
            "status": "FAIL",
            "details": {}
        }
        
        # Buscar información de USB en menuData tags
        usb_tags = [
            'devmgr_statusmgr_lua.lua',
            'dev_info_lua.lua',
            'status_devicestatus_lua.lua',
            'system_info_lua.lua'
        ]
        
        for tag in usb_tags:
            response = self._menudata_get(tag)
            
            if response and response.get('success') != False:
                # Buscar información de USB
                usb_info = None
                
                if 'raw' in response and isinstance(response['raw'], str):
                    raw = response['raw'].lower()
                    # Buscar indicadores de USB
                    if 'usb' in raw:
                        result["status"] = "PASS"
                        result["details"]["usb_detected"] = True
                        result["details"]["tag"] = tag
                        result["details"]["note"] = "Puerto USB detectado en información del dispositivo"
                        return result
        
        result["details"]["error"] = "No se detectó información de puerto USB"
        return result

    def test_software_version(self) -> Dict[str, Any]:
        """Test de verificación de versión de software"""
        print("[TEST] SOFTWARE_PASS - Versión")
        
        result = {
            "name": "SOFTWARE_PASS",
            "status": "FAIL",
            "details": {}
        }
        
        metadata = self.test_results['metadata']
        
        if metadata.get('software_version'):
            result["status"] = "PASS"
            result["details"]["software_version"] = metadata['software_version']
            
            if metadata.get('hardware_version'):
                result["details"]["hardware_version"] = metadata['hardware_version']
            if metadata.get('device_name'):
                result["details"]["model_name"] = metadata['device_name']
            if metadata.get('serial_number'):
                result["details"]["serial_number"] = metadata['serial_number']
        else:
            result["details"]["error"] = "No se pudo obtener versión de software"
        
        return result

    def test_wifi_24ghz(self) -> Dict[str, Any]:
        """Test de validación de WiFi 2.4 GHz"""
        print("[TEST] WIFI_24GHZ - Verificación")
        
        result = {
            "name": "WIFI_24GHZ",
            "status": "FAIL",
            "details": {}
        }
        
        if not self.authenticated:
            result["status"] = "SKIP"
            result["details"]["reason"] = "No autenticado"
            return result
        
        # Tags de WiFi para ZTE
        wifi_tags = [
            'wireless_info_lua.lua',
            'wlan_info_lua.lua',
            'status_wlanmgr_lua.lua',
            'wifi_status_lua.lua'
        ]
        
        for tag in wifi_tags:
            response = self._menudata_get(tag)
            
            if response and response.get('success') != False:
                wifi_found = False
                
                if 'raw' in response and isinstance(response['raw'], str):
                    raw = response['raw']
                    
                    # Buscar SSID 2.4GHz
                    ssid_patterns = [
                        r'"ssid":"([^"]+)"',
                        r'"SSID":"([^"]+)"',
                        r'<ssid>([^<]+)</ssid>'
                    ]
                    
                    for pattern in ssid_patterns:
                        match = re.search(pattern, raw, re.IGNORECASE)
                        if match:
                            result["status"] = "PASS"
                            result["details"]["ssid"] = match.group(1)
                            result["details"]["tag"] = tag
                            wifi_found = True
                            break
                    
                    if wifi_found:
                        # Buscar password
                        pwd_patterns = [
                            r'"wpakey":"([^"]+)"',
                            r'"password":"([^"]+)"',
                            r'"psk":"([^"]+)"'
                        ]
                        for pattern in pwd_patterns:
                            match = re.search(pattern, raw, re.IGNORECASE)
                            if match:
                                result["details"]["password"] = match.group(1)
                                break
                        
                        return result
        
        result["details"]["error"] = "No se pudo obtener información de WiFi 2.4GHz"
        return result

    def test_wifi_5ghz(self) -> Dict[str, Any]:
        """Test de validación de WiFi 5 GHz"""
        print("[TEST] WIFI_5GHZ - Verificación")
        
        result = {
            "name": "WIFI_5GHZ",
            "status": "FAIL",
            "details": {}
        }
        
        if not self.authenticated:
            result["status"] = "SKIP"
            result["details"]["reason"] = "No autenticado"
            return result
        
        # Tags de WiFi para ZTE (buscar 5GHz)
        wifi_tags = [
            'wireless_info_lua.lua',
            'wlan_info_lua.lua',
            'status_wlanmgr_lua.lua',
            'wifi_status_lua.lua',
            'wireless_5g_lua.lua'
        ]
        
        for tag in wifi_tags:
            response = self._menudata_get(tag)
            
            if response and response.get('success') != False:
                if 'raw' in response and isinstance(response['raw'], str):
                    raw = response['raw']
                    
                    # Buscar indicadores de 5GHz
                    if '5g' in raw.lower() or '5ghz' in raw.lower():
                        result["status"] = "PASS"
                        result["details"]["tag"] = tag
                        result["details"]["note"] = "WiFi 5GHz detectado"
                        
                        # Intentar extraer SSID
                        ssid_patterns = [
                            r'"ssid":"([^"]+)"',
                            r'"SSID":"([^"]+)"'
                        ]
                        for pattern in ssid_patterns:
                            match = re.search(pattern, raw, re.IGNORECASE)
                            if match:
                                result["details"]["ssid"] = match.group(1)
                                break
                        
                        return result
        
        result["details"]["error"] = "No se pudo obtener información de WiFi 5GHz"
        return result

    def test_network_settings(self) -> Dict[str, Any]:
        """Test de configuración de red"""
        print("[TEST] NETWORK_SETTINGS - Configuración de red")
        
        result = {
            "name": "NETWORK_SETTINGS",
            "status": "FAIL",
            "details": {}
        }
        
        if not self.authenticated:
            result["status"] = "SKIP"
            result["details"]["reason"] = "No autenticado"
            return result
        
        # Tags de red para ZTE
        network_tags = [
            'wan_conn_info_lua.lua',
            'status_wanmgr_lua.lua',
            'lan_info_lua.lua',
            'status_lanmgr_lua.lua',
            'network_info_lua.lua'
        ]
        
        for tag in network_tags:
            response = self._menudata_get(tag)
            
            if response and response.get('success') != False:
                if 'raw' in response and isinstance(response['raw'], str):
                    raw = response['raw']
                    
                    # Buscar IP, máscara, gateway
                    ip_pattern = r'"ip(?:addr)?":"(\d+\.\d+\.\d+\.\d+)"'
                    mask_pattern = r'"(?:net)?mask":"(\d+\.\d+\.\d+\.\d+)"'
                    gw_pattern = r'"gateway":"(\d+\.\d+\.\d+\.\d+)"'
                    
                    ip_match = re.search(ip_pattern, raw, re.IGNORECASE)
                    mask_match = re.search(mask_pattern, raw, re.IGNORECASE)
                    gw_match = re.search(gw_pattern, raw, re.IGNORECASE)
                    
                    if ip_match or mask_match or gw_match:
                        result["status"] = "PASS"
                        result["details"]["tag"] = tag
                        
                        if ip_match:
                            result["details"]["ip_address"] = ip_match.group(1)
                        if mask_match:
                            result["details"]["netmask"] = mask_match.group(1)
                        if gw_match:
                            result["details"]["gateway"] = gw_match.group(1)
                        
                        return result
        
        result["details"]["error"] = "No se pudo obtener configuración de red"
        return result

    def test_dns_resolution(self) -> Dict[str, Any]:
        """Test de resolución DNS"""
        print("[TEST] DNS_RESOLUTION - Resolución DNS")
        
        result = {
            "name": "DNS_RESOLUTION",
            "status": "FAIL",
            "details": {}
        }
        
        try:
            # Intentar resolver un nombre de dominio
            test_domain = "google.com"
            ip_address = socket.gethostbyname(test_domain)
            
            result["status"] = "PASS"
            result["details"]["test_domain"] = test_domain
            result["details"]["resolved_ip"] = ip_address
            result["details"]["note"] = "DNS funcionando correctamente"
        except Exception as e:
            result["details"]["error"] = str(e)
            result["details"]["test_domain"] = test_domain
        
        return result

    def test_ping_connectivity(self) -> Dict[str, Any]:
        """Test de ping"""
        print("[TEST] PING_CONNECTIVITY - Ping")
        
        result = {
            "name": "PING_CONNECTIVITY",
            "status": "FAIL",
            "details": {}
        }
        
        try:
            param = "-n" if platform.system() == "Windows" else "-c"
            cmd = ["ping", param, "4", "-w", "2000", self.host]
            output = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if output.returncode == 0:
                result["status"] = "PASS"
                result["details"]["reachable"] = True
            else:
                result["details"]["reachable"] = False
                result["details"]["error"] = "Host no alcanzable"
        except Exception as e:
            result["details"]["error"] = str(e)
        
        return result

    def test_http_connectivity(self) -> Dict[str, Any]:
        """Test de conectividad HTTP"""
        print("[TEST] HTTP_CONNECTIVITY - HTTP")
        
        result = {
            "name": "HTTP_CONNECTIVITY",
            "status": "FAIL",
            "details": {}
        }
        
        try:
            start = time.time()
            response = requests.get(self.base_url, timeout=5, verify=False)
            elapsed_ms = (time.time() - start) * 1000
            
            result["status"] = "PASS"
            result["details"]["http_accessible"] = True
            result["details"]["response_time_ms"] = round(elapsed_ms, 2)
            result["details"]["status_code"] = response.status_code
        except Exception as e:
            result["details"]["error"] = str(e)
        
        return result

    # ==================== EJECUCIÓN Y REPORTES ====================

    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todos los tests"""
        print("\n" + "="*70)
        print("ONT AUTOMATED TEST SUITE - ZTE F670L")
        print(f"Host: {self.host}")
        print(f"Modelo: {self.model}")
        print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*70 + "\n")
        
        # Intentar login primero
        if not self.login():
            print("[!] Error: No se pudo autenticar")
            return self.test_results
        
        # Tests a ejecutar
        tests = [
            self.test_pwd_pass,
            self.test_ping_connectivity,
            self.test_http_connectivity,
            self.test_device_info,
            self.test_factory_reset,
            self.test_usb_port,
            self.test_software_version,
            self.test_optical_power,
            self.test_wifi_24ghz,
            self.test_wifi_5ghz,
            self.test_network_settings,
            self.test_dns_resolution
        ]
        
        # Ejecutar tests
        print(f"\n[*] Ejecutando {len(tests)} tests...\n")
        for test_func in tests:
            result = test_func()
            self.test_results["tests"][result["name"]] = result
        
        return self.test_results

    def generate_report(self) -> str:
        """Genera reporte en formato texto"""
        lines = []
        
        device_name = self.test_results['metadata'].get('device_name', 'Unknown')
        serial_number = self.test_results['metadata'].get('serial_number', 'No disponible')
        
        lines.append("="*70)
        lines.append("REPORTE DE PRUEBAS AUTOMATIZADAS - ZTE F670L")
        lines.append("="*70)
        lines.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Modelo: {device_name}")
        lines.append(f"Host: {self.host}")
        lines.append(f"Serie: {serial_number}")
        lines.append(f"Usuario: {self.current_username}/{self.current_password}")
        lines.append("")
        lines.append("RESULTADOS:")
        lines.append("-"*70)
        
        pass_count = 0
        fail_count = 0
        skip_count = 0
        
        for test_name, test_data in self.test_results["tests"].items():
            status = test_data["status"]
            symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⚠"
            lines.append(f"[{symbol}] {test_name}: {status}")
            
            # Agregar detalles
            details = test_data.get("details", {})
            for key, value in details.items():
                if key != "error" or status == "FAIL":
                    lines.append(f"    {key}: {value}")
            
            if status == "PASS":
                pass_count += 1
            elif status == "FAIL":
                fail_count += 1
            else:
                skip_count += 1
        
        lines.append("")
        lines.append("-"*70)
        lines.append(f"RESUMEN: {pass_count} PASS | {fail_count} FAIL | {skip_count} SKIP")
        lines.append("="*70)
        
        return "\n".join(lines)

    def save_results(self, output_dir: str = None):
        """Guarda los resultados en archivos"""
        timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
        date_folder = datetime.now().strftime("%d_%m_%y")
        
        if output_dir is None:
            base_dir = Path(__file__).parent.parent / "reports" / "automated_tests" / date_folder
            output_dir = base_dir
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Guardar JSON
        json_file = output_dir / f"{timestamp}_MOD002_results.json"
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False)
        
        # Guardar reporte de texto
        txt_file = output_dir / f"{timestamp}_MOD002_report.txt"
        with open(txt_file, "w", encoding='utf-8') as f:
            f.write(self.generate_report())
        
        print(f"\n[+] Resultados guardados:")
        print(f"    - JSON: {json_file}")
        print(f"    - TXT: {txt_file}")


def main():
    parser = argparse.ArgumentParser(description="ONT Automated Test Suite - ZTE F670L")
    parser.add_argument("--host", required=True, help="IP del dispositivo ZTE (generalmente 192.168.1.1)")
    parser.add_argument("--output", help="Directorio de salida (opcional)")
    parser.add_argument("--explore", action="store_true", help="Explorar todos los tags menuData disponibles")
    parser.add_argument("--category", help="Explorar solo una categoría específica (device_info, optical, wifi, network, voip, services)")
    
    args = parser.parse_args()
    
    tester = ZTETester(args.host)
    
    # Modo exploración
    if args.explore:
        if not tester.login():
            print("[!] Error: No se pudo autenticar")
            return 1
        
        print("\n" + "="*70)
        print("MODO EXPLORACION - TAGS MENUDATA")
        print("="*70)
        
        results = tester.explore_menudata_tags(category=args.category, verbose=True)
        
        # Guardar resultados de exploración
        timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
        output_dir = Path(__file__).parent.parent / "data" / "analysis_results"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_file = output_dir / f"{timestamp}_menudata_exploration.json"
        with open(json_file, "w", encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Resultados de exploración guardados en: {json_file}")
        return 0
    
    # Modo normal de tests
    tester.run_all_tests()
    
    print("\n" + tester.generate_report())
    tester.save_results(args.output)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())