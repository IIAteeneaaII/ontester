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
from typing import Dict, Any, List, Optional
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

# Metodos comunes
class CommonMixin:
    def generate_report(self) -> str:
        """Genera reporte en formato texto"""
        lines = []
        
        # Obtener información del dispositivo
        # Usar model_display_name si está disponible (nombre comercial correcto)
        device_name = self.test_results['metadata'].get('device_name', 'Unknown') or \
                        self.test_results['metadata'].get('model_display_name')
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
            self.driver = driver
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
                def emit(kind, payload):
                    if self.out_q:
                        self.out_q.put((kind, payload))
                emit("logSuper", display_name)
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
                    # Asegurar estructura
                    meta = self.test_results.setdefault("metadata", {})
                    base = meta.setdefault("base_info", {})
                    base["wifi_info"] = wifi_info
                    if wifi_info.get('ssid_24ghz'):
                        print(f"[AUTH] WiFi 2.4GHz: {wifi_info['ssid_24ghz']}")
                    if wifi_info.get('ssid_5ghz'):
                        print(f"[AUTH] WiFi 5GHz: {wifi_info['ssid_5ghz']}")
                    
                    print("[INFO] Intentando extracción de passwords WiFi por Selenium...")
                    selenium_passwords = self._extract_wifi_password_selenium()
                    if selenium_passwords:
                        meta = self.test_results.setdefault("metadata", {})
                        base = meta.setdefault("base_info", {})
                        wifi_info_dict = base.setdefault("wifi_info", {})
                        wifi_info_dict.update(selenium_passwords)
                    #     wifi_info.update(selenium_passwords)
                    #     print(f"[INFO] Passwords extraídas por Selenium: {list(selenium_passwords.keys())}")
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
    
    # Para la potencia de la red
    def scan_wifi_windows(self,
                      target_ssid: Optional[str] = None,
                      retries: int = 3,
                      delay: float = 1.0,
                      debug: bool = False) -> List[Dict[str, Any]]:
        """
        Escanea redes WiFi en Windows usando 'netsh wlan show networks mode=bssid'.

        - Hace varios intentos (retries) con pausa (delay) para mitigar que
        algunas redes no aparezcan en un solo escaneo.
        - Si target_ssid se indica, filtra las redes por ese SSID
        (case-insensitive, strip).
        """
        cmd = ["netsh", "wlan", "show", "networks", "mode=bssid"]

        all_networks: List[Dict[str, Any]] = []

        def parse_output(output: str) -> List[Dict[str, Any]]:
            networks: List[Dict[str, Any]] = []
            current_ssid: Optional[str] = None
            current_bssid_index = 0

            for line in output.splitlines():
                line = line.strip()

                # SSID 1 : NombreRed
                if line.startswith("SSID ") and " : " in line:
                    parts = line.split(" : ", 1)
                    current_ssid = parts[1].strip()
                    current_bssid_index = 0
                    continue

                if current_ssid is None:
                    continue

                # Inicio de un nuevo BSSID
                if line.startswith("BSSID "):
                    current_bssid_index += 1
                    networks.append({
                        "ssid": current_ssid,
                        "bssid_index": current_bssid_index,
                        "bssid": None,
                        "signal_percent": None,
                        "channel": None,
                        "radio_type": None,
                    })
                    continue

                if not networks:
                    continue

                net = networks[-1]

                if line.lower().startswith("bssid "):
                    parts = line.split(" : ", 1)
                    if len(parts) == 2:
                        net["bssid"] = parts[1].strip()

                elif line.lower().startswith("señal") or line.lower().startswith("signal"):
                    # Señal : 99%
                    m = re.search(r"(\d+)%", line)
                    if m:
                        net["signal_percent"] = int(m.group(1))

                elif line.lower().startswith("tipo de radio") or line.lower().startswith("radio type"):
                    parts = line.split(" : ", 1)
                    if len(parts) == 2:
                        net["radio_type"] = parts[1].strip()

                elif line.lower().startswith("canal") or line.lower().startswith("channel"):
                    parts = line.split(" : ", 1)
                    if len(parts) == 2:
                        try:
                            net["channel"] = int(parts[1].strip())
                        except ValueError:
                            net["channel"] = parts[1].strip()

                # --- NUEVO BLOQUE: fallback cuando la 'ñ' se rompe ---
                elif '%' in line and net.get("signal_percent") is None:
                    # Evitar líneas tipo "Uso del canal : 24 (%)" u otras métricas
                    lower = line.lower()
                    if "uso del canal" in lower or "capacidad disponible" in lower:
                        pass  # ignorar
                    else:
                        m = re.search(r"(\d+)%", line)
                        if m:
                            net["signal_percent"] = int(m.group(1))
            return networks

        for attempt in range(retries):
            proc = subprocess.run(cmd, capture_output=True)
            # decodificar con la codificación de consola típica
            try:
                output = proc.stdout.decode("cp850", errors="ignore")
            except Exception:
                output = proc.stdout.decode(errors="ignore")

            nets = parse_output(output)

            if debug:
                print(f"[SCAN WIFI] Intento {attempt+1}, {len(nets)} redes:")
                for n in nets:
                    print(f"  SSID='{n['ssid']}', signal={n['signal_percent']}%, ch={n['channel']}")

            # añadir a la lista total sin duplicar por (ssid, bssid)
            for n in nets:
                if not any(m["ssid"] == n["ssid"] and m["bssid"] == n["bssid"] for m in all_networks):
                    all_networks.append(n)

            # si buscamos un SSID concreto y ya apareció, podemos parar
            if target_ssid:
                t = target_ssid.strip().lower()
                if any(n["ssid"] and n["ssid"].strip().lower() == t for n in all_networks):
                    break

            time.sleep(delay)

        # filtro final por SSID, si se pide
        if target_ssid:
            t = target_ssid.strip().lower()
            all_networks = [n for n in all_networks if n["ssid"] and n["ssid"].strip().lower() == t]

        return all_networks

    def test_wifi_rssi_windows(self, ssid_24: str, ssid_5: str) -> dict:
        """
        Test de cobertura WiFi usando scan_wifi_windows (Windows).
        Busca RSSI (en %) para 2.4 GHz y 5 GHz y lo compara contra umbrales
        definidos en self.wifi_rssi_thresholds.

        El resultado se guarda en self.test_results['tests']['potencia_wifi'].
        """
        print("[TEST] WIFI_RSSI_WINDOWS")

        # Asegurar estructura de umbrales (en %)
        if not hasattr(self, "wifi_rssi_thresholds"):
            self.wifi_rssi_thresholds = {
                "2.4G": {"min_percent": 60}, # TODO cambiar valor por variable
                "5G":   {"min_percent": 60},
            }

        result = {
            "name": "potencia_wifi",
            "status": "FAIL",
            "details": {
                "ssid_24": ssid_24,
                "ssid_5": ssid_5,
                "best_24_percent": None,
                "best_5_percent": None,
                "min_24_percent": None,
                "min_5_percent": None,
                "pass_24": False,
                "pass_5": False,
                "thresholds": self.wifi_rssi_thresholds,
                "raw_24": [],
                "raw_5": [],
                "errors": [],
            },
        }

        # --- obtener redes ---
        nets_24 = self.scan_wifi_windows(ssid_24)
        nets_5  = self.scan_wifi_windows(ssid_5)

        result["details"]["raw_24"] = nets_24
        result["details"]["raw_5"]  = nets_5

        if not nets_24:
            result["details"]["errors"].append(f"No se encontró red 2.4G: {ssid_24}")
        if not nets_5:
            result["details"]["errors"].append(f"No se encontró red 5G: {ssid_5}")

        if not nets_24 and not nets_5:
            self.test_results["tests"]["potencia_wifi"] = result
            return result

        # --- mejor señal por banda (en %) ---
        def _best_signal(net_list):
            if not net_list:
                return None
            return max(
                (n for n in net_list if n.get("signal_percent") is not None),
                key=lambda n: n["signal_percent"],
                default=None,
            )

        best_24 = _best_signal(nets_24)
        best_5  = _best_signal(nets_5)

        if best_24:
            p24 = best_24["signal_percent"]
            result["details"]["best_24_percent"] = p24

        if best_5:
            p5 = best_5["signal_percent"]
            result["details"]["best_5_percent"] = p5

        # --- umbrales en % ---
        th = self.wifi_rssi_thresholds

        min24 = th.get("2.4G", {}).get("min_percent", 60) # TODO cambiar valor por variable
        min5  = th.get("5G",   {}).get("min_percent", 60)

        result["details"]["min_24_percent"] = min24
        result["details"]["min_5_percent"] = min5

        # --- evaluación PASS/FAIL ---
        p24 = result["details"]["best_24_percent"]
        p5  = result["details"]["best_5_percent"]

        pass_24 = p24 is not None and p24 >= min24
        pass_5  = p5  is not None and p5  >= min5

        result["details"]["pass_24"] = bool(pass_24)
        result["details"]["pass_5"]  = bool(pass_5)

        if pass_24 and pass_5:
            result["status"] = "PASS"
        else:
            result["status"] = "FAIL"

        # guardar siempre en la ruta fija
        self.test_results["tests"]["potencia_wifi"] = result
        return result

    def searchBins(self, ruta):
        ruta = Path(ruta)
        for item in ruta.glob("*.bin"):
            return str(item)
        return None

    def _resultados_json_corto(self, fecha, modelo, sn, mac, sftVer, wifi24, wifi5, passWifi, ping, reset, usb, tx, rx, w24, w5, sftU):
        # Validar si ha pasado los tests
        valido = (
            ping == "PASS"
            and reset == "PASS"
            and usb == "PASS"
            and float(tx) > 0
            and float(rx) > -28
            and bool(w24)
            and bool(w5)
        )

        resultado = {
            "info": {
                "modelo": modelo,
                "fecha_test": fecha,
                "sn": sn,
                "mac": mac,
                "sftVer": sftVer,
                "wifi24": wifi24,
                "wifi5": wifi5,
                "passWifi": passWifi
            },
            "tests": {
                "ping": ping,
                "reset": reset,
                "usb": usb,
                "tx": tx,
                "rx": rx,
                "w24": w24,
                "w5": w5,
                "sftU": sftU
            },
            "valido": valido
        }

        return resultado
    
    def _resultadosFiber(self):
        optTest = self.opcionesTest
        tests_opts = optTest.get("tests", {})
        # Valores informativos
        fecha = self.test_results['metadata'].get('timestamp') # "2025-11-28T13:51:32.497520"
        modelo = self.test_results['metadata']['device_name'] # modelo 
        sn = self.test_results['metadata']['base_info']['raw_data'].get('gponsn') #sn
        mac = self.test_results['metadata']['base_info']['raw_data'].get('brmac') #mac
        sftVer = self.test_results['metadata']['base_info']['raw_data'].get('SoftwareVersion') #nombre sft
        wifi24 = self.test_results['metadata']['base_info']['wifi_info'].get('ssid_24ghz') #nombre wifi 2.4
        wifi5 = self.test_results['metadata']['base_info']['wifi_info'].get('ssid_5ghz') #nombre wifi 2.4
        passWifi = self.test_results['additional_info']['wifi_info']['psw'].get('password_24ghz') # contraseña

        # Tests
        ping = self.test_results['tests']['PING_CONNECTIVITY'].get('status') # pass
        if tests_opts.get("factory_reset", True):
            reset = self.test_results['tests']['FACTORY_RESET_PASS'].get('status') # pass
        else:
            reset = "SIN PRUEBA"
        if tests_opts.get("usb_port", True):
            usb = self.test_results['tests']['USB_PORT'].get('status') # pass
        else:
            usb = "SIN PRUEBA"
        if tests_opts.get("tx_power", True) and tests_opts.get("rx_power", True):
            tx = self.test_results['metadata']['base_info'].get('tx_power_dbm') # valor negativo
            rx = self.test_results['metadata']['base_info'].get('rx_power_dbm') # valor negativo
            def _to_float_safe(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
            # Revisar si la fibra pasa las pruebas
            print("LOS valores de tx y rx son: "+str(tx)+" "+str(rx))
            print("Los valores de la super de tx son: "+str(self._getMinFibraTx()) +" "+str(self._getMaxFibraTx()))
            print("Los valores de la super de rx son: "+str(self._getMinFibraRx()) +" "+str(self._getMaxFibraRx()))
            if(_to_float_safe(tx) >= self._getMinFibraTx() and _to_float_safe(tx) <= self._getMaxFibraTx()):
                tx = True
            else:
                tx = False
            
            if(_to_float_safe(rx) >= self._getMinFibraRx() and _to_float_safe(rx) <= self._getMaxFibraRx()):
                rx = True
            else:
                rx = False
        else:
            tx = "SIN PRUEBA"
            rx = "SIN PRUEBA"
        
        if tests_opts.get("wifi_24ghz_signal", True) and tests_opts.get("wifi_5ghz_signal", True):
            w24 = self.test_results['tests']['WIFI_24GHZ']['details'].get('enabled') # true
            w5 = self.test_results['tests']['WIFI_5GHZ']['details'].get('enabled') # true
            rssi_2g = int(self.test_results['tests']["WIFI_24GHZ"]["details"]["data"]["wifi_status"][0]["rssi_2g"]) # valor negativo con la potencia del wifi
            rssi_5g = int(self.test_results['tests']["WIFI_24GHZ"]["details"]["data"]["wifi_status"][0]["rssi_5g"]) # valor negativo con la potencia del wifi

            min_valor_wifi = self._getMinWifi24Signal()
            min_valor_wifi5 = self._getMinWifi5Signal()
            max_valor_wifi = self._getMaxWifi24Signal()
            max_valor_wifi5 = self._getMaxWifi5Signal()

            if(rssi_2g >= min_valor_wifi and rssi_2g <= max_valor_wifi):
                w24 = True
            else:
                w24 = False

            if(rssi_5g >= min_valor_wifi5 and rssi_5g <= max_valor_wifi5):
                w5 = True
            else:
                w5 = False
        else:
            w24 = "SIN PRUEBA"
            w5 = "SIN PRUEBA"
        sftU = "SIN PRUEBA"
        if tests_opts.get("software_update", True):
            #Obtener resultado de actualización de sft
            actN = self.test_results['tests']['software_update'].get('necesaria') # Bool
            actC = self.test_results['tests']['software_update'].get('completada') # Bool
            actNV = self.test_results['tests']['software_update'].get('version_nueva') # str
            if (actN):
                #Actualización necesaria
                sftVer = sftVer+" !"
                if actC:
                    sftVer = actNV+" ACTUALIZADO"
                    sftU = True
            else:
                sftU = True
        
        # Obtener los resultados como json
        resultado = {}
        resultado = self._resultados_json_corto(fecha, modelo, sn, mac, sftVer, wifi24, wifi5, passWifi, ping, reset, usb, tx, rx, w24, w5, sftU)
        return resultado
    
    def _resultadosZTE(self):
        optTest = self.opcionesTest
        tests_opts = optTest.get("tests", {})
        # Valores informativos
        fecha = self.test_results['metadata'].get('timestamp') # "2025-11-28T13:51:32.497520"
        modelo = self.test_results['metadata']['model'] # modelo 
        sn = self.test_results['metadata'].get('serial_number') #sn
        ruta_mac = self.test_results['tests']['mac']['details']['WAN_COMFIG']
        mac = None
        for cfg in ruta_mac:
            if cfg.get("ConnTrigger") == "AlwaysOn":
                mac = cfg.get("WorkIFMac")  # aquí está la MAC
                break
        sftVer = self.test_results['tests']['basic']['details']['DEVINFO'].get('SoftwareVer') #sft version
        ruta_wifi = self.test_results['tests']['wifi']['details']['WLANAP']
        essids_validos = [
            ap["ESSID"]
            for ap in ruta_wifi
                if "ESSID" in ap and "SSID" not in ap["ESSID"]
        ]
        wifi24 = essids_validos[0] if essids_validos else None
        wifi5 = essids_validos[1] if essids_validos else None
        passWifi = self.test_results['tests']['Contraseña']['details'].get('password')

        # Tests
        ping = "PASS" # si llega hasta aqui es que se le puede hacer ping
        if tests_opts.get("factory_reset", True):
            reset = "PASS" # ya está implementado y si no se resetea no hace nada
        else:
            reset = "SIN PRUEBA"
        if tests_opts.get("usb_port", True):
            usb_ruta = self.test_results['tests']['usb']['details'] # ruta donde estará o no el valor buscado
            usb = "USBDEV" in usb_ruta # True or False
            if(usb):
                usb_final=True
            else:
                usb_final=False
        else:
            usb_final="SIN PRUEBA"
        if tests_opts.get("tx_power", True) and tests_opts.get("rx_power", True):
            def _to_float_safe(v):
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return None
            tx = self.test_results['tests']['fibra']['details']['PON_OPTICALPARA'].get('RxPower') # valor negativo
            rx = self.test_results['tests']['fibra']['details']['PON_OPTICALPARA'].get('TxPower') # valor negativo
            print("LOS valores de tx y rx son: "+str(tx)+" "+str("rx"))
            # Revisar si la fibra pasa las pruebas
            if(_to_float_safe(tx) >= self._getMinFibraTx() and _to_float_safe(tx) <= self._getMaxFibraTx()):
                tx = True
            else:
                tx = False
            
            if(_to_float_safe(rx) >= self._getMinFibraRx() and _to_float_safe(rx) <= self._getMaxFibraRx()):
                rx = True
            else:
                rx = False
        else:
            tx = "SIN PRUEBA"
            rx = "SIN PRUEBA"
        if tests_opts.get("wifi_24ghz_signal", True) and tests_opts.get("wifi_5ghz_signal", True):
            w24 = self.test_results['tests']['wifi']['details']['WLANSETTING'][0]["RadioStatus"] # valor 1 si activo
            w5 = self.test_results['tests']['wifi']['details']['WLANSETTING'][1]["RadioStatus"] # valor 1 si activo
            # validar la potencia del wifi
            # verificar que el reporte no tenga errores
            pot = self.test_results["tests"]["potencia_wifi"]
            details = pot["details"]
            raw_24 = details["raw_24"]
            raw_5 = details["raw_5"]
            
            # Obtener configuraciones de minimos en porcentajes
            min_valor_wifi = self._getMinWifi24SignalPercent()
            min_valor_wifi5 = self._getMinWifi5SignalPercent()

            # Verificar que NO estén vacías
            if details["raw_24"]:
                # wifi 2.4 con valor || validar si la potencia es mayor a la esperada TODO cambiar por variable
                net = next((n for n in raw_24 if n["ssid"] == wifi24), None)
                if net and net["signal_percent"] >= min_valor_wifi:
                    w24 = True
                else:
                    w24 = False
            else:
                w24 = False

            # Verificar que NO estén vacías
            if details["raw_5"]:
                # wifi 2.4 con valor || validar si la potencia es mayor a la esperada TODO cambiar por variable
                net = next((n for n in raw_5 if n["ssid"] == wifi5), None)
                if net and net["signal_percent"] >= min_valor_wifi5:
                    w5 = True
                else:
                    w5 = False
            else:
                w5 = False
        else:
            w24 = "SIN PRUEBA"
            w5 = "SIN PRUEBA"

        if tests_opts.get("software_update", True):
            try:
                sftU = self.test_results['tests']['software_update']['details'].get('update_completed')
            except:
                sftU = False
        else:
            sftU = "SIN PRUEBA"
        # Obtener los resultados como json
        resultado = {}
        resultado = self._resultados_json_corto(fecha,modelo, sn, mac, sftVer, wifi24, wifi5, passWifi, ping, reset, usb_final, tx, rx, w24, w5, sftU)
        return resultado
    
    def _resultadosHuawei(self):
        optTest = self.opcionesTest
        tests_opts = optTest.get("tests", {})
        
        # Valores informativos
        fecha = self.test_results['metadata'].get('timestamp') # "2025-11-28T13:51:32.497520"
        modelo = self.test_results['metadata']['model'] # modelo 
        sn = self.test_results['metadata'].get('serial_number') #sn
        mac = self.test_results['tests']['hw_mac'].get('data') # mac
        sftVer = self.test_results['tests']['hw_device']['data'].get('software_version') # sft version
        wifi24 = self.test_results['tests']['hw_wifi24']['data'].get('ssid') # nombre wifi
        wifi5 = self.test_results['tests']['hw_wifi5']['data'].get('ssid') # nombre wifi
        passWifi = self.test_results['tests']['hw_wifi24_pass']['data'].get('password') # pass wifi

        # Tests
        ping = "PASS" # sin poder hacer ping no se podría avanzar tanto
        if tests_opts.get("factory_reset", True):
            reset = "PASS" # ya se resetea
        else:
            reset= "SIN PRUEBA"
        if tests_opts.get("usb_port", True):
            usb = self.test_results['tests']['hw_usb']['data'].get('connected') # true or false
            if(usb):
                usb_final = True
            else:
                usb_final = False
        else:
            usb_final = "SIN PRUEBA"
        if tests_opts.get("tx_power", True) and tests_opts.get("rx_power", True):
            tx = self.test_results['tests']['hw_optical']['data'].get('tx_optical_power') # -- dBm si no tiene conexion
            rx = self.test_results['tests']['hw_optical']['data'].get('rx_optical_power') # -- dBm si no tiene conexion
        else:
            tx = "SIN PRUEBA"
            rx = "SIN PRUEBA"
        if tests_opts.get("wifi_24ghz_signal", True) and tests_opts.get("wifi_5ghz_signal", True):
            w24 = self.test_results['tests']['hw_wifi24']['data'].get('status') # Enabled si true
            w5 = self.test_results['tests']['hw_wifi5']['data'].get('status') # Enabled si true
            # validar la potencia del wifi
            # verificar que el reporte no tenga errores
            pot = self.test_results["tests"]["potencia_wifi"]
            details = pot["details"]
            raw_24 = details["raw_24"]
            raw_5 = details["raw_5"]
            
            # Obtener configuraciones de minimos en porcentajes
            min_valor_wifi = self._getMinWifi24SignalPercent()
            min_valor_wifi5 = self._getMinWifi5SignalPercent()

            # Verificar que NO estén vacías
            if details["raw_24"]:
                # wifi 2.4 con valor || validar si la potencia es mayor a la esperada TODO cambiar por variable
                net = next((n for n in raw_24 if n["ssid"] == wifi24), None)
                if net and net["signal_percent"] >= min_valor_wifi:
                    w24 = True
                else:
                    w24 = False
            else:
                w24 = False

            # Verificar que NO estén vacías
            if details["raw_5"]:
                # wifi 2.4 con valor || validar si la potencia es mayor a la esperada TODO cambiar por variable
                net = next((n for n in raw_5 if n["ssid"] == wifi5), None)
                if net and net["signal_percent"] >= min_valor_wifi5:
                    w5 = True
                else:
                    w5 = False
            else:
                w5 = False
        else:
            w24 = "SIN PRUEBA"
            w5 = "SIN PRUEBA"

        
        # Valores por defecto para no mandar --
        tx_final=-60.0
        rx_final=-60.0
        if(tx != "-- dBm"):
            tx_final = tx
        if(rx != "-- dBm"):
            rx_final = rx

        # Revisar si la fibra pasa las pruebas
        if tests_opts.get("tx_power", True) and tests_opts.get("rx_power", True):
            if(tx_final >= self._getMinFibraTx() and tx_final <= self._getMaxFibraTx()):
                tx_final = True
            else:
                tx_final = False
            
            if(rx_final >= self._getMinFibraRx() and rx_final <= self._getMaxFibraRx()):
                rx_final = True
            else:
                rx_final = False
        if tests_opts.get("software_update", True):
            sftU = self.test_results['tests']['software_update']['details'].get('update_completed')
        else:
            sftU = "SIN PRUEBA"
        # Obtener los resultados como json
        resultado = {}
        resultado = self._resultados_json_corto(fecha, modelo, sn, mac, sftVer, wifi24, wifi5, passWifi, ping, reset, usb_final, tx_final, rx_final, w24, w5, sftU)
        return resultado
    # Aqui voy a poner el resultado de las pruebas de todos los modelos
    # PD para Atenea, las funciones devuelven un dict con la siguiente estructura:
    """
    resultado = {
        "info": {
            "modelo": modelo,
            "sn": sn,
            "mac": mac,
            "sftVer": sftVer,
            "wifi24": wifi24,
            "wifi5": wifi5,
            "passWifi": passWifi,
        },
        "tests": {
            "ping": ping,
            "reset": reset,
            "usb": usb,
            "tx": tx,
            "rx": rx,
            "w24": w24,
            "w5": w5,
            "sftU": sftU
        },
        "valido": valido, 
    }
    """
    def _resultados_finales(self):
        res = {}
        # Identificar el modelo
        if (self.model == "MOD001" or self.model == "MOD008"):
            #Fiber | ont
            res = self._resultadosFiber()
        elif (self.model == "MOD002"):
            #zte | ont
            res = self._resultadosZTE()
        elif (self.model == "MOD003" or self.model == "MOD004" or self.model == "MOD005" or self.model == "MOD007"):
            #huawei | ont
            res = self._resultadosHuawei()
        elif (self.model == "MOD006"):
            #grandstream | empresarial
            print("A este modelo aun le falta")
        else:
            #otro modelo
            print("Sin reporte de resultados, modelo no admitido")

        return res
    