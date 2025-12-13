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
        # Ajustes para el fiber
        self.minWifi24Signal = -80  # Valor mínimo de señal WiFi 2.4GHz
        self.minWifi5Signal = -80  # Valor mínimo de señal WiFi 2.4GHz
        self.maxWifi24Signal = -5  # Valor máximo de señal WiFi 2.4GHz
        self.maxWifi5Signal = -5  # Valor máximo de señal WiFi 5GHz
        # Ajustes para ZTE y Huawei
        self.minWifi24Percent = 60  # Porcentaje mínimo de señal WiFi 2.4GHz
        self.minWifi5Percent = 60   # Porcentaje mínimo de señal WiFi 5GHz
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

    def _login_fiberhomeSuper(self):
        """Login con credenciales de Super Admin para actualización de firmware"""
        print("[SELENIUM] Haciendo logout y login con credenciales Super Admin...")
        
        chrome_options = Options()
        headless = True
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
        try:
            # Navegar a logout
            print("[SELENIUM] Navegando a logout...")
            driver.get(f"{self.base_url}/logout.html")
            time.sleep(2)
            
            # Borrar todas las cookies para forzar nuevo login
            print("[SELENIUM] Borrando cookies de sesión...")
            driver.delete_all_cookies()
            time.sleep(1)
            
            # Navegar al login nuevamente
            print("[SELENIUM] Navegando a página de login...")
            driver.get(self.base_url)
            time.sleep(3)
            
            # Esperar y llenar formulario con credenciales Super Admin
            print("[SELENIUM] Esperando formulario de login...")
            username_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "Frm_Username"))
            )
            print("[SELENIUM] Campo username encontrado")
            
            password_field = driver.find_element(By.ID, "Frm_Password")
            print("[SELENIUM] Campo password encontrado")
            
            # Limpiar y llenar credenciales Super Admin
            username_field.clear()
            username_field.send_keys("admin")
            password_field.clear()
            password_field.send_keys("z#Wh46QN@52Rm%j5")
            print("[SELENIUM] Credenciales Super Admin ingresadas (admin/Zgs12O5TSa2l3o9)")
            
            # Hacer clic en login
            login_button = driver.find_element(By.ID, "LoginId")
            login_button.click()
            print("[SELENIUM] Click en botón login")
            
            time.sleep(5)
            
            # Verificar que el login fue exitoso buscando algún elemento de la interfaz
            try:
                driver.find_element(By.ID, "mgrAndDiag")
                print("[SELENIUM] Login Super Admin completado exitosamente")
                return True
            except:
                print("[ERROR] Login Super Admin no completó correctamente - no se encuentra interfaz")
                return False
            
        except TimeoutException:
            print(f"[ERROR] Timeout esperando formulario de login después de logout")
            # Guardar screenshot para debug
            try:
                driver.save_screenshot("debug_login_super_timeout.png")
                with open("debug_login_super_timeout.html", "w", encoding="utf-8") as f:
                    f.write(driver.page_source)
                print("[DEBUG] Screenshot y HTML guardados para debug")
            except:
                pass
            return False
        except Exception as e:
            print(f"[ERROR] Login Super Admin falló: {e}")
            # Guardar screenshot para debug
            try:
                driver.save_screenshot("debug_login_super_failed.png")
                print("[DEBUG] Screenshot guardado: debug_login_super_failed.png")
            except:
                pass
            return False

    def test_sft_update(self):
        ok = True
        if ok:
            print("[INFO] Actualizando software")
            # Se definen las variables a utilizar
            if (self.model == "MOD001"):
                FIRMWARE_PATH = r"C:\BINS\HG6145F"
            else:
                FIRMWARE_PATH = r"C:\BINS\HG6145F1"
            archivo = self.searchBins(FIRMWARE_PATH)
            ROUTER_IP = "192.168.100.1"
            UPGRADE_URL = f"http://{ROUTER_IP}/nginx_upgradecgi"

            params = {
                "method": "upload",
                "action": "upgradeimage",
                "key": "Yq4PFaNB",
            }

            data = {
                "upgradefile_telmex": "",
                "path": "",
            }
            # Se necesitará hacer otro login con las credenciales de super usuario
            
            login_ok = self._login_fiberhomeSuper()
            if login_ok:
                print("[INFO] Login Super Admin exitoso")
                with open(archivo, "rb") as f:
                    files = {
                        # name="upgradefile" del input <input type="file">
                        "upgradefile": (archivo, f, "application/octet-stream"),
                    }

                    print("[*] Enviando firmware al router (esto puede tardar varios minutos)...")
                    try:
                        resp = requests.post(
                            UPGRADE_URL,
                            params=params,
                            data=data,
                            files=files,
                            cookies=self.selenium_cookies,
                            # timeout=(conexion, lectura): dale margen grande a la lectura
                            timeout=(10, 200),  # 10 s para conectar, 900 s (~15 min) para que responda
                        )
                    except requests.exceptions.Timeout:
                        print("[!] Tiempo de espera agotado durante la actualización.")
                        return
                    except requests.RequestException as e:
                        print("[!] Error en la petición:", e)
                        return

                print("[*] Respuesta HTTP:", resp.status_code)
                print(resp.text[:500])  # primeros caracteres, por si devuelve texto de estado

                if resp.status_code == 200:
                    print("[*] El router indicó que la carga terminó.")
                    print("[*] Esperando a que el router se reinicie y vuelva a estar en línea...")
                    self.wait_for_router()
                else:
                    print("[!] Código distinto de 200: revisa si el firmware es válido o si la sesión expiró.")
            else:
                print("[ERROR] No se pudo hacer el login de Super Admin")
        else:
            print("[INFO] No se actualizará software")
    
    def searchBins(self, ruta):
        ruta = Path(ruta)
        for item in ruta.glob("*.bin"):
            return str(item)
        return None

if __name__ == "__main__":
    obj = FiberMixin("192.168.100.1")
    obj.model = "MOD001"
    obj.test_sft_update()