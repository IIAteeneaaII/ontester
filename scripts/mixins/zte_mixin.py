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

# Clase que en teoría hereda todo de donde se manda a llamar
class ZTEMixin:
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

    def nav_zte_wifi_pass(self, driver):
        """Local Network -> WLAN -> WLAN Basic -> WLAN SSID Configuration (SSID1 2.4GHz)"""
        # Siempre arrancar desde la raíz del GUI ZTE
        driver.switch_to.default_content()
        driver.get(self.base_url)

        # 1) Menú superior: Local Network
        self.click_anywhere(
            driver,
            [
                (By.ID, "localnet"),
                (By.XPATH, "//*[@id='localnet' or @menupage='localNetStatus']"),
            ],
            "Local Network",
        )

        # 2) Submenú: WLAN
        self.click_anywhere(
            driver,
            [
                (By.ID, "wlanConfig"),
                (By.XPATH, "//*[@id='wlanConfig' or @menupage='wlanBasic']"),
            ],
            "WLAN",
        )

        # 3) Tercer nivel: WLAN Basic
        self.click_anywhere(
            driver,
            [
                (By.ID, "wlanBasic"),
                (By.XPATH, "//*[@id='wlanBasic' or contains(normalize-space(.),'WLAN Basic')]"),
            ],
            "WLAN Basic",
        )

        # 4) Barra "WLAN SSID Configuration"
        self.click_anywhere(
            driver,
            [
                (By.ID, "WLANSSIDConfBar"),
                (By.XPATH, "//*[@id='WLANSSIDConfBar']"),
            ],
            "WLAN SSID Configuration",
        )

        # 5) Esperar (con reintentos) a que el AJAX cargue la instancia SSID1 (2.4GHz)
        max_attempts = 4
        for attempt in range(max_attempts):
            # usamos find_element_anywhere porque ya recorre todos los frames/iframes
            ssid1 = self.find_element_anywhere(
                driver,
                By.ID,
                "instName_WLANSSIDConf:0",
                desc="SSID1 (2.4GHz)",
                timeout=6,  # espera por intento
            )

            if ssid1:
                print("[SELENIUM] SSID1 (2.4GHz) listo en WLAN SSID Configuration")
                # nos aseguramos de que quede expandido (por si acaso)
                try:
                    driver.execute_script("arguments[0].click();", ssid1)
                except Exception:
                    pass
                return True

            # Si no se encontró, reintentamos forzando una recarga ligera del panel
            print(
                f"[SELENIUM] Intento {attempt+1}/{max_attempts}: "
                "Panel SSID1 no disponible. Reintentando recarga AJAX..."
            )

            try:
                driver.switch_to.default_content()
                # re-clic en la barra de SSID Configuration
                self.click_anywhere(
                    driver,
                    [
                        (By.ID, "WLANSSIDConfBar"),
                        (By.XPATH, "//*[@id='WLANSSIDConfBar']"),
                    ],
                    "WLAN SSID Configuration (re-click)",
                )
                # algunos firmwares usan este input oculto para refrescar
                driver.execute_script(
                    """
                    var btn = document.getElementById('WLANSSIDConf_Refresh_button');
                    if (btn) { btn.click(); }
                    """
                )
            except Exception:
                # si algo sale mal aquí, sólo esperamos y volvemos a intentar
                pass

            time.sleep(3)  # pequeña espera antes del siguiente intento

        print("[ERROR] No se logró preparar el panel SSID1 2.4GHz :(")
        return False

    def parse_zte_wifi_pass(self, driver):
        """Obtener contraseña WiFi 2.4GHz del ZTE de forma robusta."""
        try:
            driver.switch_to.default_content()

            # 1) Localizar el campo de contraseña
            pwd_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "KeyPassphrase:0"))
            )
            print("[SELENIUM] Campo KeyPassphrase:0 localizado.")

            # 2) Modificar el type="password" → "text"
            driver.execute_script("""
                let f = document.getElementById('KeyPassphrase:0');
                if (f) f.setAttribute('type','text');
            """)
            print("[SELENIUM] Se forzó type=text en el campo de contraseña.")

            # 3) Leer el valor ya visible
            password = pwd_field.get_attribute("value").strip()

            if password:
                print(f"[SELENIUM] Contraseña WiFi 2.4GHz obtenida: {password}")
                return {"band": "2.4GHz", "password": password}

            print("[SELENIUM] Campo localizado pero vacío.")
            return {"band": "2.4GHz", "password": "N/A"}

        except TimeoutException:
            print("[SELENIUM] Timeout al buscar campo de contraseña WiFi 2.4GHz")
            return {"band": "2.4GHz", "password": "N/A"}

        except Exception as e:
            print(f"[ERROR] Falló la extracción de contraseña ZTE: {e}")
            return {"band": "2.4GHz", "password": "N/A"}

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

            # Funcion adicional para obtener la contraseña del wifi:
            nav_bool = self.nav_zte_wifi_pass(driver) # Navegacion
            if (nav_bool):
                pswd = self.parse_zte_wifi_pass(driver) # Obtencion
                result = {
                    "name": "Contraseña",
                    "status": pswd.get("error", {}).get("str") == "SUCC",
                    "details": pswd,          # aquí va el json parseado de ese XML
                }
                self.test_results["tests"][result["name"]] = result
            #Guardar a archivo
            self.save_results2("test_mod002")
        except Exception as e:
            print("No success :c", e)

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