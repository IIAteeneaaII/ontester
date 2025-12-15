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
import re
from typing import Set
import customtkinter as ct
from PIL import Image
import threading
import tkinter as tk  # para PhotoImage
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
    # print("[WARNING] Selenium no disponible. Instala con: pip install selenium webdriver-manager")

class Mac():
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
                    # print(f"[SELENIUM] {desc} encontrado con {by}='{sel}'")
                    return found_el
                time.sleep(0.5)
                
            return None
            
        except Exception as e:
            # # print(f"[DEBUG] Error buscando {desc}: {e}")
            return None

    def _login_fiberhome(self) -> bool:
        """
        Login específico para Fiberhome usando Selenium.
        Soporta navegación a reset de fábrica y skip wizard.
        """
        if not SELENIUM_AVAILABLE:
            # print("[ERROR] Selenium no está disponible para Fiberhome")
            return False

        driver = None
        headless = True # DEBUG: Visible para el usuario
        try:
            # print(f"[SELENIUM] Iniciando login Fiberhome a {self.host}...")
            
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
            
            # --- LIMPIEZA DE SESIONES PREVIA (MEJORADA CON POST) ---
            # print("[SELENIUM] FORZANDO CIERRE DE SESIONES ACTIVAS...")
            try:
                # PASO 1: Navegar a login para establecer contexto
                driver.set_page_load_timeout(5)
                try:
                    # print("[SELENIUM] Navegando a login para verificar sesiones...")
                    driver.get(f"http://{self.host}/html/login_inter.html")
                    time.sleep(1)
                    
                    # Verificar si hay alerta de sesión activa Y ACEPTARLA
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        if "already" in alert_text.lower() or "logged" in alert_text.lower():
                            # print(f"[SELENIUM] ⚠️ Sesión activa detectada: '{alert_text[:60]}...'")
                            # print("[SELENIUM] Aceptando alerta para forzar cierre...")
                            alert.accept()
                            time.sleep(2)  # Esperar a que el servidor procese
                        else:
                            alert.accept()
                    except:
                        # print("[SELENIUM] No hay alerta de sesión activa")
                        pass
                except Exception as e:
                    # print(f"[SELENIUM] Error verificando login: {e}")
                    numero = 2
                
                # PASO 2: POST logout explícito usando JavaScript
                # print("[SELENIUM] Enviando comandos de logout...")
                logout_commands = [
                    f"fetch('http://{self.host}/cgi-bin/do_logout', {{method: 'POST', credentials: 'include'}}).catch(() => {{}})",
                    f"fetch('http://{self.host}/html/logout.html', {{method: 'GET', credentials: 'include'}}).catch(() => {{}})",
                    f"document.cookie.split(';').forEach(c => {{document.cookie = c.trim().split('=')[0] + '=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/;'}})"
                ]
                
                for cmd in logout_commands:
                    try:
                        driver.execute_script(cmd)
                        time.sleep(0.3)
                    except:
                        pass
                
                # PASO 3: Limpiar cookies del navegador
                driver.delete_all_cookies()
                # print("[SELENIUM] Cookies eliminadas")
                
                # PASO 4: Recargar página de login LIMPIA
                # print("[SELENIUM] Recargando login limpio...")
                driver.get(f"http://{self.host}/html/login_inter.html")
                time.sleep(1)
                
                # PASO 5: Verificar si TODAVÍA hay alerta
                try:
                    alert = driver.switch_to.alert
                    # print(f"[SELENIUM] ⚠️ ALERTA PERSISTENTE: {alert.text[:60]}")
                    alert.accept()
                    time.sleep(2)
                    
                    # Si persiste, esperar más tiempo para que el servidor libere la sesión
                    # print("[SELENIUM] Esperando 5s para que el servidor libere sesión...")
                    time.sleep(5)
                    
                    # Recargar una vez más
                    driver.get(f"http://{self.host}/html/login_inter.html")
                    time.sleep(1)
                except:
                    # print("[SELENIUM] ✓ Login limpio - sin alertas")
                    numero = 3
                
                driver.set_page_load_timeout(30)  # Restaurar timeout
                # print("[SELENIUM] ✓ Limpieza de sesiones completada")
                
            except Exception as e:
                # print(f"[WARN] Error en limpieza previa: {e}")
                numero = 3
            # -----------------------------------

            # Ya estamos en la página de login después de la limpieza
            # Esperar a que cargue completamente
            wait = WebDriverWait(driver, 10)
            
            # 2. Ingresar credenciales
            # Fiberhome suele usar 'user_name' y 'loginpp' o 'password'
            try:
                user_field = wait.until(EC.presence_of_element_located((By.ID, "user_name")))
                # print("[SELENIUM] Campo username encontrado: id='user_name'")
                user_field.clear()
                user_field.send_keys('root')
                
                try:
                    pass_field = driver.find_element(By.ID, "loginpp")
                    # print("[SELENIUM] Campo password encontrado: id='loginpp'")
                except:
                    pass_field = driver.find_element(By.ID, "password")
                    # print("[SELENIUM] Campo password encontrado: id='password'")
                
                pass_field.clear()
                pass_field.send_keys('golondrin0s1')
                
                # 3. Click Login
                # Intentar varios IDs comunes para el botón
                login_btn = None
                for btn_id in ["login_btn", "login", "LoginId"]:
                    try:
                        login_btn = driver.find_element(By.ID, btn_id)
                        # print(f"[SELENIUM] Botón login encontrado: id='{btn_id}'")
                        break
                    except:
                        continue
                
                if login_btn:
                    login_btn.click()
                    
                    # Verificar si hay alerta de "Usuario ya logueado"
                    try:
                        WebDriverWait(driver, 3).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        # print(f"[SELENIUM] Alerta tras login: {alert.text}")
                        alert.accept()
                        time.sleep(1)
                    except:
                        pass
                else:
                    # print("[ERROR] No se encontró botón de login")
                    return False
                
            except TimeoutException:
                # print("[ERROR] No se encontraron campos de login Fiberhome")
                return False
            
            # 4. Verificar login exitoso
            time.sleep(3)
            current_url = driver.current_url
            # print(f"[DEBUG] URL actual tras login: {current_url}")
            
            if "login_inter.html" in current_url or "login" in current_url.split('/')[-1]:
                # print("[WARNING] URL no cambió tras click. Intentando ENTER en password...")
                try:
                    from selenium.webdriver.common.keys import Keys
                    pass_field.send_keys(Keys.ENTER)
                    time.sleep(3)
                    
                    # Verificar alerta de nuevo
                    try:
                        WebDriverWait(driver, 3).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        # print(f"[SELENIUM] Alerta tras ENTER: {alert.text}")
                        alert.accept()
                        time.sleep(1)
                    except:
                        pass
                        
                    current_url = driver.current_url
                except Exception as e:
                    # print(f"[ERROR] Falló intento de ENTER: {e}")
                    numero = 3

            if "login_inter.html" not in current_url and "login" not in current_url.split('/')[-1]:
                # print("[AUTH] Login Fiberhome exitoso (URL cambió)")
                
                # Obtener cookies para requests
                selenium_cookies = driver.get_cookies()
                for cookie in selenium_cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                
                return True
            else:
                # print(f"[ERROR] Login fallido, seguimos en login page ({current_url})")
                
                # Verificar si es por sesión activa
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    page_source = driver.page_source.lower()
                    
                    if "already" in body_text or "logged" in body_text or "sesión" in page_source:
                        # print("[AUTH] ⚠️ SESIÓN ACTIVA DETECTADA - Intentando forzar cierre...")
                        
                        # Intentar URLs de logout
                        logout_urls = [
                            f"http://{self.host}/cgi-bin/do_logout",
                            f"http://{self.host}/html/logout.html",
                            f"http://{self.host}/logout"
                        ]
                        
                        for url in logout_urls:
                            try:
                                driver.get(url)
                                time.sleep(1)
                            except:
                                pass
                        
                        # Limpiar cookies de nuevo
                        driver.delete_all_cookies()
                        
                        # print("[AUTH] Esperando 5s para que servidor libere sesión...")
                        time.sleep(5)
                        
                        # print("[AUTH] REINTENTANDO LOGIN...")
                        driver.get(f"http://{self.host}/html/login_inter.html")
                        time.sleep(2)
                        
                        # REINTENTAR LOGIN COMPLETO
                        try:
                            # Esperar y verificar alerta
                            try:
                                alert = driver.switch_to.alert
                                # print(f"[AUTH] Alerta detectada: {alert.text[:60]}")
                                alert.accept()
                                time.sleep(2)
                            except:
                                pass
                            
                            # Reingresar credenciales
                            wait = WebDriverWait(driver, 10)
                            user_field = wait.until(EC.presence_of_element_located((By.ID, "user_name")))
                            user_field.clear()
                            user_field.send_keys('root')
                            
                            try:
                                pass_field = driver.find_element(By.ID, "loginpp")
                            except:
                                pass_field = driver.find_element(By.ID, "password")
                            
                            pass_field.clear()
                            pass_field.send_keys('golondrin0s1')
                            
                            # Click login
                            login_btn = None
                            for btn_id in ["login_btn", "login", "LoginId"]:
                                try:
                                    login_btn = driver.find_element(By.ID, btn_id)
                                    break
                                except:
                                    continue
                            
                            if login_btn:
                                login_btn.click()
                                time.sleep(3)
                                
                                # Verificar éxito
                                current_url = driver.current_url
                                if "login_inter.html" not in current_url:
                                    # print("[AUTH] ✓ LOGIN EXITOSO tras reintento")
                                    
                                    # Cookies
                                    selenium_cookies = driver.get_cookies()
                                    for cookie in selenium_cookies:
                                        self.session.cookies.set(cookie['name'], cookie['value'])
                                    
                                    return True
                                else:
                                    # print("[ERROR] Reintento falló - sesión aún activa")
                                    # print("[INFO] Cierre manualmente la sesión desde otro navegador o espere timeout")
                                    return False
                        except Exception as e:
                            # print(f"[ERROR] Error en reintento: {e}")
                            return False
                except Exception as e:
                    # print(f"[ERROR] Error verificando sesión: {e}")
                    pass
                    
                return False
                
        except Exception as e:
            # print(f"[ERROR] Excepción en login Fiberhome: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return False

    def _selenium_get_wifi_clients(self) -> List[Dict[str, Any]]:
        """
        Usa Selenium para navegar a:
        Status -> Wireless Status -> WIFI Client List
        y devuelve la lista de clientes WiFi (MAC, IP, SSID, Host).
        """
        if not SELENIUM_AVAILABLE:
            # print("[ERROR] Selenium no está disponible para Fiberhome")
            return []

        # Asegurarnos de tener driver logueado
        if not self.driver:
            # print("[DEBUG] No hay driver activo, intentando _login_fiberhome()...")
            if not self._login_fiberhome():
                # print("[ERROR] No se pudo iniciar sesión Fiberhome con Selenium")
                return []

        driver = self.driver
        wait = WebDriverWait(driver, 10)

        try:
            driver.switch_to.default_content()

            # 1) Top menu: Status
            # print("[WIFI CLIENTS] Navegando a Status...")
            status_menu = self.find_element_anywhere(
                driver,
                By.ID,
                "first_menu_status"
            ) or self.find_element_anywhere(
                driver,
                By.LINK_TEXT,
                "Status"
            )
            if status_menu:
                status_menu.click()
                time.sleep(1)
            else:
                # print("[ERROR] No se encontró menú Status")
                return []

            # 2) Left menu: Wireless Status
            # print("[WIFI CLIENTS] Navegando a Wireless Status...")
            wireless_menu = self.find_element_anywhere(
                driver,
                By.ID,
                "span_wireless_state"
            ) or self.find_element_anywhere(
                driver,
                By.XPATH,
                "//*[contains(text(), 'Wireless Status')]"
            )
            if wireless_menu:
                wireless_menu.click()
                time.sleep(1)
            else:
                # print("[ERROR] No se encontró Wireless Status")
                return []

            # 3) Third menu: WIFI Client List
            # print("[WIFI CLIENTS] Navegando a WIFI Client List...")
            client_list_menu = self.find_element_anywhere(
                driver,
                By.ID,
                "thr_wifi_mac_list"
            ) or self.find_element_anywhere(
                driver,
                By.XPATH,
                "//*[contains(text(), 'WIFI Client List')]"
            )


            if client_list_menu:
                client_list_menu.click()
                time.sleep(2)
            else:
                # print("[ERROR] No se encontró WIFI Client List")
                return []

            # ===== Buscar el frame que contiene la tabla =====
            driver.switch_to.default_content()

            frames = driver.find_elements(By.TAG_NAME, "frame") + \
                     driver.find_elements(By.TAG_NAME, "iframe")
            # print(f"[WIFI CLIENTS] Detectados {len(frames)} frames/iframes")

            target_html = None

            if not frames:
                # Sin frames: usar page_source tal cual
                target_html = driver.page_source
            else:
                for idx, frame in enumerate(frames):
                    try:
                        driver.switch_to.default_content()
                        driver.switch_to.frame(frame)
                        html = driver.page_source
                        if ("WIFI Client List" in html or
                            "WIFI Clients List" in html):
                            # print(f"[WIFI CLIENTS] Tabla encontrada en frame índice {idx}")
                            target_html = html
                            break
                    except Exception as e:
                        # print(f"[DEBUG] Error al inspeccionar frame {idx}: {e}")
                        continue

            if target_html is None:
                # Fallback: usar contenido actual
                # print("[WIFI CLIENTS] No se encontró texto 'WIFI Client List' en frames, usando page_source actual")
                target_html = driver.page_source

            soup = BeautifulSoup(target_html, "html.parser")
            clients: List[Dict[str, Any]] = []

            # Vamos a recorrer todas las filas y detectar banda (2.4G / 5G)
            current_band: Optional[str] = None

            for row in soup.find_all("tr"):
                # Texto completo de la fila (sirve para detectar los títulos)
                row_text = row.get_text(" ", strip=True)

                # Detectar cambio de sección
                if "2.4G WIFI Clients List" in row_text:
                    current_band = "2.4G"
                    continue
                if "5G WIFI Clients List" in row_text:
                    current_band = "5G"
                    continue

                cells = row.find_all("td")
                # Las filas útiles tienen al menos: ID, SSID, Host, MAC, IP
                if len(cells) < 5:
                    continue

                # Texto de cada celda
                values = [c.get_text(strip=True) for c in cells]

                # Saltar fila de encabezado (ID / SSID / Host Name / MAC / IP...)
                if values[0].upper() == "ID" and "MAC" in [v.upper() for v in values]:
                    continue

                mac = values[3].strip()  # por layout: ID, SSID, Host, MAC, IP, Rate...

                # Saltar filas sin MAC real
                if not mac or mac.upper() == "MAC":
                    continue

                client: Dict[str, Any] = {
                    "band": current_band,           # "2.4G" o "5G"
                    "id": values[0],
                    "ssid": values[1],
                    "host_name": values[2],
                    "mac": mac,
                    "ip": values[4],
                }

                # Si hay columna de velocidad (Receiving Rate)
                if len(values) > 5:
                    client["rate"] = values[5]

                clients.append(client)

            print(f"[WIFI CLIENTS] Se encontraron {len(clients)} clientes WiFi")
            return clients

        except Exception as e:
            # print(f"[ERROR] Excepción obteniendo WIFI Client List: {e}")
            return []

    def _normalize_mac(self, mac: str) -> str:
        """
        Normaliza una MAC:
        - quita :, -, espacios, puntos
        - la pasa a minúsculas
        Resultado: 'a45e60123456'
        """
        mac = mac.strip().lower()
        mac = re.sub(r'[^0-9a-f]', '', mac)
        return mac

    def _load_mac_whitelist(self, path: str) -> Set[str]:
        """
        Lee un archivo .txt con una MAC por línea y devuelve
        un set de MACs normalizadas.
        Líneas vacías o que empiezan con # se ignoran.
        """
        allowed: Set[str] = set()
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    allowed.add(self._normalize_mac(line))
        except FileNotFoundError:
            # print(f"[WIFI CLIENTS] No se encontró whitelist MAC: {path}")
            numero = 1
        return allowed

    def test_wifi_clients(self) -> Dict[str, Any]:
        """
        Test: Obtener lista de clientes WiFi (MACs conectadas) en Fiberhome
        y compararlas contra un archivo de MACs permitidas.
        """
        # print("[TEST] WIFI CLIENTS - Lista de clientes WiFi")

        result: Dict[str, Any] = {
            "name": "WIFI_CLIENTS",
            "status": "FAIL",
            "details": {
                "clients": [],
                "mac_list": [],
                "unauthorized_clients": [],
                "unauthorized_mac_list": [],
                "whitelist_path": None
            }
        }

        clients = self._selenium_get_wifi_clients()
        if not clients:
            result["details"]["error"] = "No se encontraron clientes WiFi o fallo la navegación"
            return result

        # --- COMPARAR CONTRA WHITELIST ---
        whitelist_path = "C:/Users/Admin/Desktop/macs_sin_desc.txt"  # ajusta la ruta real
        result["details"]["whitelist_path"] = whitelist_path

        allowed = self._load_mac_whitelist(whitelist_path)

        # Si no hay whitelist, solo regresamos la lista cruda
        if not allowed:
            # print("[WIFI CLIENTS] Whitelist vacía o no encontrada, no se hará filtrado")
            result["status"] = "PASS"
            result["details"]["clients"] = clients
            result["details"]["mac_list"] = [c["mac"] for c in clients]
            return result

        unauthorized_clients = []
        for c in clients:
            norm_mac = self._normalize_mac(c["mac"])
            if norm_mac not in allowed:
                unauthorized_clients.append(c)

        result["details"]["clients"] = clients
        result["details"]["mac_list"] = [c["mac"] for c in clients]
        result["details"]["unauthorized_clients"] = unauthorized_clients
        result["details"]["unauthorized_mac_list"] = [c["mac"] for c in unauthorized_clients]

        # Si NO hay MACs no permitidas -> PASS, si sí hay -> FAIL
        if unauthorized_clients:
            result["status"] = "FAIL"
            # print(f"[WIFI CLIENTS] MACs NO permitidas: {result['details']['unauthorized_mac_list']}")
        else:
            result["status"] = "PASS"
            # print("[WIFI CLIENTS] Todas las MAC están en la whitelist")

        return result

    def get_unauthorized_wifi_clients(self, whitelist_path: str) -> List[Dict[str, Any]]:
        """
        Devuelve la lista de clientes WiFi (con todos sus datos) cuya MAC
        NO está en el archivo de whitelist.
        """
        # 1) Obtener todos los clientes actuales del router
        clients = self._selenium_get_wifi_clients()
        if not clients:
            # print("[WIFI CLIENTS] No se encontraron clientes WiFi")
            return []

        # 2) Cargar whitelist
        allowed = self._load_mac_whitelist(whitelist_path)
        if not allowed:
            # print(f"[WIFI CLIENTS] Whitelist vacía o no encontrada: {whitelist_path}")
            # En este caso podrías devolver todos, pero aquí devuelvo lista vacía
            return []

        # 3) Filtrar clientes cuya MAC NO está permitida
        unauthorized: List[Dict[str, Any]] = []
        for c in clients:
            norm_mac = self._normalize_mac(c["mac"])
            if norm_mac not in allowed:
                unauthorized.append(c)

        # print(f"[WIFI CLIENTS] Clientes NO permitidos: {len(unauthorized)}")
        return unauthorized

