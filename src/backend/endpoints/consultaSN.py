import time
import re, html
import requests
from typing import Tuple
from typing import Dict
from src.backend.ont_automatico import _ping_once 
from datetime import datetime
from selenium.webdriver.chrome.options import Options
import sys
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import xml.etree.ElementTree as ET

COMMON_IPS = ["192.168.100.1", "192.168.1.1"]

def mostrarModelo(ip: str) -> Tuple[str, str]:
    # Detectar que modelo es:
    modelo_info = detectar_modelo_por_http(ip) # fabricante || codigo || modelo
    fabricante = modelo_info[0]
    codigo = modelo_info[1]
    modelo = modelo_info[2]
    if fabricante == "GRANDSTREAM" or fabricante == "ONT":
        # hacer emit en SN de no soportado por el momento
        print("No soportado...")
        return ["None", "None"]
    else:
        return [fabricante, modelo]

def mostrarSN(fabricante: str, modelo: str) -> str:
    print(f"Fabricante: {fabricante}")
    if fabricante == "FIBERHOME":
        # login fiber
        sn = login_fiber()
    elif fabricante == "ZTE":
        # login ZTE
        sn = login_zte()
    elif fabricante == "HUAWEI":
        # login HUAWEI
        sn = login_huawei()
    return sn

def _get_chrome_binary_path() -> str:
        if getattr(sys, "frozen", False):
            base_path = Path(sys._MEIPASS) / "backend" / "drivers" / "chrome"
        else:
            here = Path(__file__).resolve()
            backend_root = here.parent if here.parent.name == "backend" else here.parent.parent
            base_path = backend_root / "drivers" / "chrome"
        chrome_binary = base_path / "chrome.exe"
        print(f"[DEBUG] chrome binary = {chrome_binary}  exists={chrome_binary.exists()}")
        return str(chrome_binary)

def _get_chromedriver_path() -> str:
        """
        Devuelve la ruta al chromedriver.exe ubicado en:
        src/backend/drivers/chromedriver.exe
        """

        if getattr(sys, "frozen", False):
            # Ejecutándose desde un .exe (PyInstaller)
            # OJO: cuando empaquetes, usa algo como:
            #   --add-binary "src/backend/drivers/chromedriver.exe;backend/drivers"
            base_path = Path(sys._MEIPASS) / "backend" / "drivers"
        else:
            # Ejecutándose desde el código fuente
            here = Path(__file__).resolve()

            # Si ESTE archivo está en src/backend/endpoints/xxx.py -> subir a src/backend
            backend_root = here.parent
            if backend_root.name != "backend":
                backend_root = backend_root.parent  # sube un nivel más si hace falta

            base_path = backend_root / "drivers"

        driver_path = base_path / "chromedriver.exe"
        print(f"[DEBUG] chromedriver path = {driver_path}  exists={driver_path.exists()}")
        return str(driver_path)

def login_fiber() -> str:
    headless = True
    base_url = "http://192.168.100.1"

    chrome_options = Options()
    chrome_binary = _get_chrome_binary_path()
    chrome_options.binary_location = chrome_binary
    if headless:
        chrome_options.add_argument('--headless=new')  # Modo headless moderno
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--log-level=3')  # Suprimir logs verbosos
    chrome_options.add_argument(f'--host-resolver-rules=MAP * 192.168.100.1')
    
    # Deshabilitar warnings de certificado
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--allow-insecure-localhost')
    
    # Inicializar driver con WebDriver Manager
    print("[SELENIUM] Descargando/verificando ChromeDriver...")
    # service = Service(ChromeDriverManager().install())
    driver_path = _get_chromedriver_path()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    login_url = f"{base_url}/html/login_inter.html"
    # si está busy, espera a que libere (no reintentes creando sesiones)
    if not _wait_not_busy_login_page(driver, login_url, max_wait=240):
        print("[SELENIUM] Login bloqueado por sesión activa (no liberó).")
        return False
    driver.get(login_url)

    # Espera que cargue login
    WebDriverWait(driver, 5).until(
        EC.presence_of_element_located((By.ID, "user_name"))
    )

    USER = "root"
    PASS = "admin"

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
        el = find_element_anywhere(drv, By.ID, "first_menu_manage", desc="Management", timeout=1)
        if el:
            return "OK"

        return False

    res = WebDriverWait(driver, 20).until(post_login_ok)
    if res == "BUSY":
        print("[SELENIUM] Login bloqueado por sesión activa.")
        return "APAGUE Y VUELVA A PRENDER EL EQUIPO"

    print("[SELENIUM] Login OK (salí de login o ya hay frames).")

    session = requests.Session()
    for cookie in driver.get_cookies():
        session.cookies.set(cookie['name'], cookie['value'])
                
    # Extracción de SN
    snFinal = extraccionFiber(session)
    try:
        driver.quit()
    except:
        pass
    return snFinal

