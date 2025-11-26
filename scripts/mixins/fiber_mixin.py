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

class FiberMixin:
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