# --- helpers para centrar ventanas ---

def centrar_en_pantalla(ventana, width, height):
    """Centra una ventana (Tk o CTk) en la pantalla."""
    pantalla_ancho  = ventana.winfo_screenwidth()
    pantalla_alto   = ventana.winfo_screenheight()

    x = (pantalla_ancho  - width)  // 2
    y = (pantalla_alto   - height) // 2

    ventana.geometry(f"{width}x{height}+{x}+{y}")

def centrar_sobre_padre(hijo, padre):
    """Centra un Toplevel sobre su ventana padre."""
    hijo.update_idletasks()   # asegurar que tenga tamaño real

    pw, ph = padre.winfo_width(),  padre.winfo_height()
    px, py = padre.winfo_x(),      padre.winfo_y()
    cw, ch = hijo.winfo_width(),   hijo.winfo_height()

    x = px + (pw - cw) // 2
    y = py + (ph - ch) // 2

    hijo.geometry(f"+{x}+{y}")

def temporal(app):
     # 1) Ventana de carga (modal ligera)
    loading = ct.CTkToplevel(app)
    loading.title("Por favor espera")
    loading.geometry("300x120")
    loading.resizable(False, False)

    msg = ct.CTkLabel(loading, text="Conectando al router...\nNo cierres la aplicación.")
    msg.pack(pady=10)

    bar = ct.CTkProgressBar(loading, mode="indeterminate")
    bar.pack(pady=10, padx=20, fill="x")
    bar.start()

    # Centrar sobre la ventana principal (opcional)
    loading.transient(app)
    loading.grab_set()  # bloquea interacción con la ventana principal

    centrar_sobre_padre(loading, app)
    def worker():
        # --- CÓDIGO PESADO AQUÍ (NO UI) ---
        obj = Mac(host="192.168.202.1", model=None)
        login_ok = obj._login_fiberhome()
        # ----------------------------------

        # De regreso al hilo de la UI
        def finish():
            loading.destroy()
            if login_ok:
                app.objClass = obj
                lbl = ct.CTkLabel(app, text="Login exitoso", fg_color="transparent")
                lbl.grid(row=5, column=0, padx=20, pady=(0, 5), columnspan=2)
            else:
                lbl = ct.CTkLabel(app, text="Error en login", fg_color="transparent")
                lbl.grid(row=5, column=0, padx=20, pady=(0, 5), columnspan=2)

        app.after(0, finish)

    # Lanzar hilo
    t = threading.Thread(target=worker, daemon=True)
    t.start()
        
