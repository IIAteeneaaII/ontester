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

class HuaweiMixin:
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
                {"id": "guideinternet", "desc": "Exit wizard"},
                # {"id": "guidesyscfg", "desc": "Paso 1: Skip Network Config"},
                # {"id": "guideskip", "desc": "Paso 2: Skip User Config"},
                # {"id": "nextpage", "desc": "Paso 3: Return to Home Page"}
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
        except Exception as e:
            print(f"[SELENIUM] Error extrayendo contraseña WiFi 2.4GHz: {e}")
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
        except Exception as e:
            print(f"[SELENIUM] Error extrayendo contraseña WiFi 5GHz: {e}")
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
            error_msg = str(e).split('\n')[0] if str(e) else type(e).__name__
            print(f"[SELENIUM] Error leyendo estado USB: {error_msg}")
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
                # (By.NAME, "m1div_deviceinfo"),
                # (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
            ],
            "Huawei System Information (menú principal)",
        )

        # 2) Submenú "Device"
        # self.click_anywhere(
        #     driver,
        #     [
        #         (By.ID, "name_deviceinfo"),
        #         # (By.XPATH, "//div[@id='name_deviceinfo']"),
        #         # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Device']"),
        #     ],
        #     "Huawei Device (System Information)",
        # )

    def nav_hw_optical(self, driver):
        """System Information -> Optical (fibra)"""
        driver.switch_to.default_content()
        # self.click_anywhere(
        #     driver,
        #     [
        #         (By.ID, "pointer_Systeminfo"),
        #         # (By.NAME, "m1div_deviceinfo"),
        #         # (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
        #     ],
        #     "Huawei System Information (menú principal)",
        # )

        # Esperar a que el submenú de System Information se expanda
        #time.sleep(2)

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_opticinfo"),
                # (By.XPATH, "//div[@id='name_opticinfo']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Optical']"),
            ],
            "Huawei Optical",
        )

    def nav_hw_lan(self, driver):
        """System Information -> Eth Port (información de LAN / conexiones Ethernet)"""

        # 1) Navegar a "System Information"
        # self.click_anywhere(
        #     driver,
        #     [
        #         (By.ID, "name_Systeminfo"),
        #         (By.NAME, "m1div_deviceinfo"),
        #         (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
        #     ],
        #     "Huawei System Information (menú principal)",
        # )

        # 2) Submenú "Eth Port"
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_ethinfo"),
                # (By.XPATH, "//div[@id='name_ethinfo']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Eth Port']"),
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
        # self.click_anywhere(
        #     driver,
        #     [
        #         (By.ID, "name_Systeminfo"),
        #         (By.NAME, "m1div_deviceinfo"),
        #         (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
        #     ],
        #     "Huawei System Information (menú principal)",
        # )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlaninfo"),
                # (By.XPATH, "//div[@id='name_wlaninfo']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei WLAN (menú WLAN)",
        )    

    def nav_hw_wifi_5(self, driver):
        """System Information -> WLAN (5 GHz)"""

        # self.click_anywhere(
        #     driver,
        #     [
        #         (By.ID, "name_Systeminfo"),
        #         (By.NAME, "m1div_deviceinfo"),
        #         (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
        #     ],
        #     "Huawei System Information (menú principal)",
        # )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlaninfo"),
                # (By.XPATH, "//div[@id='name_wlaninfo']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei WLAN (menú WLAN)",
        )

        # Seleccionar radio 5G (value=2)
        self.click_anywhere(
            driver,
            [
                (By.CSS_SELECTOR, "input[name='WlanMethod'][value='2']"),
                # (By.XPATH, "//input[@name='WlanMethod' and @value='2']"),
            ],
            "Huawei WLAN 5G (radio)",
        )

    def nav_hw_mac(self, driver):
        """System Information -> Home Network (tabla de MAC / clientes)"""

        # self.click_anywhere(
        #     driver,
        #     [
        #         (By.ID, "name_Systeminfo"),
        #         (By.NAME, "m1div_deviceinfo"),
        #         (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
        #     ],
        #     "Huawei System Information (menú principal)",
        # )

        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlancoverinfo"),
                # (By.XPATH, "//div[@id='name_wlancoverinfo']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='Home Network']"),
            ],
            "Huawei Home Network",
        )

    def nav_hw_show_pass_24(self, driver):
        """Advanced -> WLAN -> 2.4G Basic Network Settings, mostrar contraseña"""

        # Menú Advanced (WAN)
        self.click_anywhere(
            driver,
            [
                # (By.ID, "name_addconfig"),
                # (By.NAME, "m1div_wan"),
                (By.XPATH, "//div[@id='name_addconfig' or @name='m1div_wan' or normalize-space(.)='Advanced']"),
            ],
            "Huawei Advanced (WAN)",
        )

        # Submenú WLAN
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlanconfig"),
                # (By.XPATH, "//div[@id='name_wlanconfig']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei Advanced WLAN config",
        )

        # Tercer nivel: 2.4G Basic Network...
        self.click_anywhere(
            driver,
            [
                (By.ID, "wlan2basic"),
                # (By.NAME, "m3div_WlanBasic2G"),
                # (By.XPATH, "//div[@id='wlan2basic' or @name='m3div_WlanBasic2G']"),
            ],
            "Huawei 2.4G Basic Network",
        )

    def nav_hw_show_pass_5(self, driver):
        """Advanced -> WLAN -> 5G Basic Network Settings, mostrar contraseña"""

        # Menú Advanced (WAN)
        self.click_anywhere(
            driver,
            [
                # (By.ID, "name_addconfig"),
                # (By.NAME, "m1div_wan"),
                (By.XPATH, "//div[@id='name_addconfig' or @name='m1div_wan' or normalize-space(.)='Advanced']"),
            ],
            "Huawei Advanced (WAN)",
        )

        # Submenú WLAN
        self.click_anywhere(
            driver,
            [
                (By.ID, "name_wlanconfig"),
                # (By.XPATH, "//div[@id='name_wlanconfig']"),
                # (By.XPATH, "//div[contains(@class,'SecondMenuTitle') and normalize-space(.)='WLAN']"),
            ],
            "Huawei Advanced WLAN config",
        )

        # Tercer nivel: 5G Basic Network...
        self.click_anywhere(
            driver,
            [
                (By.ID, "wlan5basic"),
                # (By.NAME, "m3div_WlanBasic5G"),
                # (By.XPATH, "//div[@id='wlan5basic' or @name='m3div_WlanBasic5G']"),
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
            # usb_menu = wait.until(EC.element_to_be_clickable((By.ID, "usbapplication")))
            # print("[SELENIUM] Huawei USB Application encontrado en documento principal con id='usbapplication'")
            # usb_menu.click()

            # 4) Cambiar al iframe del contenido
            driver.switch_to.default_content()
            wait.until(EC.frame_to_be_available_and_switch_to_it((By.ID, "menuIframe")))
            print("[SELENIUM] iframe 'menuIframe' disponible para USB Application.")

            # 5) Esperar el select de USB
            wait.until(EC.presence_of_element_located((By.ID, "SrvClDevType")))
            print("[SELENIUM] Select USB 'SrvClDevType' encontrado en página USB Application.")

            return True

        except Exception as e:
            error_msg = str(e).split('\n')[0] if str(e) else type(e).__name__
            print(f"[SELENIUM] Error navegando a USB Application: {error_msg}")
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def nav_advanced(self, driver):
        print("[SELENIUM] Navegando a Advanced...")
        # NO hacer driver.get() - ya estamos logueados y el menú está cargado
        driver.switch_to.default_content()
        time.sleep(1)  # Pequeña espera para estabilidad

        # Entrar en Advanced
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "name_addconfig"),
                (By.CSS_SELECTOR, "a[menupage='name_addconfig']"),
                (By.LINK_TEXT, "Advanced"),
            ],
            desc="Advanced",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en Advanced")

        print("[SELENIUM] Advanced debería ser accesible ahora")

    def nav_maintenance_diagnosis(self, driver):
        print("[SELENIUM] Navegando a Maintenance Diagnosis...")
        # NO hacer driver.get() - mantener sesión Super Admin
        driver.switch_to.default_content()
        time.sleep(1)

        # Entrar en Maintenance Diagnosis
        ok = self.click_anywhere(
            driver,
            selectors=[
                (By.ID, "name_maintaininfo"),
                (By.CSS_SELECTOR, "a[menupage='name_maintaininfo']"),
                (By.LINK_TEXT, "Maintenance Diagnosis"),
            ],
            desc="Maintenance Diagnosis",
            timeout=10
        )
        if not ok:
            raise RuntimeError("No se pudo hacer click en Maintenance Diagnosis")

        print("[SELENIUM] Maintenance Diagnosis debería ser accesible ahora")

    def nav_browse_button(self, driver):
        print("[SELENIUM] Buscando input file para subir firmware...")
        
        # Esperar a que cargue la página de Software Update en el iframe
        try:
            driver.switch_to.default_content()
            WebDriverWait(driver, 10).until(
                EC.frame_to_be_available_and_switch_to_it((By.ID, "menuIframe"))
            )
            print("[SELENIUM] Cambiado a iframe 'menuIframe'")
            
            # Esperar el input file (id=t_file, type=file)
            file_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "t_file"))
            )
            print("[SELENIUM] Input file encontrado (id=t_file)")
            return file_input
            
        except TimeoutException:
            print("[ERROR] No se encontró el input file (id=t_file) después de 10s")
            # Guardar debug
        #     try:
        #         timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #         driver.save_screenshot(f"debug_browse_error_{timestamp}.png")
        #         with open(f"debug_browse_error_{timestamp}.html", 'w', encoding='utf-8') as f:
        #             f.write(driver.page_source)
        #         print(f"[DEBUG] Archivos de debug guardados: debug_browse_error_{timestamp}.*")
        #     except:
        #         pass
        #     raise RuntimeError("No se pudo encontrar el input file")
        # except Exception as e:
        #     print(f"[ERROR] Error navegando al input file: {e}")
        #     raise

    def huawei_info(self, driver):
        # Verificar opciones a testear
        optTest = self.opcionesTest
        tests_opts = optTest.get("tests", {})

        # Igual que ZTE: primero lista vacía (solo se agregan las que procedan)
        tests = []

        # Descripcion || navegacion (clicks) || extracción
        if isinstance(optTest.get("info", False), dict):
            if any(optTest.get("info", False).values()):
                tests.extend([
                    # === System Information ===
                    ("hw_device",  self.nav_hw_info,       self.parse_hw_device),
                    ("hw_lan",     self.nav_hw_lan,        self.parse_hw_lan),
                    ("hw_wifi24",  self.nav_hw_wifi_24,    self.parse_hw_wifi24),
                    ("hw_wifi5",   self.nav_hw_wifi_5,     self.parse_hw_wifi5),
                    ("hw_mac",     self.nav_hw_mac,        self.parse_hw_mac),
                    #("hw_optical", self.nav_hw_optical,    self.parse_hw_optical),

                    # === Advanced ===
                    ("hw_wifi24_pass", self.nav_hw_show_pass_24, self.parse_hw_wifi24_pass),
                    ("hw_wifi5_pass",  self.nav_hw_show_pass_5,  self.parse_hw_wifi5_pass),
                    #("hw_usb",  self.nav_hw_usb, self.read_hw_usb_status)
                ])
        elif optTest.get("info", False):
            tests.extend([
                # === System Information ===
                ("hw_device",  self.nav_hw_info,       self.parse_hw_device),
                ("hw_lan",     self.nav_hw_lan,        self.parse_hw_lan),
                ("hw_wifi24",  self.nav_hw_wifi_24,    self.parse_hw_wifi24),
                ("hw_wifi5",   self.nav_hw_wifi_5,     self.parse_hw_wifi5),
                ("hw_mac",     self.nav_hw_mac,        self.parse_hw_mac),
                #("hw_optical", self.nav_hw_optical,    self.parse_hw_optical),

                # === Advanced ===
                ("hw_wifi24_pass", self.nav_hw_show_pass_24, self.parse_hw_wifi24_pass),
                ("hw_wifi5_pass",  self.nav_hw_show_pass_5,  self.parse_hw_wifi5_pass),
                #("hw_usb",  self.nav_hw_usb, self.read_hw_usb_status)
            ])

        # MISMA IDEA QUE ZTE: si info es dict y NO se pide nada, no ejecutar INFO
        if isinstance(optTest.get("info", False), dict):
            if not any(optTest.get("info", {}).values()):
                tests = []
        elif not optTest.get("info", False):
            tests = []

        # MOD: FILTRO MINIMO (estilo ZTE) para que unitarias (ej. USB Port) NO extraigan LAN/WLAN/PASS si en conexion.py vienen en False
        if isinstance(optTest.get("info", False), dict) and tests:
            # LAN: en tu conexion.py NO existe "lan", así que por default NO debe ejecutarse.
            if not optTest.get("info", {}).get("lan", False):
                tests = [t for t in tests if t[0] != "hw_lan"]

            # SSIDs: solo si fueron solicitados explícitamente
            if not optTest.get("info", {}).get("ssid_24ghz", False):
                tests = [t for t in tests if t[0] != "hw_wifi24"]
            if not optTest.get("info", {}).get("ssid_5ghz", False):
                tests = [t for t in tests if t[0] != "hw_wifi5"]

            # Passwords: SOLO si fueron solicitados explícitamente
            if not optTest.get("info", {}).get("wifi_password", False):
                tests = [t for t in tests if t[0] not in ("hw_wifi24_pass", "hw_wifi5_pass")]

        # Verificar opciones a testear (NO INFO)
        if tests_opts.get("tx_power", True) and tests_opts.get("rx_power", True):
            print("Se ejecutará prueba de TX y RX")
            #tests.append( ("hw_optical", self.nav_hw_optical,    self.parse_hw_optical) )
            tests.insert(5, ("hw_optical", self.nav_hw_optical, self.parse_hw_optical))
        if tests_opts.get("usb_port", True):
            tests.append( ("hw_usb",  self.nav_hw_usb, self.read_hw_usb_status) )
        
        # Recorrer todas las funciones de clicks + extraer el DOM
        # Usar try/except para cada paso para evitar que un fallo detenga todo el proceso
        def emit(kind, payload):
            if self.out_q:
                print("[INFO Q] Se detectó la queue")
                self.out_q.put((kind, payload))
            else:
                print("[INFO Q] NOOO Se detectó la queue")
                
        for name, nav_func, parse_func in tests:
            try:
                emit("pruebas", f"Ejecutando: {name}")
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

        # wifi24 = self.test_results['tests']['hw_wifi24']['data'].get('ssid') # nombre wifi
        # wifi5 = self.test_results['tests']['hw_wifi5']['data'].get('ssid') # nombre wifi
        wifi24 = (self.test_results.get("tests", {}).get("hw_wifi24", {}).get("data") or {}).get("ssid")
        wifi5  = (self.test_results.get("tests", {}).get("hw_wifi5",  {}).get("data") or {}).get("ssid")

        if tests_opts.get("software_update", True):
            emit("pruebas", "Ejecutando Actualizacion de Software")
            self.test_sft_updateHw(driver)

        # Verificar si se tienen que probar las señales wifi
        if tests_opts.get("wifi_24ghz_signal", True) and tests_opts.get("wifi_5ghz_signal", True):
                emit("pruebas", "Ejecutanto Prueba de Señal WiFi")
                if wifi24 and wifi5:
                    self.test_wifi_rssi_windows(wifi24, wifi5)

        # Emitir resultado de factory_reset si se ejecutó (al final de todas las pruebas)
        factory_result = self.test_results.get('tests', {}).get('factory_reset', {})
        if factory_result:
            status = "PASS" if factory_result.get('status') == True else "FAIL"
            emit("test_individual", {"name": "factory_reset", "status": status})
    
        self.save_results2("test_mod003-mod005")
        #print(self.test_results)

    def tail_digits(self, s: str) -> str:
        m = re.search(r"(\d+)$", s)
        return m.group(1) if m else ""

    def test_sft_updateCheckHw(self):
        print("Se ha seleccionado la actualización de software")
        # Obtener el modelo
        modelo = self.model
        
        # Obtener la versión de software desde hw_device (donde Selenium guarda la info en Huawei)
        try:
            hw_device_data = self.test_results.get('tests', {}).get('hw_device', {}).get('data', {})
            sftVer = hw_device_data.get('software_version', '')
            
            if not sftVer:
                print("[ERROR] No se pudo obtener la versión de software del dispositivo")
                print("[DEBUG] Contenido de hw_device_data:", hw_device_data)
                return False
                
            print(f"[INFO] Versión actual de software detectada: {sftVer}")
            
        except Exception as e:
            print(f"[ERROR] Error al obtener versión de software: {e}")
            print(f"[DEBUG] test_results structure: {self.test_results.get('tests', {}).keys()}")
            return False

        # Configurar ruta y patrón según el modelo
        if modelo == "MOD003":
            FIRMWARE_PATH = r"C:\BINS\X6-10"
            # Patrón: HG8145X6-10_V500R022C00SPC297
            patron = re.compile(r'^HG8145X6-10_V[\d\w]+$')
        elif modelo == "MOD007":
            FIRMWARE_PATH = r"C:\BINS\X6"
            # Patrón: HG8145X6_V500R022C00SPC232
            patron = re.compile(r'^HG8145X6_V[\d\w]+$')
        elif modelo in ["MOD004", "MOD005"]:
            FIRMWARE_PATH = r"C:\BINS\HG8145V5"
            # Patrón: HG8145V5_V500R022C00SPC292
            patron = re.compile(r'^HG8145V5_V[\d\w]+$')
        else:
            print(f"[ERROR] Modelo {modelo} no soportado para actualización de firmware")
            return False
        
        # Proceso de carga diferente dependiendo qué modelo de Fiber sea
        # Verificar si la versión de software está actualizada
        # Buscar el archivo .bin en el directorio
        print("[INFO] El modelo es: "+modelo)
        archivo = self.searchBins(FIRMWARE_PATH)
        # Verificar que exista el archivo
        if archivo != None:
            # Seguimos
            stem = Path(archivo).stem      # Nombre sin extensión
            print(f"[DEBUG] Archivo encontrado: {Path(archivo).name}")
            print(f"[DEBUG] Stem (sin .bin): {stem}")
            print(f"[DEBUG] Patrón esperado: {patron.pattern}")
            nombreValido = bool(patron.fullmatch(stem))
            # Validar que el bin tenga el patron definido
            if nombreValido:
                # Extracción de la versión de software a instalar
                stem = Path(archivo).stem      # "HG6145F_RP4379"
                codigo = stem.split("_", 1)[1]  # "RP4379"

                sft_num = "".join(ch for ch in codigo if ch.isdigit()) # "4379"
                sftVerActual = "".join(ch for ch in sftVer if ch.isdigit())

                sufijo_actual = self.tail_digits(sftVer)
                sufijo_bin    = self.tail_digits(codigo)
                # Verificar que la actual no sea igual o mayor a la que se quiere instalar
                if (sufijo_actual != sufijo_bin): # Que sea diferente a la nuestra, para unificarlas
                    print("[INFO] Se necesita actualizar software")
                    return True
                else:
                    print("[INFO] El software está actualizado")
                    
                    # Obtener versión anterior desde hw_device
                    previous_version = self.test_results.get('tests', {}).get('hw_device', {}).get('data', {}).get('software_version', 'N/A')
                    
                    self.test_results["tests"]["software_update"] = {
                        "name": "software_update",
                        "status": True,
                        "details": {
                            "previous_version": previous_version,
                            "new_version": "Ya está actualizado",
                            "firmware_file": archivo,
                            "update_completed": True,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        }
                    }

                    return False
            else:
                print("[ERROR] El archivo .bin no tiene la nomenclatura correcta")
                self.test_results["tests"]["software_update"] = {
                    "name": "software_update",
                    "status": True,
                    "details": {
                        "previous_version": previous_version,
                        "new_version": "El archivo bin no tiene buen nombre",
                        "firmware_file": "archivo",
                        "update_completed": False,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                return False
            
        else:
            print("[ERROR] No existe un archivo de actualización en el directorio correcto")
            self.test_results["tests"]["software_update"] = {
                "name": "software_update",
                "status": True,
                "details": {
                    "previous_version": previous_version,
                    "new_version": "No hay directorio correcto",
                    "firmware_file": "archivo",
                    "update_completed": False,
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }
            }
            return False
        
    def test_sft_updateHw(self, driver):
        ok = self.test_sft_updateCheckHw()
        modelo = self.model
        if ok:
            print("[INFO] Actualizando software...")
            # Configurar ruta y patrón según el modelo
            if modelo == "MOD003":
                FIRMWARE_PATH = r"C:\BINS\X6-10"
                # Patrón: HG8145X6_V500R022C00SPC297
                patron = re.compile(r'^HG8145X6_V[\d\w]+$')
            elif modelo in ["MOD004", "MOD005"]:
                FIRMWARE_PATH = r"C:\BINS\HG8145V5"
                # Patrón: HG8145V5_V500R022C00SPC292
                patron = re.compile(r'^HG8145V5_V[\d\w]+$')
            elif modelo == "MOD007":
                FIRMWARE_PATH = r"C:\BINS\X6"
            else:
                print(f"[ERROR] Modelo {modelo} no soportado para actualización de firmware")
                return False
            
            archivo = self.searchBins(FIRMWARE_PATH)
            
            try:
                # Hacer login con credenciales Super Admin
                if not self._login_huawei_super(driver):
                    print("[ERROR] No se pudo hacer login Super Admin")
                    return False
                
                # Navegar a la sección de actualización usando Selenium
                self.nav_advanced(driver)
                self.nav_maintenance_diagnosis(driver)
                
                # Esperar a que cargue la página de Software Update
                time.sleep(3)
                
                # Obtener el input file directamente (id=t_file, type=file)
                file_input = self.nav_browse_button(driver)
                print("[SELENIUM] Input file listo para recibir ruta del firmware")
                
                # Enviar la ruta del archivo
                print(f"[SELENIUM] Cargando archivo: {archivo}")
                file_input.send_keys(archivo)
                time.sleep(2)
                
                # Buscar y hacer clic en el botón Upgrade (id=btnSubmit)
                print("[SELENIUM] Buscando botón Upgrade...")
                upload_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "btnSubmit"))
                )
                print("[SELENIUM] Haciendo clic en Upgrade...")
                upload_button.click()
                
                # Esperar confirmación
                time.sleep(3)
                
                # Aceptar diálogo de confirmación si aparece
                try:
                    confirm_btn = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "confirmOK"))
                    )
                    confirm_btn.click()
                    print("[SELENIUM] Confirmación aceptada. Iniciando actualización...")
                except TimeoutException:
                    print("[SELENIUM] No apareció diálogo de confirmación (puede ser normal)")
                
                # Esperar a que inicie el proceso de actualización
                print("[SELENIUM] Esperando inicio de actualización (100 segundos)...")
                time.sleep(100)
                
                # Guardar captura de pantalla del estado de actualización
                # try:
                #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                #     screenshot_path = f"debug_firmware_upload_{timestamp}.png"
                #     driver.save_screenshot(screenshot_path)
                #     print(f"[DEBUG] Captura guardada: {screenshot_path}")
                    
                #     # Guardar HTML para debug
                #     html_path = f"debug_firmware_upload_{timestamp}.html"
                #     with open(html_path, 'w', encoding='utf-8') as f:
                #         f.write(driver.page_source)
                #     print(f"[DEBUG] HTML guardado: {html_path}")
                # except Exception as e:
                #     print(f"[DEBUG] No se pudo guardar captura: {e}")
                
                # Monitorear progreso y reinicio (total 200 segundos)
                print("[SELENIUM] Monitoreando actualización (60 segundos)...")
                max_wait = 90  # 1.5 minutos de monitoreo
                check_interval = 15  # Revisar cada 15 segundos
                elapsed = 0
                
                while elapsed < max_wait:
                    try:
                        # Verificar si hay texto de progreso en la página
                        page_text = driver.page_source.lower()
                        
                        if 'upgrading' in page_text or 'updating' in page_text or 'progress' in page_text:
                            print(f"[SELENIUM] Actualización en progreso... ({elapsed}s transcurridos)")
                        elif 'success' in page_text or 'complete' in page_text:
                            print("[SUCCESS] Actualización completada según interfaz web")
                            break
                        elif 'error' in page_text or 'failed' in page_text:
                            print("[ERROR] Error detectado en la interfaz de actualización")
                            # Guardar evidencia del error
                            # driver.save_screenshot(f"error_firmware_{timestamp}.png")
                            # with open(f"error_firmware_{timestamp}.html", 'w', encoding='utf-8') as f:
                            #     f.write(driver.page_source)
                            return False
                        
                        time.sleep(check_interval)
                        elapsed += check_interval
                        
                    except Exception as e:
                        print(f"[WARNING] Error al verificar progreso: {e}")
                        break
                # Darle click al boton de restart
                print("[SELENIUM] Buscando botón Restart...")
                restart_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        # 1) El más específico: onclick exacto
                        "//button[@type='button' and (@onclick='onReboot();' or contains(@onclick,'onReboot'))]"
                    ))
                )
                print("[SELENIUM] Haciendo clic en Restart...")
                try:
                    restart_button.click()
                except Exception:
                    # Fallback por si Selenium dice "intercepted/not interactable"
                    driver.execute_script("arguments[0].click();", restart_button)

                print("[INFO] Esperando reinicio del dispositivo (120 segundos adicionales)...")
                WebDriverWait(driver, 10).until(EC.alert_is_present())
                alert = driver.switch_to.alert
                print("[SELENIUM] Confirmación reboot:", alert.text)
                alert.accept()
                print("[SELENIUM] Confirmación aceptada. Reiniciando...")
                time.sleep(120)  # Esperar 2 minutos para el reinicio completo
                
                # Intentar hacer login post-actualización para obtener nueva versión
                print("[INFO] Verificando nueva versión de firmware...")
                new_version = "N/A (no se pudo verificar)"
                
                try:
                    # Volver a cargar la página de login
                    driver.get(self.base_url)
                    time.sleep(5)
                    
                    # Login con usuario normal (root/admin) - usar la misma lógica que _login_huawei()
                    print("[SELENIUM] Login post-actualización con root/admin...")
                    
                    wait = WebDriverWait(driver, 20)
                    
                    # Campos de login
                    username_field = wait.until(
                        EC.presence_of_element_located((By.ID, "txt_Username"))
                    )
                    password_field = driver.find_element(By.ID, "txt_Password")
                    
                    username_field.clear()
                    username_field.send_keys("root")
                    password_field.clear()
                    password_field.send_keys("admin")
                    
                    time.sleep(0.5)
                    
                    # Click con JavaScript igual que en _login_huawei()
                    driver.execute_script("""
                        var btn = document.getElementById('loginbutton');
                        if (btn) { btn.click(); } else { console.log('loginbutton no encontrado'); }
                    """)
                    print("[SELENIUM] Click en botón login vía JS")
                    
                    # Esperar que cargue el menú
                    wait.until(
                        EC.presence_of_element_located((By.ID, "name_Systeminfo"))
                    )
                    print("[SELENIUM] Login post-actualización completado")
                    time.sleep(2)
                    
                    # Navegar a Device Info para leer la nueva versión
                    print("[SELENIUM] Navegando a Device Info para obtener nueva versión...")
                    self.nav_hw_info(driver)
                    time.sleep(2)
                    
                    # Leer la nueva versión
                    new_device_info = self.parse_hw_device(driver)
                    new_version = new_device_info.get('software_version', 'N/A')
                    print(f"[SUCCESS] Nueva versión detectada: {new_version}")
                    
                except Exception as e:
                    print(f"[WARNING] No se pudo verificar nueva versión: {e}")
                
                # Guardar registro de actualización con ambas versiones
                print("[INFO] Guardando registro de actualización...")
                if "software_update" not in self.test_results["tests"]:
                    self.test_results["tests"]["software_update"] = {}
                
                # Obtener versión anterior desde hw_device
                previous_version = self.test_results.get('tests', {}).get('hw_device', {}).get('data', {}).get('software_version', 'N/A')
                
                self.test_results["tests"]["software_update"] = {
                    "name": "software_update",
                    "status": True,
                    "details": {
                        "previous_version": previous_version,
                        "new_version": new_version,
                        "firmware_file": archivo,
                        "update_completed": True,
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                }
                
                print(f"[SUCCESS] Actualización de firmware completada")
                print(f"[INFO] Versión anterior: {previous_version}")
                print(f"[INFO] Versión nueva: {new_version}")
                print(f"[INFO] Archivo aplicado: {Path(archivo).name}")
                
                return True
                
            except Exception as e:
                print(f"[ERROR] Falló la actualización de firmware: {e}")
                return False
        else:
            print("[INFO] No se actualizará software")
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
                chrome_binary = self._get_chrome_binary_path()
                chrome_options.binary_location = chrome_binary
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
                # service = Service(ChromeDriverManager().install())
                driver_path = self._get_chromedriver_path()
                service = Service(driver_path)
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
                    print("[SELENIUM] Login HUAWEI completado, menú System Information visible.")
                    # return True
                except TimeoutException:
                    print("[SELENIUM] WARNING: No apareció 'name_Systeminfo' tras login (puede que el login haya fallado) o haya wizard.")
                    # Guardamos la pantalla resultante para revisar
                    # after_path = Path("debug_huawei_after_login.html")
                    # after_path.write_text(driver.page_source, encoding="utf-8")
                    # print(f"[SELENIUM] HTML tras login guardado en {after_path}")
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
                    # no reset de fabrica
                    # print("[INFO] No se saltó la página de configuración inicial o no se encontraron los skips")
                    # Verificar si se tiene que hacer el reset de fabrica
                    optTest = self.opcionesTest
                    tests_opts = optTest.get("tests", {})
                    if tests_opts.get("factory_reset", True):
                        def emit(kind, payload):
                            if self.out_q:
                                self.out_q.put((kind, payload))
                        emit("pruebas", "Ejecutando Reinicio de Fabrica")
                        reset_ok = self._reset_factory_huawei(driver)
                        time.sleep(110)

                        if(reset_ok):
                            # Guardar y emitir resultados
                            self.test_results.setdefault("tests", {})["factory_reset"] = {
                                "name": "factory_reset",
                                "status": True,
                                "data": {
                                    "result": "PASS"
                                }
                            }
                            #emit("test_individual", {"name": "factory_reset", "status": "PASS"})

                            # 1. Limpiar WiFi previo a relogin
                            try:
                                tests_dict = self.test_results.get("tests", {})
                                tests_dict.pop("hw_wifi24", None)
                                tests_dict.pop("hw_wifi5", None)
                                tests_dict.pop("hw_wifi24_pass", None)
                            except Exception:
                                pass

                            # 2. Desactivar factory_reset para no entrar en loop
                            try:
                                self.opcionesTest.setdefault("tests", {})["factory_reset"] = False
                            except Exception:
                                pass

                            # 3. Cerrar driver actual y hacer relogin
                            driver.quit()
                            return self._login_huawei()
                        else:
                            # Guardar y emitir fallo
                            self.test_results.setdefault("tests", {})["factory_reset"] = {
                                "name": "factory_reset",
                                "status": False,
                                "data": {
                                    "result": "FAIL"
                                }
                            }
                            #emit("test_individual", {"name": "factory_reset", "status": "FAIL"})
                            print("[INFO] No se reseteo de fabrica")
                
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

    def _login_huawei_super(self, driver):
        """Login con credenciales de Super Admin para actualización de firmware"""
        print("[SELENIUM] Haciendo logout y login con credenciales Super Admin...")
        
        try:
            # Borrar todas las cookies para forzar nuevo login
            print("[SELENIUM] Borrando cookies de sesión...")
            driver.delete_all_cookies()
            time.sleep(1)
            
            # Navegar directamente al login (más confiable que /logout.html)
            print("[SELENIUM] Navegando a página de login...")
            login_url = f"{self.base_url}/login.html"
            try:
                driver.get(login_url)
                time.sleep(3)
            except:
                # Si login.html falla, probar con la URL base
                print("[SELENIUM] login.html no disponible, intentando URL base...")
                driver.get(self.base_url)
                time.sleep(3)
            
            # Esperar y llenar formulario con credenciales Super Admin
            print("[SELENIUM] Esperando formulario de login...")
            
            # Intentar múltiples selectores para el campo username
            username_field = None
            username_selectors = [
                (By.ID, "Frm_Username"),
                (By.ID, "txt_Username"),
                (By.NAME, "Frm_Username"),
                (By.CSS_SELECTOR, "input[type='text']")
            ]
            
            for by, selector in username_selectors:
                try:
                    username_field = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((by, selector))
                    )
                    print(f"[SELENIUM] Campo username encontrado con {by}={selector}")
                    break
                except:
                    continue
            
            if not username_field:
                raise Exception("No se encontró campo de username")
            
            # Intentar múltiples selectores para el campo password
            password_field = None
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
            
            for by, selector in password_selectors:
                try:
                    password_field = driver.find_element(by, selector)
                    print(f"[SELENIUM] Campo password encontrado con {by}={selector}")
                    break
                except:
                    continue
            
            if not password_field:
                raise Exception("No se encontró campo de password")
            
            # Limpiar y llenar credenciales Super Admin
            username_field.clear()
            username_field.send_keys("telecomadmin")
            password_field.clear()
            password_field.send_keys("F0xB734Fr3@j%YEP")
            print("[SELENIUM] Credenciales Super Admin ingresadas")

            driver.execute_script("""
                var btn = document.getElementById('loginbutton');
                if (btn) { btn.click(); } else { console.log('loginbutton no encontrado'); }
            """)
            
            # Hacer clic en login
            #login_button = driver.find_element(By.ID, "LoginId")
            #login_button.click()
            #print("[SELENIUM] Click en botón login")
            # (Opcional) Exit / firstpage puede o no estar
            exit_btn = self.find_element_anywhere(driver, By.ID, "firstpage", desc="Exit (firstpage)", timeout=2)
            if exit_btn:
                try:
                    exit_btn.click()
                except Exception:
                    driver.execute_script("arguments[0].click();", exit_btn)
                time.sleep(1)
                driver.switch_to.default_content()
            time.sleep(5)
            
            # Verificar que el login fue exitoso esperando elemento CLICKEABLE
            print("[SELENIUM] Verificando login exitoso...")
            try:
                # Esperar que name_addconfig sea clickeable, no solo presente
                WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "name_addconfig"))
                )
                print("[SELENIUM] Login Super Admin completado exitosamente")
                return True
            except:
                print("[ERROR] Login Super Admin no completó correctamente - menú no disponible")
                # Guardar debug
                # try:
                #     driver.save_screenshot("debug_login_super_no_menu.png")
                #     with open("debug_login_super_no_menu.html", "w", encoding="utf-8") as f:
                #         f.write(driver.page_source)
                #     print("[DEBUG] Screenshot y HTML guardados")
                # except:
                #     pass
                return False
            
        except TimeoutException:
            print(f"[ERROR] Timeout esperando formulario de login después de logout")
            # Guardar screenshot para debug
            # try:
            #     driver.save_screenshot("debug_login_super_timeout.png")
            #     with open("debug_login_super_timeout.html", "w", encoding="utf-8") as f:
            #         f.write(driver.page_source)
            #     print("[DEBUG] Screenshot y HTML guardados para debug")
            # except:
            #     pass
            return False
        except Exception as e:
            print(f"[ERROR] Login Super Admin falló: {e}")
            # Guardar screenshot para debug
            # try:
            #     driver.save_screenshot("debug_login_super_failed.png")
            #     print("[DEBUG] Screenshot guardado: debug_login_super_failed.png")
            # except:
            #     pass
            return False