def extraccionFiber(session) -> str:
    sn = "---"
    base_info = _ajax_get(session, 'get_base_info')
    if base_info.get('gponsn'):
        # gponsn contiene el Serial Number Físico/PON directamente en HEX
        sn = base_info['gponsn']
        print(f"[INFO] Serial Number Físico/PON (gponsn): {sn}")
    return sn

def login_huawei():
     #login con selenium
    driver = None
    headless = True
    timeout = 2

    try:
        # Configurar opciones de Chrome
        chrome_options = Options()
        chrome_binary = _get_chrome_binary_path()
        chrome_options.binary_location = chrome_binary
        if headless:
            chrome_options.add_argument('--headless=new')  # Modo headless moderno
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')  # Suprimir logs verbosos
        chrome_options.add_argument(f'--host-resolver-rules=MAP * 192.168.100.1')
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
        driver_path = _get_chromedriver_path()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)
        
        # Navegar a la página principal (el router redirigirá al login)
        # Usar IP directa en lugar de login.html para evitar bloqueo de nginx
        base_url = f"http://192.168.100.1/"
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
            (By.ID, 'txt_Username'),        #HUAWEI
            (By.NAME, 'txt_Username'),      #HUAWEI
        ]
        
        password_selectors = [
            (By.ID, 'txt_Password'),        #HUAWEI
            (By.NAME, 'txt_Password'),      #HUAWEI
        ]

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
            print("[ERROR] No se encontro campo de contraseña")
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
        ]

        # 4) Comprobar si realmente existe el botón en el HTML
        page_html = driver.page_source
        if 'id="loginbutton"' not in page_html and "loginbutton" not in page_html:
            print("[SELENIUM] No se encontró ningún 'loginbutton' en el HTML.")
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
        time.sleep(2)  # Dar tiempo para procesar login
        cookies = {c["name"]: c["value"] for c in driver.get_cookies()}
        print("[SELENIUM] Cookies obtenidas:", cookies)

        session = requests.Session()
        session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/142.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "http://192.168.1.1/",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
        })
        session.cookies.update(cookies)

        # Antes de hacer la extraccion hay que confirmar si no es la primera vez conectando el Huawei
        salto = hw_maybe_skip_initial_guide(driver)
        if(salto):
            print("[INFO] Se saltó la pagina de configuración inicial")
            #hacer sesion otra vez
            #temp_bool = self._login_huawei()
        sn = huawei_info(driver)
        try:
            driver.quit()
        except:
            pass
        return sn
    except Exception as e:
        print(f"[ERROR] Selenium login falló: {type(e).__name__} - {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False

def huawei_info(driver) -> str:
    # navegacion
    """System Information -> Device (información básica)"""

    # 1) Menú principal "System Information"
    click_anywhere(
        driver,
        [
            (By.ID, "name_Systeminfo"),
            # (By.NAME, "m1div_deviceinfo"),
            # (By.XPATH, "//div[contains(@class,'menuContTitle') and normalize-space(.)='System Information']"),
        ],
        "Huawei System Information (menú principal)",
    )

    # Extracción
    sn_el = find_element_anywhere(
        driver, By.ID, "td3_2", desc="Serial (td3_2)"
    )
    sn_raw = sn_el.text.strip()
    serial_number = sn_raw.split()[0] if sn_raw else sn_raw
    
    return serial_number

def login_zte():
    driver = None
    headless = True
    timeout = 10
    try:
        # Configurar opciones de Chrome
        chrome_options = Options()
        chrome_binary = _get_chrome_binary_path()
        chrome_options.binary_location = chrome_binary
        if headless:
            chrome_options.add_argument('--headless=new')  # Modo headless moderno
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--log-level=3')  # Suprimir logs verbosos
        chrome_options.add_argument(f'--host-resolver-rules=MAP * 192.168.1.1')
        chrome_options.page_load_strategy = "eager"  # <- No esperar recursos innecesarios, solo con el DOM principal
        
        # Deshabilitar warnings de certificado
        chrome_options.add_argument('--ignore-certificate-errors')
        chrome_options.add_argument('--allow-insecure-localhost')
        
        # Inicializar driver con WebDriver Manager
        print("[SELENIUM] Descargando/verificando ChromeDriver...")
        # service = Service(ChromeDriverManager().install())
        driver_path = _get_chromedriver_path()
        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(timeout)
        
        # Navegar a la página principal (el router redirigirá al login)
        # Usar IP directa en lugar de login.html para evitar bloqueo de nginx
        base_url = f"http://192.168.1.1/"
        print(f"[SELENIUM] Navegando a {base_url}...")
        
        try:
            driver.set_page_load_timeout(30)
            driver.get(base_url)
        except Exception as e:
            print(f"[ERROR] No se pudo cargar {base_url}: {e}")
            #driver.quit()
            #return False
        
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
            (By.ID, 'Frm_Username'),        #ZTE
            (By.NAME, 'Frm_Username'),      #ZTE
        ]
        
        password_selectors = [
            (By.ID, 'Frm_Password'),        #ZTE
            (By.NAME, 'Frm_Password'),      #ZTE
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
            print("[ERROR] No se encontro campo de contrasena.")
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
            #login_button.click()
            print("[SELENIUM] Click en botón de login...")
        else:
            # Si no hay botón, enviar formulario con Enter
            print("[SELENIUM] Enviando formulario con Enter...")
            from selenium.webdriver.common.keys import Keys
            password_field.send_keys(Keys.RETURN)
        
        # Esperar a que cargue la página principal (varios indicadores posibles)
        time.sleep(5)  # Dar tiempo para procesar login
        #Petición extra:
        # Utilizando selenium para darle click a un boton || Tactica extrema, no intentar en casa
        button_selectors = [
            (By.ID, 'mgrAndDiag'),         # ZTE
            (By.LINK_TEXT, "Management & Diagnosis")
        ]
        
        mgmt = WebDriverWait(driver, 25).until(
            #EC.element_to_be_clickable((By.LINK_TEXT, "Management & Diagnosis"))
            EC.presence_of_element_located((By.XPATH, '//a[@title="Management & Diagnosis"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", mgmt)
        driver.execute_script("arguments[0].focus();", mgmt)
        driver.execute_script("arguments[0].click();", mgmt)
        #mgmt.click()
        # print("[DEBUG] URL:", driver.current_url)
        # print("[DEBUG] readyState:", driver.execute_script("return document.readyState"))
        # print("[DEBUG] page snippet:", driver.page_source[:200].lower())
        print("[SELENIUM] Click en Management & Diagnosis")
        
        time.sleep(1.5)

        # Debug EXTREMO
        # with open("zte_after_mgmt.html", "w", encoding="utf-8") as f:
        #     f.write(driver.page_source)
        # print("[DEBUG] HTML guardado como zte_after_mgmt.html")
        # 2) Ahora buscar el Status
        status = find_status_link(driver, timeout=10)
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
        session = requests.Session()
        session.headers.update({
            "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/142.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "http://192.168.1.1/",
            "Connection": "keep-alive",
            "X-Requested-With": "XMLHttpRequest",
        })
        session.cookies.update(cookies)

        #Mandar a llamar a las peticiones desde aqui para no cerrar el driver

        sn = zte_info(session, driver)
        
        try:
            driver.quit()
        except:
            pass
        return sn
    except Exception as e:
        print(f"[ERROR] Selenium login falló: {type(e).__name__} - {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return False

def zte_info(session: requests.Session, driver) -> str:
    base_url = f"http://192.168.1.1/"
    guid = str(int(time.time() * 1000))
    info = f"{base_url}/?_type=menuData&_tag=devmgr_statusmgr_lua.lua&_={guid}"
    
    # 2) Obtener el XML 
    # driver.get(info)
    r = session.get(info, timeout=5, verify=False)
    raw = r.text # driver.page_source
    print("[ZTE_INFO] Snippet:", raw[:500].replace("\n", " "))
    start = raw.find("<ajax_response_xml_root")
    end   = raw.rfind("</ajax_response_xml_root>") + len("</ajax_response_xml_root>")
    xml_final = raw[start:end]

    # 3) Parsear XML con tu función
    parsed = parse_zte_status_xml(xml_final)
    print(parsed)
    devinfo = parsed.get("DEVINFO")
    sn = devinfo.get("SerialNumber")

    return sn

def detectar_modelo_por_http(ip: str, timeout: int = 3) -> Tuple[str, str, str]:
    """
    Return:
      (tipo, model_code, model_name_str)
    tipo: 'FIBERHOME'|'HUAWEI'|'ZTE'|'GRANDSTREAM'|'ONT'
    model_code: 'MOD001'...'MOD009' o '' si no aplica
    model_name_str: texto detectado (title/ProductName) o ''
    """
    base_url = f"http://{ip}/"
    s = requests.Session()

    r = s.get(base_url, timeout=timeout, verify=False, allow_redirects=True)

    raw_html = r.text or ""
    html_lower = raw_html.lower()
    server_header = (r.headers.get("Server") or "").lower()
    html_normalized = html_lower.replace(" ", "").replace("\n", "").replace("\t", "")

    # 1) GRANDSTREAM
    if "grandstream" in html_lower or "grandstream" in server_header or "ht818" in html_lower:
        return ("GRANDSTREAM", "", "HT818")

    # 2) FIBERHOME
    if any(k in html_lower for k in ["fiberhome", "hg6145f", "user_name", "loginpp", "fh-text-security"]):
        model_code = "MOD001"
        if "hg6145f1" in html_lower:
            model_code = "MOD008"
        # si quieres regresar nombre:
        return ("FIBERHOME", model_code, "HG6145F" if "hg6145f" in html_lower else "HG6145F1")

    # 3) HUAWEI
    if any(k in html_normalized for k in ["huawei", "hg8145", "txt_username", "txt_password"]):
        product_name = ""

        m = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE)
        if m:
            product_name = m.group(1).upper().strip()

        if "HG8145" not in product_name:
            js = re.search(r"var\s+ProductName\s*=\s*['\"]([^'\"]+)['\"]", raw_html, re.IGNORECASE)
            if js:
                raw_js = js.group(1).upper()
                product_name = raw_js.replace("\\X2D", "-").replace("\\x2d", "-").strip()

        if "HG8145X6-10" in product_name:
            model_code = "MOD003"
        elif "HG8145X6" in product_name:
            model_code = "MOD007"
        elif "HG8145V5" in product_name:
            model_code = "MOD005" if "SMALL" in product_name else "MOD004"
        else:
            model_code = "MOD004"

        return ("HUAWEI", model_code, product_name)

    # 4) ZTE
    if any(k in html_lower for k in ["zte", "zxhn", "f670l", "f6600", "frm_username", "frm_password"]):
        zte_title = ""
        m = re.search(r"<title>(.*?)</title>", raw_html, re.IGNORECASE)
        if m:
            zte_title = html.unescape(m.group(1)).upper().strip()

        if "F6600" in zte_title:
            model_code = "MOD009"
        elif "F670L" in zte_title:
            model_code = "MOD002"
        else:
            model_code = "MOD002"

        return ("ZTE", model_code, zte_title)

    # fallback por segmento
    if ip == "192.168.100.1":
        return ("FIBERHOME", "MOD001", "POR CONFIRMAR")  
    return ("ONT", "", "")

def snFinal(out_q=None, stop_event=None) -> str:
    """
    Detectar la IP                                                      | ok
    Hacer emit de conexión                                              | ok
    Detectar el modelo                                                  | 
    Hacer login                                                         |
    Extraer SN                                                          |
    Hacer emit a la UI (maybe un nuevo kind para no mandar puro N/A)    |
    Hacer emit de desconexión (al desconectar)                          | ok
    """
    def emit(kind, payload):
        if out_q:
            out_q.put((kind, payload))
    
    # Hacer emit de que se está comenzando a buscar la IP
    emit("log", "Buscando IP...")

    last_state = None
    current_ip = None

    while True:
        if stop_event and stop_event.is_set():
            emit("log", "Consulta cancelada por cambio de modo")
            return

        # 1) detectar si hay equipo (ping a IPs)
        found_ip = None
        for ip in COMMON_IPS:
            if _ping_once(ip, timeout_ms=500):
                found_ip = ip
                break

        # 2) estado
        connected = found_ip is not None

        # 3) emitir solo si cambia el estado (anti-spam)
        if connected and (last_state != "connected" or current_ip != found_ip):
            current_ip = found_ip
            last_state = "connected"
            emit("con", "Dispositivo Conectado")
            # Marcar PING como PASS automáticamente al detectar conexión
            emit("individual_show", {"name": "ping", "status": "PASS"})
            emit("log", f"Conectado: {current_ip}")

            # Buscar el modelo
            fabricante, modelo = mostrarModelo(current_ip)
            emit("logSuper", modelo)
            emit("pruebas", f"Fabricante: {fabricante}")
            # Login + extraccion de sn
            sn = mostrarSN(fabricante, modelo)
            emit("sn", sn)

        if (not connected) and last_state != "disconnected":
            current_ip = None
            last_state = "disconnected"
            emit("con", "DESCONECTADO") 
            emit("log", "Desconectado")

        time.sleep(0.5)
    return ""


# Funciones adicionales necesarias
def _wait_not_busy_login_page(driver, login_url, max_wait=180):
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

def find_element_anywhere(driver, by, sel, desc="", timeout=5):
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

def _ajax_get(session, method: str, params: Dict = None) -> Dict:
        """Realiza peticion GET via AJAX endpoint"""
        params = params or {}
        params['ajaxmethod'] = method
        params['_'] = str(datetime.now().timestamp())
        
        try:
            response = session.get(
                "http://192.168.100.1/cgi-bin/ajax",#self.ajax_url, 
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

def find_status_link(driver, timeout=10):
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

def parse_zte_status_xml(xml_text: str) -> dict:
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

def hw_maybe_skip_initial_guide(driver, timeout=10):
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
                    element = find_element_anywhere(
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
        
def click_anywhere(driver, selectors, desc, timeout=5):
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

        try:
            driver.switch_to.default_content()
        except Exception:
            pass

        for by, sel in selectors:
            try:
                el = find_element_anywhere(
                    driver, by, sel,
                    desc=f"{desc} ({by}='{sel}')",
                    timeout=1
                )
                if el:
                    try:
                        driver.execute_script(
                            "arguments[0].scrollIntoView({block:'center', inline:'center'});",
                            el
                        )
                    except Exception:
                        pass

                    try:
                        el.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", el)

                    print(f"[SELENIUM] OK - Click: {desc} con {by}='{sel}'")
                    return True

            except StaleElementReferenceException as e:
                last_err = e
            except Exception as e:
                last_err = e

        time.sleep(0.25)

    print(f"[SELENIUM] No se encontró {desc} en {timeout}s")
    return False

"""
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠖⠃⠀⠀⠀⡁⠀⠀⠀⠀⠀⠐⠆⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡠⢔⡤⠊⠁⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⠀⠀⠁⠀⠀⠘⠁⢀⠀⠀⠀⠀⢈⠓⠂⠠⡄⠀⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣶⠿⠞⠋⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠒⠁⠀⠠⡚⠁⢀⣙⣀⣈⡩⠬⢁⠀⢑⠶⠤⡆⠤⡀⠀⠀⠀⠀⠀⠀⢀⠴⢲⣋⣽⣷⠟⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⠀⢠⠀⠀⣶⠃⠗⣡⣶⣮⣿⡿⠿⠿⢿⣿⣷⣶⣤⣤⠤⠴⠦⠬⣤⣤⠄⣉⠉⠝⢲⣿⡷⠻⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠈⠀⠀⠀⠀⠁⡀⡸⠁⣰⣿⡿⠛⠋⣁⡀⠤⠤⢄⡀⠈⠛⢯⣿⣟⣾⣶⣶⣮⣭⣵⣾⣿⣟⠿⠉⢨⠖⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠀⢠⠳⡧⣻⡿⠋⢀⠒⠉⠀⠀⠀⠀⠀⠀⠉⠢⠀⠀⠙⠛⣻⣿⣿⣿⢿⣿⣿⠟⡱⠖⠊⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⢠⣧⠓⣾⣿⠁⠀⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⢦⣠⣾⣿⠿⣿⣿⣿⡿⣫⠏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⡀⠀⠂⢃⣸⣿⠇⢠⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣠⣴⣿⠟⢿⠁⠸⡿⣿⣯⡶⠃⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠁⢘⡄⠘⣿⣿⠀⠸⡀⠀⠀⠀⠀⠀⢀⣀⣴⣾⣿⡿⡟⡋⠐⡇⠀⢸⣿⣿⠃⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢡⠘⢰⣿⡿⡆⠀⣇⠀⣀⣠⣤⣶⣿⢷⢟⠻⠀⠈⠀⠀⠀⡇⠀⣼⣿⣿⠂⠀⡀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⠔⢀⡴⢯⣾⠟⡏⢀⣠⣿⣿⣿⣟⢟⡋⠅⠘⠉⠀⠀⠀⠀⢀⠀⠁⢠⣿⣟⠃⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢠⠞⣻⣷⡿⢙⣩⣶⡿⠿⠛⠉⠑⢡⡁⠀⠀⠀⠀⠀⠀⢀⠔⠁⠀⣰⣿⣿⡟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣡⣾⣥⣾⢫⡦⠾⠛⠙⠉⠀⠀⢀⣀⠀⠈⠙⠓⠦⠤⠤⠀⠘⠁⢀⡤⣾⡿⠏⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⠀⠀⠔⣴⣾⣿⣿⢟⢝⠢⠃⢀⣤⢴⣾⣮⣷⣶⢿⣶⡤⣐⡀⠀⣠⣤⢶⣪⣿⣿⡿⠟⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⠀⠀⠀⡀⣦⣾⡿⡛⠵⠺⢈⡠⠶⠿⠥⠥⡭⠉⠉⢱⡛⠻⠿⣿⣿⣿⣿⣿⠿⠿⠿⠟⠭⠛⠂⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⠀⠀⠀⢀⢴⠕⣋⠝⠕⠐⠀⠔⠉⠀⠀⠀⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠉⠁⠉⠁⠁⠁⠁⠈⠀⠁⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
⢀⣠⠁⠈⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀
"""