def mostrar_tabla_baneados(app, bans):
    """
    Crea (o reemplaza) una tabla con scroll que muestra los dispositivos no permitidos.
    'bans' debe ser una lista de dicts (mac, ip, hostname, ssid, etc.).
    """

    # Si ya había una tabla anterior, la destruimos
    if hasattr(app, "bans_frame") and app.bans_frame is not None:
        app.bans_frame.destroy()

    # Marco con scroll
    frame = ct.CTkScrollableFrame(app, width=540, height=200)
    frame.grid(row=7, column=0, columnspan=2,
               padx=20, pady=(5, 20), sticky="nsew")

    app.bans_frame = frame  # guardamos referencia por si luego queremos borrarla

    # ---- Cabeceras de la tabla ----
    headers = ["MAC", "IP", "Nombre", "SSID"]
    for col, text in enumerate(headers):
        header_lbl = ct.CTkLabel(frame, text=text, fg_color="#1f538d")
        header_lbl.grid(row=0, column=col, padx=5, pady=5, sticky="ew")

    # Dar peso a las columnas para que se repartan el espacio
    for col in range(len(headers)):
        frame.grid_columnconfigure(col, weight=1)

    # ---- Filas con datos ----
    for row, dev in enumerate(bans, start=1):
        # Adaptar nombres de claves a lo que regrese tu función
        mac      = dev.get("mac") or dev.get("MAC") or ""
        ip       = dev.get("ip") or dev.get("IP") or ""
        hostname = dev.get("host_name") or dev.get("name") or ""
        ssid     = dev.get("ssid") or dev.get("ESSID") or ""

        ct.CTkLabel(frame, text=mac).grid(     row=row, column=0, padx=5, pady=2, sticky="ew")
        ct.CTkLabel(frame, text=ip).grid(      row=row, column=1, padx=5, pady=2, sticky="ew")
        ct.CTkLabel(frame, text=hostname).grid(row=row, column=2, padx=5, pady=2, sticky="ew")
        ct.CTkLabel(frame, text=ssid).grid(    row=row, column=3, padx=5, pady=2, sticky="ew")

