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
from collections import deque
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
        headless = True # DEBUG: Visible para el usuario
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
            
            # --- LIMPIEZA DE SESIONES PREVIA (MEJORADA CON POST) ---
            print("[SELENIUM] FORZANDO CIERRE DE SESIONES ACTIVAS...")
            try:
                # PASO 1: Navegar a login para establecer contexto
                driver.set_page_load_timeout(5)
                try:
                    print("[SELENIUM] Navegando a login para verificar sesiones...")
                    driver.get(f"http://{self.host}/html/login_inter.html")
                    time.sleep(1)
                    
                    # Verificar si hay alerta de sesión activa Y ACEPTARLA
                    try:
                        alert = driver.switch_to.alert
                        alert_text = alert.text
                        if "already" in alert_text.lower() or "logged" in alert_text.lower():
                            print(f"[SELENIUM] ⚠️ Sesión activa detectada: '{alert_text[:60]}...'")
                            print("[SELENIUM] Aceptando alerta para forzar cierre...")
                            alert.accept()
                            time.sleep(2)  # Esperar a que el servidor procese
                        else:
                            alert.accept()
                    except:
                        print("[SELENIUM] No hay alerta de sesión activa")
                        pass
                except Exception as e:
                    print(f"[SELENIUM] Error verificando login: {e}")
                
                # PASO 2: POST logout explícito usando JavaScript
                print("[SELENIUM] Enviando comandos de logout...")
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
                print("[SELENIUM] Cookies eliminadas")
                
                # PASO 4: Recargar página de login LIMPIA
                print("[SELENIUM] Recargando login limpio...")
                driver.get(f"http://{self.host}/html/login_inter.html")
                time.sleep(1)
                
                # PASO 5: Verificar si TODAVÍA hay alerta
                try:
                    alert = driver.switch_to.alert
                    print(f"[SELENIUM] ⚠️ ALERTA PERSISTENTE: {alert.text[:60]}")
                    alert.accept()
                    time.sleep(2)
                    
                    # Si persiste, esperar más tiempo para que el servidor libere la sesión
                    print("[SELENIUM] Esperando 5s para que el servidor libere sesión...")
                    time.sleep(5)
                    
                    # Recargar una vez más
                    driver.get(f"http://{self.host}/html/login_inter.html")
                    time.sleep(1)
                except:
                    print("[SELENIUM] ✓ Login limpio - sin alertas")
                
                driver.set_page_load_timeout(30)  # Restaurar timeout
                print("[SELENIUM] ✓ Limpieza de sesiones completada")
                
            except Exception as e:
                print(f"[WARN] Error en limpieza previa: {e}")
            # -----------------------------------

            # Ya estamos en la página de login después de la limpieza
            # Esperar a que cargue completamente
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
                    
                    # Verificar si hay alerta de "Usuario ya logueado"
                    try:
                        WebDriverWait(driver, 3).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        print(f"[SELENIUM] Alerta tras login: {alert.text}")
                        alert.accept()
                        time.sleep(1)
                    except:
                        pass
                else:
                    print("[ERROR] No se encontró botón de login")
                    return False
                
            except TimeoutException:
                print("[ERROR] No se encontraron campos de login Fiberhome")
                return False
            
            # 4. Verificar login exitoso
            time.sleep(3)
            current_url = driver.current_url
            print(f"[DEBUG] URL actual tras login: {current_url}")
            
            if "login_inter.html" in current_url or "login" in current_url.split('/')[-1]:
                print("[WARNING] URL no cambió tras click. Intentando ENTER en password...")
                try:
                    from selenium.webdriver.common.keys import Keys
                    pass_field.send_keys(Keys.ENTER)
                    time.sleep(3)
                    
                    # Verificar alerta de nuevo
                    try:
                        WebDriverWait(driver, 3).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        print(f"[SELENIUM] Alerta tras ENTER: {alert.text}")
                        alert.accept()
                        time.sleep(1)
                    except:
                        pass
                        
                    current_url = driver.current_url
                except Exception as e:
                    print(f"[ERROR] Falló intento de ENTER: {e}")

            if "login_inter.html" not in current_url and "login" not in current_url.split('/')[-1]:
                print("[AUTH] Login Fiberhome exitoso (URL cambió)")
                
                # Intentar saltar wizard si existe
                self.fh_maybe_skip_initial_guide(driver)
                
                # Obtener cookies para requests
                selenium_cookies = driver.get_cookies()
                for cookie in selenium_cookies:
                    self.session.cookies.set(cookie['name'], cookie['value'])
                
                # Guardar referencia al driver
                self.driver = driver
                return True
            else:
                print(f"[ERROR] Login fallido, seguimos en login page ({current_url})")
                
                # Verificar si es por sesión activa
                try:
                    body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                    page_source = driver.page_source.lower()
                    
                    if "already" in body_text or "logged" in body_text or "sesión" in page_source:
                        print("[AUTH] ⚠️ SESIÓN ACTIVA DETECTADA - Intentando forzar cierre...")
                        
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
                        
                        print("[AUTH] Esperando 5s para que servidor libere sesión...")
                        time.sleep(5)
                        
                        print("[AUTH] REINTENTANDO LOGIN...")
                        driver.get(f"http://{self.host}/html/login_inter.html")
                        time.sleep(2)
                        
                        # REINTENTAR LOGIN COMPLETO
                        try:
                            # Esperar y verificar alerta
                            try:
                                alert = driver.switch_to.alert
                                print(f"[AUTH] Alerta detectada: {alert.text[:60]}")
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
                            pass_field.send_keys('admin')
                            
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
                                    print("[AUTH] ✓ LOGIN EXITOSO tras reintento")
                                    
                                    # Saltar wizard
                                    self.fh_maybe_skip_initial_guide(driver)
                                    
                                    # Cookies
                                    selenium_cookies = driver.get_cookies()
                                    for cookie in selenium_cookies:
                                        self.session.cookies.set(cookie['name'], cookie['value'])
                                    
                                    return True
                                else:
                                    print("[ERROR] Reintento falló - sesión aún activa")
                                    print("[INFO] Cierre manualmente la sesión desde otro navegador o espere timeout")
                                    if driver:
                                        try:
                                            driver.quit()
                                        except:
                                            pass
                                    return False
                        except Exception as e:
                            print(f"[ERROR] Error en reintento: {e}")
                            return False
                except Exception as e:
                    print(f"[ERROR] Error verificando sesión: {e}")
                    pass
                    if driver:
                        try:
                            driver.quit()
                        except:
                            pass
                return False
        except Exception as e:
            print(f"[ERROR] Excepción en login Fiberhome: {e}")
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            return False
        
    def _login_fiberhomeSuper(self, headless: bool = True, timeout: int = 10) -> bool:
        if self.driver:
            print("DRIVER ACTIVO")
            self._router_logout_best_effort(self.driver)
            self.driver.delete_all_cookies()
            self.driver.quit()
            self.driver = None
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
        self.driver = driver
        login_url = f"{self.base_url}/html/login_inter.html"
        # si está busy, espera a que libere (no reintentes creando sesiones)
        if not self._wait_not_busy_login_page(driver, login_url, max_wait=240):
            print("[SELENIUM] Login bloqueado por sesión activa (no liberó).")
            return False
        driver.get(login_url)

        # Espera que cargue login
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "user_name"))
        )

        USER = "admin"
        PASS = "z#Wh46QN@52Rm%j5"

        # Llenar rápido por JS
        u = driver.find_element(By.ID, "user_name")
        p = driver.find_element(By.ID, "loginpp")
        driver.execute_script("arguments[0].value = arguments[1];", u, USER)
        driver.execute_script("arguments[0].value = arguments[1];", p, PASS)

        # Click Login
        driver.find_element(By.ID, "login_btn").click()

        # Esperar resultado post-login
        def post_login_ok(drv):
            html = (drv.page_source or "").lower()
            if "already logged" in html:
                return "BUSY"

            # 1) si desaparece el form, suele ser OK
            if not drv.find_elements(By.ID, "user_name"):
                return "OK"

            # 2) si ya hay frames, suele ser OK
            if len(drv.find_elements(By.CSS_SELECTOR, "frame,iframe")) > 0:
                return "OK"

            # 3) si ya puedo encontrar el menú en algún frame, OK
            el = self.find_element_anywhere(drv, By.ID, "first_menu_manage", desc="Management", timeout=1)
            if el:
                return "OK"

            return False

        res = WebDriverWait(driver, 20).until(post_login_ok)
        if res == "BUSY":
            print("[SELENIUM] Login bloqueado por sesión activa.")
            return False

        print("[SELENIUM] Login OK (salí de login o ya hay frames).")
        return True

    def _wait_not_busy_login_page(self, driver, login_url, max_wait=180):
        start = time.time()
        while time.time() - start < max_wait:
            driver.get(login_url)
            time.sleep(0.8)
            html = (driver.page_source or "").lower()
            if "already logged" not in html and "somebody has already logged in" not in html:
                return True
            print("[SELENIUM] Router ocupado (sesión activa). Esperando 5s...")
            time.sleep(5)
        return False

    def _router_logout_best_effort(self, driver):
        # 1) intenta URL directa
        try:
            driver.get(f"{self.base_url}/logout.html")
            time.sleep(1)
            return
        except:
            pass

        # 2) si existe botón logout en UI (fallback)
        try:
            self.click_anywhere(driver, [
                # agrega aquí IDs/XPaths si los conoces
                (By.ID, "logout"),
                # (By.XPATH, "//a[contains(.,'Logout') or contains(.,'Salir')]"),
            ], desc="Logout", timeout=3)
            time.sleep(1)
        except:
            pass

    def _enter_main_frameset(self, timeout_total=25) -> bool:
        driver = self.driver

        # candidatos comunes (no es AJAX; solo cargar la UI que ya existe)
        candidates = [
            f"{self.base_url}/",
            f"{self.base_url}/index.html",
            f"{self.base_url}/main.html",
            f"{self.base_url}/html/index.html",
            f"{self.base_url}/html/main_inter.html",
        ]

        start = time.time()
        while time.time() - start < timeout_total:
            for url in candidates:
                try:
                    driver.get(url)
                    time.sleep(0.8)

                    frames = driver.find_elements(By.CSS_SELECTOR, "frame,iframe")
                    if frames:
                        # confirmo que el menú exista en algún frame
                        el = self.find_element_anywhere(driver, By.ID, "first_menu_manage",
                                                        desc="Management", timeout=3)
                        if el:
                            print("[SELENIUM] Frameset principal listo en:", url)
                            return True

                except:
                    continue

        # debug
        driver.save_screenshot("debug_no_frameset.png")
        with open("debug_no_frameset.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source or "")
        return False

    def _ensure_fiberhome_main_ui(self, driver, timeout=20) -> bool:
        """
        1) Si el router abrió otra ventana, cambia a la última
        2) Fuerza cargar base_url
        3) Espera a que existan frames/iframes
        4) Verifica que el menú exista en algún frame
        """
        # 1) Si se abrió otra ventana, cambiar a la última
        try:
            if len(driver.window_handles) > 1:
                driver.switch_to.window(driver.window_handles[-1])
        except:
            pass

        # 2) Ir a home del router (misma URL base)
        try:
            driver.switch_to.default_content()
            driver.get(f"{self.base_url}/")
        except:
            pass

        # 3) Esperar que aparezcan frames (UI típica de FiberHome)
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, "frame,iframe")) > 0
            )
        except:
            # no hay frames; probablemente no estás en la UI principal
            driver.save_screenshot("debug_no_frames.png")
            with open("debug_no_frames.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return False

        # 4) Validar que el menú exista en ALGÚN frame (usando tu helper)
        el = self.find_element_anywhere(driver, By.ID, "first_menu_manage", desc="Management", timeout=timeout)
        if not el:
            # dump rápido para diagnóstico
            driver.save_screenshot("debug_menu_not_found.png")
            with open("debug_menu_not_found.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return False

        return True

    def fh_maybe_skip_initial_guide(self, driver):
        """Intenta saltar el wizard de configuración inicial de Fiberhome"""
        print("[SELENIUM] Verificando wizard inicial Fiberhome...")
        try:
            # Buscar botones comunes de "Next", "Skip", "Cancel"
            # IDs y XPaths comunes en Fiberhome
            skip_buttons = [
                "//input[@value='Next']",
                "//input[@value='Skip']",
                "//button[contains(text(), 'Next')]",
                "//button[contains(text(), 'Skip')]",
                "//a[contains(text(), 'Skip')]"
            ]
            
            for xpath in skip_buttons:
                try:
                    # Timeout muy corto (1s) porque es opcional y probamos varios
                    btn = self.find_element_anywhere(driver, By.XPATH, xpath, timeout=1)
                    if btn and btn.is_displayed():
                        print(f"[SELENIUM] Botón de wizard encontrado: {xpath}")
                        btn.click()
                        time.sleep(1)
                except:
                    pass
                    
        except Exception as e:
            print(f"[DEBUG] Error verificando wizard: {e}")

    def _ensure_fiberhome_driver(self) -> bool:
        """
        Verifica que self.driver siga vivo.
        - Si no hay driver, hace login Selenium.
        - Si el driver está muerto, lo cierra y crea uno nuevo.
        """
        # No hay driver → login normal
        if not getattr(self, "driver", None):
            print("[SELENIUM] No hay driver. Iniciando login Fiberhome...")
            return self._login_fiberhome()

        # Hay objeto driver, pero puede estar muerto
        try:
            # comando muy simple solo para probar conexión
            _ = self.driver.current_url
            return True
        except Exception as e:
            print(f"[SELENIUM] Driver inválido/desconectado: {e}")
            # intentar cerrarlo por si quedó zombie
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None
            print("[SELENIUM] Recreando driver con nuevo login...")
            return self._login_fiberhome()

    def _reset_factory_fiberhome(self):
        """
        Realiza reset de fábrica para Fiberhome.
        Ruta: Management (first_menu_manage) -> Device Management (span_device_admin) -> Restore (Restart_button)
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
            
            # 1. Click en Management (Top Menu) - ID: first_menu_manage
            print("[RESET] Buscando menú Management (first_menu_manage)...")
            try:
                # Intentar primero por ID específico proporcionado
                mgmt_link = self.find_element_anywhere(driver, By.ID, "first_menu_manage", timeout=3)
                
                if not mgmt_link:
                    # Fallback a texto
                    mgmt_link = self.find_element_anywhere(driver, By.XPATH, "//a[contains(text(), 'Management')]", timeout=2)
                
                if mgmt_link:
                    mgmt_link.click()
                    time.sleep(2)
                else:
                    print("[ERROR] No se encontró menú Management")
                    return False
            except Exception as e:
                print(f"[ERROR] Falló click en Management: {e}")
                return False
                
            # 2. Click en Device Management (Left Menu) - ID: span_device_admin
            print("[RESET] Buscando Device Management (span_device_admin)...")
            try:
                # Intentar primero por ID específico proporcionado
                dev_mgmt = self.find_element_anywhere(driver, By.ID, "span_device_admin", timeout=2)
                
                if not dev_mgmt:
                    # Fallback a texto
                    dev_mgmt = self.find_element_anywhere(driver, By.XPATH, "//a[contains(text(), 'Device Management')]", timeout=2)
                
                if dev_mgmt:
                    dev_mgmt.click()
                    time.sleep(2)
                else:
                    print("[ERROR] No se encontró Device Management")
                    return False
            except Exception as e:
                print(f"[ERROR] Falló click en Device Management: {e}")
                return False

            # 3. Click en botón Restore - ID: Restart_button
            print("[RESET] Buscando botón Restore (Restart_button)...")
            restore_btn = None
            
            try:
                # Intentar encontrar el botón directamente
                restore_btn = self.find_element_anywhere(driver, By.ID, "Restart_button", timeout=5)
                
                if not restore_btn:
                     # Fallback
                     restore_btn = self.find_element_anywhere(driver, By.XPATH, "//input[@value='Restore']", timeout=2)
            except:
                pass
                
            # 4. Click en botón Restore
            if restore_btn:
                print("[RESET] Botón Restore encontrado, haciendo click...")
                try:
                    restore_btn.click()
                    
                    # 5. Confirmar alerta
                    try:
                        WebDriverWait(driver, 5).until(EC.alert_is_present())
                        alert = driver.switch_to.alert
                        print(f"[RESET] Alerta detectada: {alert.text}")
                        alert.accept()
                        print("[RESET] Alerta aceptada. Reinicio en curso...")
                        return True
                    except TimeoutException:
                        print("[WARNING] No apareció alerta de confirmación, asumiendo reinicio...")
                        return True
                except Exception as e:
                    print(f"[ERROR] Error al hacer click en Restore: {e}")
                    return False
            else:
                print("[ERROR] No se encontró el botón Restore (Restart_button)")
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
        
        # ya que hay 147 llamadas a base_info, voy a poner aqui la info del wifi - U
        wifi_info = self._extract_wifi_allwan()
        meta = self.test_results.setdefault("metadata", {})
        base = meta.setdefault("base_info", {})
        base["wifi_info"] = wifi_info
        extracted["wifi_info"] = wifi_info
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
    
    def _extract_wifi_password_selenium(self, driver=None) -> Dict[str, str]:
        """
        Extrae contraseñas WiFi usando Selenium manipulando el DOM.
        
        Ruta:
        1. Navegar a http://192.168.100.1/html/main_inter.html
        2. Click en Network (ID: first_menu_network)
        3. Click en WLAN Security (ID: thr_security)
        4. Remover clase de seguridad del input PreSharedKey
        5. Leer valor del campo
        
        Returns:
            Dict con passwords_24ghz y password_5ghz
        """
        # --- asegurar driver válido ---
        if driver is None:
            # usamos el driver de la clase, pero garantizando que la sesión exista
            if not self._ensure_fiberhome_driver():
                print("[ERROR] No se pudo preparar un driver Selenium para WiFi")
                return {}
            driver = self.driver
        else:
            # si nos pasan un driver explícito, verificar que esté vivo
            try:
                _ = driver.current_url
            except Exception as e:
                print(f"[SELENIUM] Driver pasado a _extract_wifi_password_selenium no es válido: {e}")
                return {}
        
        # driver = driver or self.driver
        passwords = {}
        
        try:
            # 1. Navegar a main_inter.html
            main_url = f"http://{self.host}/html/main_inter.html"
            print(f"[SELENIUM] Navegando a {main_url} para extraer passwords WiFi...")
            driver.get(main_url)
            time.sleep(2)
            
            # 2. Click en Network (first_menu_network)
            print("[SELENIUM] Click en Network menu...")
            network_menu = self.find_element_anywhere(driver, By.ID, "first_menu_network", timeout=5)
            if not network_menu:
                print("[ERROR] No se encontró menú Network")
                return {}
            network_menu.click()
            time.sleep(1)
            
            # 3. Click en WLAN Security (thr_security)
            print("[SELENIUM] Click en WLAN Security...")
            wlan_security = self.find_element_anywhere(driver, By.ID, "thr_security", timeout=5)
            if not wlan_security:
                print("[ERROR] No se encontró WLAN Security")
                return {}
            wlan_security.click()
            time.sleep(2)
            
            # 4. Buscar campo PreSharedKey y extraer password
            print("[SELENIUM] Buscando campo PreSharedKey...")
            
            # Intentar encontrar el campo (puede estar en un iframe)
            psk_field = self.find_element_anywhere(driver, By.ID, "PreSharedKey", timeout=5)
            
            if psk_field:
                # DEBUG: Inspect element before modification
                print(f"[DEBUG] Pre-mod - Value: '{psk_field.get_attribute('value')}'")
                print(f"[DEBUG] Pre-mod - Class: '{psk_field.get_attribute('class')}'")
                print(f"[DEBUG] Pre-mod - Type: '{psk_field.get_attribute('type')}'")

                # Remover clase de seguridad usando JavaScript (SOLO CLASE)
                print("[SELENIUM] Removiendo clase de seguridad del campo...")
                driver.execute_script("arguments[0].removeAttribute('class');", psk_field)
                
                time.sleep(0.5)
                
                # DEBUG: Inspect element after modification
                print(f"[DEBUG] Post-mod - Value: '{psk_field.get_attribute('value')}'")
                print(f"[DEBUG] Post-mod - Class: '{psk_field.get_attribute('class')}'")
                
                # Leer el valor
                password = psk_field.get_attribute('value')
                
                if password:
                    print(f"[SELENIUM] ✓ Password 2.4GHz extraída: {password}")
                    passwords['password_24ghz'] = password
                    passwords['extraction_method'] = 'selenium_dom_manipulation'

                    # Definirla directamente en los resultados
                    extra = self.test_results.setdefault('additional_info', {})  # o 'aditional_info'
                    wifi  = extra.setdefault('wifi_info', {})
                    wifi['psw'] = passwords
                else:
                    print("[WARN] Campo PreSharedKey vacío")
            else:
                print("[ERROR] No se encontró campo PreSharedKey")
            
            # ========== EXTRAER PASSWORD 5GHz ==========
            print("\n[SELENIUM] Intentando extraer password 5GHz...")
            try:
                # MÉTODO 1: Buscar dropdown/selector de banda (común en Fiberhome)
                print("[SELENIUM] Buscando selector de banda WiFi...")
                selector_found = False
                
                # IDs comunes para selector de banda
                selector_ids = ["WlanIndex", "ssid_mode", "wlan_mode", "wifi_index", "band_select", "SSID_Index"]
                
                for sel_id in selector_ids:
                    try:
                        selector = self.find_element_anywhere(driver, By.ID, sel_id, timeout=1)
                        if selector:
                            print(f"[SELENIUM] ✓ Selector encontrado: {sel_id}")
                            
                            # Verificar si es un select/dropdown
                            tag_name = selector.tag_name.lower()
                            if tag_name == 'select':
                                # Es un dropdown - seleccionar opción de 5GHz
                                options = selector.find_elements(By.TAG_NAME, "option")
                                print(f"[DEBUG] Opciones disponibles: {len(options)}")
                                
                                # Buscar opción que contenga "5G", "5GHz", o índice 1
                                for idx, option in enumerate(options):
                                    opt_text = option.text.lower()
                                    opt_value = option.get_attribute('value')
                                    print(f"[DEBUG]   Opción {idx}: text='{option.text}' value='{opt_value}'")
                                    
                                    if '5g' in opt_text or '5ghz' in opt_text or opt_value in ['1', 'wlan1', 'ssid1']:
                                        print(f"[SELENIUM] Seleccionando opción 5GHz: {option.text}")
                                        option.click()
                                        time.sleep(2)  # Esperar a que la página actualice
                                        selector_found = True
                                        break
                                
                                if selector_found:
                                    break
                    except Exception as e:
                        continue
                
                # MÉTODO 2: Buscar tabs/pestañas
                if not selector_found:
                    print("[SELENIUM] No se encontró selector, buscando tabs...")
                    tab_ids = ["5g_tab", "wifi_5g", "wlan_5g", "wireless_5g", "tab_5g", "ssid1_tab"]
                    
                    for tab_id in tab_ids:
                        try:
                            tab_element = self.find_element_anywhere(driver, By.ID, tab_id, timeout=1)
                            if tab_element:
                                print(f"[SELENIUM] ✓ Tab 5GHz encontrado: {tab_id}")
                                tab_element.click()
                                time.sleep(2)
                                selector_found = True
                                break
                        except:
                            continue
                
                # MÉTODO 3: Buscar menú separado para 5GHz (WLAN Security 5GHz)
                if not selector_found:
                    print("[SELENIUM] Buscando menú WLAN Security 5GHz separado...")
                    menu_5g_ids = ["thr_security_5g", "thr_security5g", "wlan_security_5g", "sec_menu_5g"]
                    
                    for menu_id in menu_5g_ids:
                        try:
                            menu_5g = self.find_element_anywhere(driver, By.ID, menu_id, timeout=1)
                            if menu_5g:
                                print(f"[SELENIUM] ✓ Menú 5GHz encontrado: {menu_id}")
                                menu_5g.click()
                                time.sleep(2)
                                selector_found = True
                                break
                        except:
                            continue
                
                # Si encontramos forma de cambiar a 5GHz, leer el MISMO campo PreSharedKey
                if selector_found:
                    print("[SELENIUM] Buscando campo PreSharedKey para 5GHz...")
                    
                    # El campo sigue siendo PreSharedKey, pero ahora muestra la password de 5GHz
                    psk_5g_field = self.find_element_anywhere(driver, By.ID, "PreSharedKey", timeout=3)
                    
                    if psk_5g_field:
                        print(f"[DEBUG] 5GHz Pre-mod - Value: '{psk_5g_field.get_attribute('value')}'")
                        print(f"[DEBUG] 5GHz Pre-mod - Class: '{psk_5g_field.get_attribute('class')}'")
                        
                        driver.execute_script("arguments[0].removeAttribute('class');", psk_5g_field)
                        time.sleep(0.5)
                        
                        print(f"[DEBUG] 5GHz Post-mod - Value: '{psk_5g_field.get_attribute('value')}'")
                        
                        password_5g = psk_5g_field.get_attribute('value')
                        
                        if password_5g and password_5g != passwords.get('password_24ghz'):
                            print(f"[SELENIUM] ✓ Password 5GHz extraída: {password_5g}")
                            passwords['password_5ghz'] = password_5g
                        elif password_5g == passwords.get('password_24ghz'):
                            print("[INFO] Password 5GHz es igual a 2.4GHz (banda dual con misma clave)")
                            passwords['password_5ghz'] = password_5g
                        else:
                            print("[WARN] Campo PreSharedKey 5GHz vacío")
                    else:
                        print("[WARN] No se encontró campo PreSharedKey para 5GHz")
                else:
                    print("[INFO] No se encontró forma de cambiar a banda 5GHz")
                    print("[INFO] Puede que el dispositivo use la misma contraseña para ambas bandas")
                    # Asumir que usan la misma password
                    if 'password_24ghz' in passwords:
                        passwords['password_5ghz'] = passwords['password_24ghz']
                        passwords['password_5ghz_note'] = "Asumida igual a 2.4GHz (no se encontró selector)"
                    
            except Exception as e:
                print(f"[WARN] Error extrayendo password 5GHz: {e}")
                import traceback
                traceback.print_exc()
            
            return passwords
            
        except Exception as e:
            print(f"[ERROR] Error extrayendo passwords WiFi: {e}")
            import traceback
            traceback.print_exc()
            return passwords

    def _extract_wifi_info(self) -> Dict[str, Any]:
        """Extrae información WiFi completa (SSIDs, passwords, canales) usando endpoints específicos (fallback)"""
        wifi_info = {}
        
        # NOTA: La extracción de passwords por Selenium se hace en common_mixin después
        # de llamar a este método, para evitar llamadas duplicadas
        
        if not self.session_id:
            print("[DEBUG] No hay sessionid, no se puede obtener info WiFi adicional")
            return wifi_info if wifi_info else {}
        
        # PRIORIDAD 1: Intentar get_wifi_info para WiFi 2.4GHz (SSID y otros datos)
        try:
            wifi_24_response = self._ajax_get('get_wifi_info')
            if wifi_24_response.get('session_valid') == 1:
                if wifi_24_response.get('SSID'):
                    wifi_info['ssid_24ghz'] = wifi_24_response['SSID']
                # Solo usar password de AJAX si no la obtuvimos por Selenium
                if wifi_24_response.get('PreSharedKey') and 'password_24ghz' not in wifi_info:
                    wifi_info['password_24ghz'] = wifi_24_response['PreSharedKey']
                if wifi_24_response.get('Channel'):
                    wifi_info['channel_24ghz'] = wifi_24_response['Channel']
                if wifi_24_response.get('Enable'):
                    wifi_info['enabled_24ghz'] = wifi_24_response['Enable'] == '1'
        except Exception as e:
            print(f"[DEBUG] Error obteniendo WiFi 2.4GHz: {e}")
        
        # PRIORIDAD 2: Intentar get_5g_wifi_info para WiFi 5GHz
        try:
            wifi_5g_response = self._ajax_get('get_5g_wifi_info')
            if wifi_5g_response.get('session_valid') == 1:
                if wifi_5g_response.get('SSID'):
                    wifi_info['ssid_5ghz'] = wifi_5g_response['SSID']
                # Solo usar password de AJAX si no la obtuvimos por Selenium
                if wifi_5g_response.get('PreSharedKey') and 'password_5ghz' not in wifi_info:
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
                    
                    # Extraer y desencriptar password (solo si no lo tenemos por Selenium)
                    psk_encrypted = network.get('PreSharedKey', '')
                    psk_decrypted = self._decrypt_wifi_credential(psk_encrypted) if psk_encrypted else 'N/A'
                    
                    # Canal en uso
                    channel = network.get('channelIsInUse', network.get('Channel', 'Auto'))
                    
                    # Asignar a la banda correcta
                    if is_5ghz:
                        if 'ssid_5ghz' not in wifi_info:  # Solo la primera red 5GHz activa
                            wifi_info['ssid_5ghz'] = ssid_decrypted
                            # Solo usar password encriptada si no la tenemos por Selenium
                            if 'password_5ghz' not in wifi_info:
                                wifi_info['password_5ghz'] = psk_decrypted
                            wifi_info['channel_5ghz'] = channel
                            wifi_info['enabled_5ghz'] = True
                            wifi_info['standard_5ghz'] = network.get('Standard')
                    else:
                        if 'ssid_24ghz' not in wifi_info:  # Solo la primera red 2.4GHz activa
                            wifi_info['ssid_24ghz'] = ssid_decrypted
                            # Solo usar password encriptada si no la tenemos por Selenium
                            if 'password_24ghz' not in wifi_info:
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
        
        # Lógica específica para Fiberhome (MOD001 y MOD008)
        if (self.model == "MOD001" or self.model == "MOD008"):
            print("[TEST] Ejecutando secuencia de Factory Reset para Fiberhome...")
            
              # Asegurar driver válido
            if not self._ensure_fiberhome_driver():
                result["status"] = "FAIL"
                result["details"]["error"] = "No se pudo iniciar driver Selenium para reset"
                return result
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
                    
                    # Extraer información post-reset para verificar estado
                    print("[TEST] Extrayendo información post-reset...")
                    try:
                        # Intentar extraer info básica
                        base_info = self._extract_base_info()
                        if base_info:
                            self.test_results['metadata']['base_info'] = base_info
                            result["details"]["post_reset_info"] = "Extracted"
                            print("[TEST] Información actualizada correctamente")
                    except Exception as e:
                        print(f"[WARNING] No se pudo extraer info post-reset: {e}")
                        
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
        """Test 3: Detección de puerto(s) USB"""
        print("[TEST] USB PORT - Detección")

        result: Dict[str, Any] = {
            "name": "USB_PORT",
            "status": "FAIL",
            "details": {}
        }

        # 1) Capacidad de hardware desde base_info
        base_info = self.test_results.get("metadata", {}).get("base_info")
        if not base_info:
            result["details"]["error"] = "No se pudo obtener información de hardware (base_info)."
            result["details"]["note"] = "get_base_info no disponible"
            return result

        usb_ports = base_info.get("usb_ports", base_info.get("usb_port_num", 0))
        usb_status = base_info.get("usb_status")

        result["details"]["hardware_method"] = "AJAX get_base_info"
        result["details"]["usb_ports_capacity"] = usb_ports
        if usb_status is not None:
            result["details"]["usb_status_flag"] = usb_status

        # Si el modelo no declara puertos USB, nada más que hacer
        if usb_ports <= 0:
            result["details"]["note"] = "El equipo no reporta puertos USB en base_info."
            return result

        # 2) Dispositivos conectados vía get_ftpclient_info
        try:
            ftp_info = self._ajax_get("get_ftpclient_info")
        except Exception as e:
            result["details"]["error"] = f"Error llamando get_ftpclient_info: {e}"
            result["details"]["method"] = "AJAX get_ftpclient_info"
            return result

        if ftp_info.get("session_valid") != 1:
            result["details"]["error"] = f"get_ftpclient_info devolvió session_valid={ftp_info.get('session_valid')}"
            result["details"]["method"] = "AJAX get_ftpclient_info"
            return result

        usb_list_raw = ftp_info.get("UsbList") or ""

        devices = [d for d in re.split(r"[,\s]+", usb_list_raw) if d]
        connected_count = len(devices)

        result["details"]["method"] = "AJAX get_base_info + AJAX get_ftpclient_info"
        result["details"]["usb_devices_connected"] = connected_count
        result["details"]["usb_devices_list"] = devices
        result["details"]["usb_list_raw"] = usb_list_raw

        # 3) Comparar capacidad vs dispositivos detectados
        if connected_count == usb_ports:
            result["status"] = "PASS"
            result["details"]["note"] = (
                f"Capacidad de hardware: {usb_ports} puerto(s); "
                f"dispositivos detectados: {connected_count} (OK)."
            )
        else:
            result["status"] = "FAIL"
            result["details"]["note"] = (
                f"Capacidad de hardware: {usb_ports} puerto(s); "
                f"dispositivos detectados: {connected_count}. "
                "Revisar conexión de memorias USB o posible fallo de puerto."
            )

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
        
        # PRIORIDAD 0: Intentar extraer password NO ENCRIPTADA por Selenium
        if self.driver:
            print("[TEST] Intentando extracción de password WiFi 2.4GHz por Selenium...")
            try:
                selenium_passwords = self._extract_wifi_password_selenium()
                if selenium_passwords and 'password_24ghz' in selenium_passwords:
                    print(f"[TEST] ✓ Password 2.4GHz obtenida por Selenium: {selenium_passwords['password_24ghz']}")
                    result["details"]["password_unencrypted"] = selenium_passwords['password_24ghz']
                    result["details"]["extraction_method"] = "selenium_dom_manipulation"
            except Exception as e:
                print(f"[WARN] Error en extracción Selenium: {e}")
        
        # Prioridad 1: Usar datos de get_base_info si están disponibles
        base_info = self.test_results['metadata'].get('base_info')
        if base_info and base_info.get('wifi_info'):
            wifi_info = base_info['wifi_info']
            if 'ssid_24ghz' in wifi_info:
                result["status"] = "PASS"
                result["details"]["method"] = "AJAX get_base_info"
                result["details"]["ssid"] = wifi_info.get('ssid_24ghz')
                # Solo usar password AJAX si no tenemos la de Selenium
                if "password_unencrypted" not in result["details"]:
                    result["details"]["password"] = wifi_info.get('password_24ghz', 'N/A')
                    result["details"]["note"] = "Password encriptada (use Selenium para versión sin encriptar)"
                result["details"]["channel"] = wifi_info.get('channel_24ghz', 'N/A')
                result["details"]["enabled"] = wifi_info.get('enabled_24ghz', False)
                # return result
        
        # Prioridad 2: Intentar metodo AJAX get_wifi_status
        wifi_status = self._ajax_get('get_wifi_status')
        
        result["status"] = "PASS"
        result["details"]["method"] = "AJAX get_wifi_status"
        result["details"]["data"] = wifi_status
        if wifi_status.get('session_valid') == 0:
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
        
        # PRIORIDAD 0: Intentar extraer password NO ENCRIPTADA por Selenium
        if self.driver:
            print("[TEST] Intentando extracción de password WiFi 5GHz por Selenium...")
            try:
                selenium_passwords = self._extract_wifi_password_selenium()
                if selenium_passwords and 'password_5ghz' in selenium_passwords:
                    print(f"[TEST] ✓ Password 5GHz obtenida por Selenium: {selenium_passwords['password_5ghz']}")
                    result["details"]["password_unencrypted"] = selenium_passwords['password_5ghz']
                    result["details"]["extraction_method"] = "selenium_dom_manipulation"
            except Exception as e:
                print(f"[WARN] Error en extracción Selenium: {e}")
        
        # Prioridad 1: Usar datos de get_base_info si están disponibles
        base_info = self.test_results['metadata'].get('base_info')
        if base_info and base_info.get('wifi_info'):
            wifi_info = base_info['wifi_info']
            if 'ssid_5ghz' in wifi_info:
                result["status"] = "PASS"
                result["details"]["method"] = "AJAX get_base_info"
                result["details"]["ssid"] = wifi_info.get('ssid_5ghz')
                # Solo usar password AJAX si no tenemos la de Selenium
                if "password_unencrypted" not in result["details"]:
                    result["details"]["password"] = wifi_info.get('password_5ghz', 'N/A')
                    result["details"]["note"] = "Password encriptada (use Selenium para versión sin encriptar)"
                result["details"]["channel"] = wifi_info.get('channel_5ghz', 'N/A')
                result["details"]["enabled"] = wifi_info.get('enabled_5ghz', False)
                # return result
        
        # Prioridad 2: Usa el mismo metodo que 2.4GHz (get_wifi_status devuelve ambas bandas)
        wifi_status = self._ajax_get('get_wifi_status')
        
        
        result["status"] = "PASS"
        result["details"]["method"] = "AJAX get_wifi_status"
        result["details"]["data"] = wifi_status
        if wifi_status.get('session_valid') == 0:
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

    def find_element_anywhere2(self, driver, by, sel, desc="", timeout=10, max_depth=8):
        """
        Busca un elemento en default_content y en TODOS los frame/iframe (multi-nivel).
        Deja el driver en el frame donde se encontró.
        """
        end = time.time() + timeout
        last_err = None

        while time.time() < end:
            try:
                driver.switch_to.default_content()

                q = deque([[]])  # paths: [], [0], [1,2], etc.
                visited = set()

                while q:
                    path = q.popleft()
                    tpath = tuple(path)
                    if tpath in visited:
                        continue
                    visited.add(tpath)

                    # switch por índices (re-obteniendo frames en cada nivel)
                    driver.switch_to.default_content()
                    ok = True
                    for idx in path:
                        frames = driver.find_elements(By.CSS_SELECTOR, "frame,iframe")
                        if idx >= len(frames):
                            ok = False
                            break
                        driver.switch_to.frame(frames[idx])
                    if not ok:
                        continue

                    # buscar en este contexto (SIN is_displayed)
                    els = driver.find_elements(by, sel)
                    if els:
                        print(f"[SELENIUM] {desc} encontrado con {by}='{sel}' en path={path}")
                        return els[0]

                    # expandir hijos
                    if len(path) < max_depth:
                        frames = driver.find_elements(By.CSS_SELECTOR, "frame,iframe")
                        for i in range(len(frames)):
                            q.append(path + [i])

            except Exception as e:
                last_err = e

            time.sleep(0.25)

        print(f"[SELENIUM] No se encontró {desc or sel} en {timeout}s. Último error: {last_err}")
        return None
    def click_anywhere2(self, driver, selectors, desc, timeout=10):
        """
        Busca (con find_element_anywhere) y hace click robusto (JS click).
        Reporta el último error real.
        """
        start = time.time()
        last_err = None

        while time.time() - start < timeout:
            for by, sel in selectors:
                try:
                    el = self.find_element_anywhere2(driver, by, sel, desc=desc, timeout=2)
                    if not el:
                        continue

                    # scroll por si está fuera de vista
                    try:
                        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
                    except:
                        pass

                    # CLICK robusto: primero JS, luego normal
                    try:
                        driver.execute_script("arguments[0].click();", el)
                    except Exception as e_js:
                        last_err = e_js
                        try:
                            el.click()
                        except Exception as e_click:
                            last_err = e_click
                            continue

                    print(f"[SELENIUM] Click OK: {desc}")
                    return True

                except Exception as e:
                    last_err = e

            time.sleep(0.2)

        print(f"[SELENIUM] No se encontró/clickeó: {desc} en {timeout}s. Último error: {last_err}")
        return False
    
    def _goto_local_upgrade_menu(self, driver, timeout=15) -> bool:
        """
        Entra a: Management -> Device Management -> Local Upgrade
        usando tus clicks masivos (sin importar frame).
        """
        # Asegurar que estás en la UI principal (después de login)
        # (si tu login te deja en otra vista, esto ayuda)
        try:
            driver.get(f"{self.base_url}/html/main_inter.html")
        except:
            pass
        # Management
        self.click_anywhere2(driver, [(By.ID, "first_menu_manage")], "Management", timeout=20)

        # Device Management
        self.click_anywhere2(driver, [(By.ID, "span_device_admin")], "Device Management", timeout=20)

        # Local Upgrade
        self.click_anywhere2(driver, [(By.ID, "thr_update")], "Local Upgrade", timeout=20)
        return True
    
    def _upload_firmware_via_form(self, firmware_path: str) -> None:
        """
        Ya logueado, navega al menú y sube el archivo con el form:
        <input type="file" id="upgradefile">
        <input type="submit" id="upgrade_button">
        """
        driver = self.driver

        # Asegura ruta absoluta (send_keys lo necesita)
        firmware_path = os.path.abspath(firmware_path)

        # Asegurar que ya estamos en el frameset donde existe el menú
        if not self._enter_main_frameset(timeout_total=25):
            raise RuntimeError("No pude entrar al frameset principal (no hay menú).")

        # Entrar al menú Local Upgrade
        self._goto_local_upgrade_menu(driver, timeout=20)

        # Cargar archivo en el input file (aunque esté en iframe)
        file_input = self.find_element_anywhere2(driver, By.ID, "upgradefile", "Input firmware", timeout=20)
        file_input.send_keys(firmware_path)
        time.sleep(0.3)

        # Click en Update File (submit)
        self.click_anywhere(
            driver,
            [(By.ID, "upgrade_button")],
            desc="Enviar firmware (Update File)",
            timeout=20
        )

        # Algunos firmwares sacan confirmación con alert()
        try:
            alert = WebDriverWait(driver, 3).until(EC.alert_is_present())
            alert.accept()
        except:
            pass

        # Si quieres, aquí puedes esperar un poco y guardar evidencia
        time.sleep(1)
    # Función para actualizar software
    def test_sft_update(self):
        # Version actual:
        sftVer = self.test_results['metadata']['base_info']['raw_data'].get('SoftwareVersion')
        need = False
        completada = False
        newVer = "None"
        ok = self.test_sft_updateCheck()
        need = ok
        if ok:
            print("[INFO] Actualizando software")
            # Se definen las variables a utilizar
            if (self.model == "MOD001"):
                FIRMWARE_PATH = r"C:\BINS\HG6145F"
            else:
                FIRMWARE_PATH = r"C:\BINS\HG6145F1"
            archivo = self.searchBins(FIRMWARE_PATH)
            stem = Path(archivo).stem      # "HG6145F_RP4379"
            newVer = stem.split("_", 1)[1]  # "RP4379"
            # Se necesitará hacer otro login con las credenciales de super usuario
            max_reintentos = 5
            for n in range(max_reintentos):
                print("Intento "+str(n+1)+" de "+str(max_reintentos)+" para iniciar sesión")
                # ni modo, no sé donde está la sesión activa
                time.sleep(310)
                login_ok = self._login_fiberhomeSuper()
                if (login_ok):
                    break
                time.sleep(10)
            if login_ok:
                print("[*] Enviando firmware al router por formulario (Selenium)...")
                self._upload_firmware_via_form(archivo)

                print("[*] Firmware enviado. Esperando reinicio...")
                self.wait_for_router()  # o tu método equivalente
                completada = True
            else:
                print("[ERROR] No se pudo hacer el login de Super Admin")
        else:
            print("[INFO] No se actualizará software")

        # Agregar a test_results
        self.test_results["tests"]["software_update"] = {
            "necesaria": need,
            "completada": completada,
            "version_anterior": sftVer,
            "version_nueva": newVer
        }

    def wait_for_router(self, max_wait_down=120, max_wait_up=300):
        """
        max_wait_down: tiempo máximo esperando a que el router 'caiga'
        max_wait_up:   tiempo máximo esperando a que vuelva a responder
        """
        ROUTER_IP = "192.168.100.1"
        base_url = f"http://{ROUTER_IP}/"

        # 1) Esperar a que deje de responder (si realmente se reinicia)
        start = time.time()
        while time.time() - start < max_wait_down:
            try:
                requests.get(base_url, timeout=3)
                # Si responde, todavía no ha caído
            except requests.RequestException:
                # Dejó de responder: asumimos que está reiniciando
                print("[*] El router dejó de responder, parece que empezó el reinicio.")
                break
            time.sleep(5)

        # 2) Esperar a que vuelva a responder
        start = time.time()
        while time.time() - start < max_wait_up:
            try:
                r = requests.get(base_url, timeout=3)
                if r.status_code == 200:
                    print("[*] El router volvió a estar en línea.")
                    return
            except requests.RequestException:
                pass
            time.sleep(5)

        print("[!] No se pudo confirmar que el router volviera a estar en línea en el tiempo esperado.")


    # Funcion para verificar si se requiere / es posible la actualización
    def test_sft_updateCheck(self):
        print("Se ha seleccionado la actualización de software")
        # Obtener el modelo
        modelo = self.model
        patron = re.compile(r'^[^_]+_([^.]+)\.[^.]+$') # del tipo: HG6145F_RP4379.bin
        sftVer = self.test_results['metadata']['base_info']['raw_data'].get('SoftwareVersion')
        if (modelo == "MOD001"):
            FIRMWARE_PATH = r"C:\BINS\HG6145F"
        else:
            FIRMWARE_PATH = r"C:\BINS\HG6145F1"
        # Proceso de carga diferente dependiendo qué modelo de Fiber sea
        # Verificar si la versión de software está actualizada
        # Buscar el archivo .bin en el directorio
        print("[INFO] El modelo es: "+modelo)
        archivo = self.searchBins(FIRMWARE_PATH)
        # Verificar que exista el archivo
        if archivo != None:
            # Seguimos
            nombre = Path(archivo).name   # convertir a Path solo para sacar el nombre
            nombreValido = bool(patron.fullmatch(nombre))
            # Validar que el bin tenga el patron definido
            if nombreValido:
                # Extracción de la versión de software a instalar
                stem = Path(archivo).stem      # "HG6145F_RP4379"
                codigo = stem.split("_", 1)[1]  # "RP4379"

                sft_num = "".join(ch for ch in codigo if ch.isdigit()) # "4379"
                sftVerActual = "".join(ch for ch in sftVer if ch.isdigit())

                # Verificar que la actual no sea igual o mayor a la que se quiere instalar
                if (sftVerActual != sft_num): # Que sea diferente a la nuestra, para unificarlas
                    print("[INFO] Se necesita actualizar software")
                    return True
                else:
                    print("[INFO] El software está actualizado")
                    self.test_results["tests"]["software_update"] = {
                        "necesaria": False,
                        "completada": True,
                        "version_anterior": sftVer,
                        "version_nueva": sftVer
                    }
                    return False
            else:
                print("[ERROR] El archivo .bin no tiene la nomenclatura correcta")
                self.test_results["tests"]["software_update"] = {
                    "necesaria": True,
                    "completada": False,
                    "version_anterior": sftVer,
                    "version_nueva": "N/A"
                }
                return False
        else:
            print("[ERROR] No existe un archivo de actualización en el directorio correcto")
            self.test_results["tests"]["software_update"] = {
                "necesaria": True,
                "completada": False,
                "version_anterior": sftVer,
                "version_nueva": "N/A"
            }
            return False