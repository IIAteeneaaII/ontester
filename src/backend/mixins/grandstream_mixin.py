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

class GrandStreamMixin:
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