def macsLabel(app):
    objClass = Mac(host="192.168.202.1", model=None)

    """Escanea clientes WiFi y busca MACs no permitidas en un hilo aparte."""

    # Seguridad: verificar que ya exista el objeto del router
    if not hasattr(app, "objClass"):
        aviso = ct.CTkLabel(app, text="Primero inicia sesión en el router.", fg_color="transparent")
        aviso.grid(row=6, column=0, columnspan=2, padx=20, pady=(10, 5))
        return

    # 1) Ventanita de carga
    loading = ct.CTkToplevel(app)
    loading.title("Por favor espera")
    loading.geometry("340x130")

    msg = ct.CTkLabel(
        loading,
        text="Escaneando clientes WiFi...\nEsto puede tardar unos segundos."
    )
    msg.pack(pady=10)

    bar = ct.CTkProgressBar(loading, mode="indeterminate")
    bar.pack(pady=10, padx=20, fill="x")
    bar.start()

    loading.transient(app)
    loading.grab_set()  # bloquear la ventana principal mientras tanto

    # Si ya tienes esta función, úsala:
    try:
        centrar_sobre_padre(loading, app)
    except NameError:
        pass  # si no la tienes definida, simplemente ignora

    def worker():
        """Código pesado que corre en otro hilo (sin tocar la UI)."""
        obj = app.objClass

        try:
            macs = obj._load_mac_whitelist("C:/Users/Admin/Desktop/macs_sin_desc.txt")
            resultado = obj.test_wifi_clients()
            bans = obj.get_unauthorized_wifi_clients("C:/Users/Admin/Desktop/macs_sin_desc.txt")
        except Exception as e:
            error_msg = str(e)

            def finish_error():
                loading.destroy()
                lbl = ct.CTkLabel(
                    app,
                    text=f"Error al escanear: {error_msg}",
                    fg_color="transparent"
                )
                lbl.grid(row=6, column=0, columnspan=2, padx=20, pady=(10, 5))

            app.after(0, finish_error)
            return

        # Si todo salió bien
        def finish_ok():
            loading.destroy()

            # Guardar resultados en la app por si los quieres usar después
            app.macs_whitelist = macs
            app.scan_result = resultado
            app.banned_macs = bans

            texto = f"Dispositivos no permitidos encontrados: {len(bans)}"
            lbl = ct.CTkLabel(app, text=texto, fg_color="transparent")
            lbl.grid(row=6, column=0, columnspan=2, padx=20, pady=(10, 5))
            # print(bans)
            mostrar_tabla_baneados(app, bans)
        app.after(0, finish_ok)

    # Lanzar hilo
    t = threading.Thread(target=worker, daemon=True)
    t.start()

def main():
    # Script para verificar los usuarios conectados en una red (fiberhome / para la oficina)
    
        # print(bans)
        # # print(resultado)

    # Necesarios para la interfaz
    app = ct.CTk()
    centrar_en_pantalla(app, 600, 550)
    app.title("BUSQUEDA DE DISPOSITIVOS INTRUSOS")
    app.grid_columnconfigure((0,1), weight=1)

    my_image = ct.CTkImage(light_image=Image.open("C:/Users/Admin/Pictures/ram.jpeg"),
                                  dark_image=Image.open("C:/Users/Admin/Pictures/ram.jpeg"),
                                  size=(70, 70))

    image_label = ct.CTkLabel(app, image=my_image, text="")  
    image_label.grid(row=0, column=0, padx=20, pady=20, columnspan=2)
    titulo = ct.CTkLabel(app, text="BUSQUEDA DE DISPOSITIVOS INTRUSOS", fg_color="transparent")
    titulo.configure(font=("Arial",20))
    titulo.grid(row=1, column=0, padx=20, pady=5, columnspan=2)
    label = ct.CTkLabel(app, text="Escanear macs en red Totalplay-5G-6630 y r2.4", fg_color="transparent")
    label.grid(row=2, column=0, padx=20,  pady=(0, 5))
    modelo = ct.CTkLabel(app, text="Router tipo FiberHome", fg_color="transparent")
    modelo.grid(row=2, column=1, padx=20,  pady=(0, 5))

    #botones para iniciar sesion y escanear
    sesionBtn = ct.CTkButton(app, text="Iniciar sesión", command=lambda: temporal(app)) #lambda para que no ejecute luego luego
    sesionBtn.grid(row=4, column=0, padx=20,  pady=(0, 5))

    escanearBtn = ct.CTkButton(app, text="Escanear macs prohibidas", command=lambda: macsLabel(app))
    escanearBtn.grid(row=4, column=1, padx=20,  pady=(0, 5))

    pathText = "La lista de macs permitidas debe estar en: C:/Users/Admin/Desktop/macs_sin_desc.txt"
    labelPath =ct.CTkLabel(app, text=pathText, fg_color="transparent")
    labelPath.grid(row=3, column=0, padx=20,  pady=(0, 5), columnspan=2)
    app.mainloop()

if __name__ == "__main__":
    main()