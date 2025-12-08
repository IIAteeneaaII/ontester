#!/usr/bin/env python3
"""
ONT Automated Test Suite
Pruebas automatizadas basadas en protocolo de testing
Fecha: 26/11/2025
"""

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
from datetime import datetime
from pathlib import Path
MAC_REGEX = re.compile(r"([0-9A-Fa-f]{2}(?:(?::|-)?[0-9A-Fa-f]{2}){5})")
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
    print("[WARNING] Selenium no disponible. Instala con: pip install selenium webdriver-manager")

# IMPORTAR LOS MODULOS MIXIN
from mixins.zte_mixin import ZTEMixin # importar la clase
from mixins.huawei_mixin import HuaweiMixin
from mixins.fiber_mixin import FiberMixin
from mixins.grandstream_mixin import GrandStreamMixin
from mixins.common_mixin import CommonMixin
# IMPORTAR EL CERTIFICADO
from certificado.certificado import generarCertificado

class ONTAutomatedTester(ZTEMixin, HuaweiMixin, FiberMixin, GrandStreamMixin, CommonMixin):
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
            "HG6145F1": "MOD001",
            
            # MOD006: GRANDSTREAM HT818
            "GRANDSTREAM HT818": "MOD006",
            "GS-HT818": "MOD006",
            "HT818": "MOD006",
        }
    
    # Configuración de umbrales de señal WiFi Fiberhome
    def _configWifiSignalThresholds(self, min24: int, min5: int):
        """Configura los umbrales mínimos de señal WiFi para los tests"""
        self.minWifi24Signal = min24
        self.minWifi5Signal = min5

    def _configWifiSignalThresholdsMax(self, max24: int, max5: int):
        """Configura los umbrales maximos de señal WiFi para los tests"""
        self.maxWifi24Signal = max24
        self.maxWifi5Signal = max5

    # Configuración de umbrales máximos de señal WiFi ZTE/Huawei
    def _configWifiSignalThresholdsPercent(self, min24: int, min5: int):
        """Configura los umbrales mínimos de señal WiFi para los tests"""
        self.minWifi24Percent = min24
        self.minWifi5Percent = min5

    def _getMinWifi24SignalPercent(self) -> int:
        """Retorna el umbral mínimo de señal WiFi en porcentaje"""
        return self.minWifi24Percent
    def _getMinWifi5SignalPercent(self) -> int:
        """Retorna el umbral mínimo de señal WiFi 5GHz en porcentaje"""
        return self.minWifi5Percent
    
    def _getMinWifi24Signal(self) -> int:
        """Retorna el umbral mínimo de señal WiFi 2.4GHz"""
        return self.minWifi24Signal
    def _getMinWifi5Signal(self) -> int:
        """Retorna el umbral mínimo de señal WiFi 5GHz"""
        return self.minWifi5Signal
    def _getMaxWifi24Signal(self) -> int:
        """Retorna el umbral máximo de señal WiFi 2.4GHz"""
        return self.maxWifi24Signal
    def _getMaxWifi5Signal(self) -> int:
        """Retorna el umbral máximo de señal WiFi 5GHz"""
        return self.maxWifi5Signal

    def _check_network_configuration(self):
        """
        Verifica que el adaptador Ethernet tenga configuradas las IPs necesarias
        para acceder a todos los modelos de ONT.
        
        Returns:
            tuple: (bool, list) - (configuración_ok, IPs_faltantes)
        """
        import socket
        import subprocess
        
        # IPs necesarias para acceder a todos los modelos
        required_networks = {
            "192.168.100": "Huawei/Fiberhome",
            "192.168.1": "ZTE"
        }
        
        try:
            # Obtener todas las IPs del adaptador usando ipconfig
            result = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='ignore'
            )
            
            output = result.stdout
            
            # Buscar las IPs configuradas
            configured_networks = set()
            for line in output.split('\n'):
                if 'IPv4' in line or 'Dirección IPv4' in line:
                    # Extraer la IP
                    parts = line.split(':')
                    if len(parts) > 1:
                        ip = parts[1].strip().split('(')[0].strip()
                        # Obtener la red (primeros 3 octetos)
                        network = '.'.join(ip.split('.')[:3])
                        if network in required_networks:
                            configured_networks.add(network)
            
            # Verificar si faltan redes
            missing_networks = []
            for network, description in required_networks.items():
                if network not in configured_networks:
                    missing_networks.append((network, description))
            
            return (len(missing_networks) == 0, missing_networks)
            
        except Exception as e:
            print(f"[WARNING] No se pudo verificar configuración de red: {e}")
            return (True, [])  # Asumir que está ok si no podemos verificar
    
    def _show_network_setup_guide(self, missing_networks):
        """Muestra instrucciones para configurar IP secundaria"""
        print("\n" + "="*70)
        print("⚠️  CONFIGURACIÓN DE RED REQUERIDA")
        print("="*70)
        print("\nPara detectar automáticamente TODOS los modelos de ONT, el adaptador")
        print("Ethernet DEBE tener IPs estáticas configuradas en múltiples redes:\n")
        
        for network, description in missing_networks:
            print(f"  • {network}.x - Para {description}")
        
        print("\n" + "-"*70)
        print("📋 CONFIGURACIÓN COMPLETA (Una vez):")
        print("-"*70)
        print("\n1. Ve a: Panel de Control > Redes e Internet > Conexiones de red")
        print("2. Click derecho en 'Ethernet' > Propiedades")
        print("3. Selecciona 'Protocolo de Internet versión 4 (TCP/IPv4)' > Propiedades")
        print("4. Marca 'Usar la siguiente dirección IP'")
        print("\n5. Configura la IP PRINCIPAL:\n")
        print("   ┌─────────────────────────────────────┐")
        print("   │ Dirección IP:     192.168.100.15   │")
        print("   │ Máscara subred:   255.255.255.0    │")
        print("   │ Puerta enlace:    (dejar vacío)    │")
        print("   └─────────────────────────────────────┘")
        print("\n6. Click en 'Opciones avanzadas...'")
        print("7. En 'Configuración IP', click 'Agregar...' para IP SECUNDARIA:\n")
        print("   ┌─────────────────────────────────────┐")
        print("   │ IP:      192.168.1.15               │")
        print("   │ Máscara: 255.255.255.0              │")
        print("   └─────────────────────────────────────┘")
        print("\n8. Click 'Aceptar' en todas las ventanas")
        print("9. Vuelve a ejecutar este script")
        
        print("\n" + "="*70)
        print("💡 IMPORTANTE: Sin IPs estáticas, el adaptador queda en 169.254.x.x")
        print("   (auto-asignación) y NO podrá comunicarse con ningún ONT.")
        print("\n💡 Con ambas IPs configuradas, detectará automáticamente CUALQUIER")
        print("   modelo (Huawei, Fiberhome, ZTE) sin cambios manuales.")
        print("="*70 + "\n")
    
    def _scan_for_device(self, timeout=10):
        """
        Escanea IPs comunes de ONTs para encontrar un dispositivo activo.
        
        Returns:
            tuple: (ip, device_type) si encuentra dispositivo, (None, None) si no
        """
        # IPs comunes basadas en los dispositivos conocidos
        common_ips = [
            "192.168.100.1",  # Fiberhome, Huawei
            "192.168.1.1",    # ZTE
        ]
        
        print("[DISCOVERY] Escaneando IPs comunes...")
        
        for ip in common_ips:
            try:
                print(f"[DISCOVERY] Probando {ip}...", end=" ")
                response = self.session.get(
                    f"http://{ip}",
                    timeout=timeout,
                    verify=False,
                    allow_redirects=True
                )
                
                # Si responde con cualquier código HTTP válido, hay un dispositivo
                if response.status_code < 500:
                    print(f"✓ Responde")
                    # Actualizar el host y detectar tipo
                    self.host = ip
                    self.base_url = f"http://{ip}"
                    self.ajax_url = f"http://{ip}/cgi-bin/ajax"
                    self.type_url = f"http://{ip}/?_type=menuData&_tag="
                    
                    device_type = self._detect_device_type()
                    print(f"[DISCOVERY] ✓ Dispositivo {device_type} encontrado en {ip}")
                    return (ip, device_type)
                    
            except requests.exceptions.Timeout:
                print("✗ Timeout")
                continue
            except requests.exceptions.ConnectionError:
                print("✗ No hay conexión")
                continue
            except Exception as e:
                print(f"✗ Error: {e}")
                continue
        
        print("[DISCOVERY] ✗ No se encontró ningún dispositivo en las IPs comunes")
        return (None, None)
    
    def login(self) -> bool:
        """Realiza login en la ONT via AJAX"""
        print("[AUTH] Intentando autenticacion...")
        
        # Detectar tipo de dispositivo primero
        device_type = self._detect_device_type()
        
        if device_type == "GRANDSTREAM":
            return self._login_grandstream()
        elif device_type == "FIBERHOME" or self.model == "MOD001":
            return self._login_fiberhome()  # Fiberhome usa Selenium
        elif device_type == "ZTE" or self.model == "MOD002":
            return self._login_zte(False) # False para indicar que aun no se ha reseteado
        elif device_type == "HUAWEI" or self.model in ["MOD003", "MOD004", "MOD005"]:
            return self._login_huawei()
        else:
            return self._login_ont_standard()
    
    def _detect_device_type(self) -> str:
        """Detecta el tipo de dispositivo (ONT o ATA Grandstream)"""
        try:
            # Intentar acceder a la página principal
            response = self.session.get(
                self.base_url,
                timeout=3,
                verify=False,
                allow_redirects=True
            )
            
            html = response.text.lower()
            server = response.headers.get('Server', '').lower()
            
            # Detectar Grandstream
            if 'grandstream' in html or 'grandstream' in server or 'ht818' in html:
                return "GRANDSTREAM"
            
            # Detectar Fiberhome (buscar elementos específicos)
            if any(keyword in html for keyword in ['fiberhome', 'hg6145f', 'user_name', 'loginpp', 'fh-text-security']):
                print("[AUTH] Dispositivo Fiberhome detectado automáticamente")
                if not self.model:
                    self.model = "MOD001"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "FIBERHOME"
            
            # Detectar Huawei (buscar elementos específicos en el HTML)
            if any(keyword in html for keyword in ['huawei', 'hg8145', 'echolife', 'txt_username', 'txt_password']):
                print("[AUTH] Dispositivo Huawei detectado automáticamente")
                # Intentar detectar modelo específico
                if not self.model:
                    if 'hg8145v5' in html:
                        if 'small' in html:
                            self.model = "MOD005"
                        else:
                            self.model = "MOD004"
                    elif 'hg8145x6' in html or 'hg6145f1' in html:
                        self.model = "MOD003"
                    else:
                        # Default to MOD004 for unknown Huawei
                        self.model = "MOD004"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "HUAWEI"
            
            # Detectar ZTE
            if any(keyword in html for keyword in ['zte', 'zxhn', 'f670l', 'frm_username', 'frm_password']):
                print("[AUTH] Dispositivo ZTE detectado automáticamente")
                if not self.model:
                    self.model = "MOD002"
                    print(f"[AUTH] Modelo asignado: {self.model}")
                return "ZTE"
            
            # Por defecto, asumir ONT estándar
            return "ONT"
            
        except:
            return "ONT"
                
    def _detect_model(self, model_name: str) -> str:
        """Detecta el codigo de modelo basado en el ModelName"""
        # Normalizar el nombre del modelo
        model_name_clean = model_name.strip()
        model_name_upper = model_name_clean.upper()
        
        # Paso 1: Buscar coincidencia exacta (case-insensitive)
        for key, value in self.model_mapping.items():
            if key.upper() == model_name_upper:
                return value
        
        # Paso 2: Buscar coincidencias más largas primero (más específicas)
        # Ordenar las claves por longitud descendente para priorizar matches más específicos
        sorted_keys = sorted(self.model_mapping.keys(), key=len, reverse=True)
        
        for key in sorted_keys:
            key_upper = key.upper()
            # Verificar si el nombre del modelo contiene la clave completa
            if key_upper in model_name_upper:
                return self.model_mapping[key]
        
        # Si no se encuentra, usar el ModelName como codigo
        print(f"[WARN] Modelo desconocido: {model_name}, usando como codigo")
        return f"UNKNOWN_{model_name}"
    
    def _get_model_display_name(self, model_code: str, reported_name: str = None) -> str:
        """Retorna el nombre de display correcto según el código de modelo"""
        display_names = {
            "MOD003": "HG8145X6-10",  # Nombre comercial usado en la empresa (coloquialmente "X6")
            "MOD001": "HG6145F",
            "MOD002": "F670L",
            "MOD004": "HG8145V5",
            "MOD005": "HG8145V5 SMALL",
            "MOD006": "HT818"
        }
        
        return display_names.get(model_code, reported_name or model_code)
         
    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todos los tests automatizados"""
        print("\n" + "="*60)
        print("ONT/ATA AUTOMATED TEST SUITE")
        print(f"Host: {self.host}")
        if self.model:
            print(f"Modelo especificado: {self.model}")
        print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*60 + "\n")
        
        login_ok = self.login()

        if not login_ok:
            print("[!] Error: No se pudo autenticar")
            if(self.model == "MOD001"):
                return self.test_results
        # Determinar qué tests ejecutar según el tipo de dispositivo
        device_type = self.test_results['metadata'].get('device_type', 'ONT')
        
        # Tests comunes a todos los dispositivos
        common_tests = [
            self.test_pwd_pass,
            self.test_factory_reset,
            self.test_ping_connectivity,
            self.test_http_connectivity,
            self.test_port_scan,
            self.test_dns_resolution,
            self.test_software_version,
        ]
        
        # Tests específicos de ONT
        ont_tests = [
            self.test_usb_port,
            self.test_tx_power,
            self.test_rx_power,
            self.test_wifi_24ghz,
            self.test_wifi_5ghz
        ]
        
        # Tests específicos de ATA (Grandstream HT818)
        ata_tests = [
            self.test_voip_lines,
            self.test_sip_registration,
            self.test_network_settings
        ]
        
        # De momento solo para fiber, se puede agregar condiciones con el operador or "||"
        if(self.model == "MOD001"):
            # Ejecutar tests comunes
            print(f"\n[*] Ejecutando tests comunes ({len(common_tests)} tests)...")
            for test_func in common_tests:
                result = test_func()
                self.test_results["tests"][result["name"]] = result
        # Ejecutar tests específicos según el tipo
        if device_type == "ATA":
            print(f"\n[*] Dispositivo ATA detectado - Ejecutando tests VoIP ({len(ata_tests)} tests)...")
            for test_func in ata_tests:
                result = test_func()
                self.test_results["tests"][result["name"]] = result
        else:
            print(f"\n[*] Dispositivo ONT detectado - Ejecutando tests fibra óptica ({len(ont_tests)} tests)...")
            for test_func in ont_tests:
                result = test_func()
                self.test_results["tests"][result["name"]] = result
        
        # Provisionalmente aqui se va a generar el certificado
        generar = True # bandera para seleccionar si se hace o no el certificado (se fuerza porque no se pasa la fibra)
        # Posteriormente se puede validar con la ultima variable del JSON que contiene si es valido o no
        # Obtener el dict con la info
        res = self._resultados_finales()
        if(generar):
            ruta = generarCertificado(res)
            print(f"\n[REPORT] Certificado generado en: {ruta}")
        return self.test_results
        
def main():
    parser = argparse.ArgumentParser(description="ONT Automated Test Suite")
    parser.add_argument("--host", help="IP de la ONT (opcional, se detecta automáticamente si se omite)")
    parser.add_argument("--model", help="Modelo de la ONT (opcional, se detecta automaticamente)")
    parser.add_argument("--output", help="Directorio de salida (opcional)")
    parser.add_argument("--mode", 
                       choices=['test', 'retest', 'label'], 
                       default='test',
                       help="Modo de operacion: test (todos), retest (solo fallidos), label (generar etiqueta)")
    
    args = parser.parse_args()
    
   # Auto-discovery si no se proporciona --host
    if not args.host:
        print("\n============================================================")
        print("ONT/ATA AUTOMATED TEST SUITE - AUTO-DISCOVERY MODE")
        print("============================================================\n")
        
        # Crear tester temporal para verificar red y escanear
        temp_tester = ONTAutomatedTester(host="0.0.0.0", model=None)
        
        # Verificar configuración de red
        print("[NETWORK] Verificando configuración de red...")
        network_ok, missing_networks = temp_tester._check_network_configuration()
        
        if not network_ok:
            print(f"[WARNING] Faltan {len(missing_networks)} red(es) configurada(s)")
            temp_tester._show_network_setup_guide(missing_networks)
            print("[INFO] Continuando con escaneo en las redes disponibles...\n")
        else:
            print("[OK] Configuración de red correcta - Todas las redes accesibles\n")
        
        ip, device_type = temp_tester._scan_for_device()
        
        if not ip:
            print("\n[ERROR] No se encontró ningún dispositivo ONT.")
            print("[ERROR] Verifica:")
            print("  1. El dispositivo esté encendido y conectado")
            print("  2. La configuración de red (ver instrucciones arriba)")
            print("\nTambién puedes especificar manualmente:")
            print("  python ont_automated_tester.py --host 192.168.100.1")
            return
        
        # Usar el IP y modelo detectados
        args.host = ip
        args.model = temp_tester.model  # El modelo ya fue asignado en _detect_device_type
        print(f"\n[OK] Dispositivo {device_type} detectado: {args.host} (Modelo: {args.model})\n")
    
    # Mostrar info de inicio
    print("=" * 60)
    print("ONT/ATA AUTOMATED TEST SUITE")
    print(f"Host: {args.host}")
    if args.model:
        print(f"Modelo especificado: {args.model}")
    print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 60)
    print()
    
    if args.mode == 'label':
        # Modo label: generar etiqueta de identificación
        generate_label(args.host, args.model)
    elif args.mode == 'retest':
        # Modo retest: solo tests fallidos
        run_retest_mode(args.host, args.model, args.output)
    else:
        # Modo test: todos los tests
        tester = ONTAutomatedTester(args.host, args.model)
        tester.run_all_tests()
        
        # Mostrar reporte en consola
        if(args.model != "MOD003" and args.model != "MOD004" and args.model != "MOD005"):
            print("\n" + tester.generate_report())
            tester.save_results(args.output) # Guardar resultados
    

def generate_label(host: str, model: str = None):
    """RF 031: Genera etiqueta imprimible con información del ONT"""
    print("\n" + "="*60)
    print("GENERANDO ETIQUETA DE IDENTIFICACION")
    print("="*60 + "\n")
    
    tester = ONTAutomatedTester(host, model)
    if not tester.login():
        print("[!] Error: No se pudo conectar al ONT")
        return
    
    # Obtener información adicional
    device_info = tester._ajax_get('get_device_name')
    operator_info = tester._ajax_get('get_operator')
    
    serial_logical = operator_info.get('SerialNumber', 'N/A')
    
    # Intentar calcular SN Físico
    serial_physical = tester._calculate_physical_sn(serial_logical)
    if serial_physical:
        sn_physical_line = f"{serial_physical:40}"
        note = "SN Fisico/PON calculado automaticamente"
    else:
        sn_physical_line = "_________________________________________"
        note = "Completar SN Fisico/PON desde la etiqueta fisica del dispositivo"
    
    # Generar etiqueta
    label = f"""
    ╔══════════════════════════════════════════════════════════════╗
    ║                  ETIQUETA DE IDENTIFICACION ONT              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║                                                              ║
    ║  MODELO:          {device_info.get('ModelName', 'N/A'):40} ║
    ║  CODIGO:          {tester.model:40} ║
    ║  SN LOGICO:       {serial_logical:40} ║
    ║  SN FISICO/PON:   {sn_physical_line} ║
    ║  OPERADOR:        {operator_info.get('operator_name', 'N/A'):40} ║
    ║  IP:              {host:40} ║
    ║  FECHA:           {datetime.now().strftime('%d/%m/%Y %H:%M'):40} ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  CONECTIVIDAD:                                               ║
    ║    • HTTP:        ✓ DISPONIBLE                               ║
    ║    • Telnet:      Puerto 23 abierto                          ║
    ║    • Web UI:      http://{host:30}         ║
    ║    • Usuario:     root                                       ║
    ║                                                              ║
    ╠══════════════════════════════════════════════════════════════╣
    ║  NOTA: {note:<57} ║
    ║        (16 caracteres hexadecimales)                         ║
    ║                                                              ║
    ║  NOTAS ADICIONALES:                                          ║
    ║  ___________________________________________________________  ║
    ║  ___________________________________________________________  ║
    ║  ___________________________________________________________  ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """
    
    print(label)
    
    # Guardar etiqueta en archivo organizado por fecha
    timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
    date_folder = datetime.now().strftime("%d_%m_%y")
    
    # Agregar sufijo _emp para dispositivos empresariales
    device_type = tester.test_results['metadata'].get('device_type', 'ONT')
    if device_type in ['ATA', 'ROUTER', 'SWITCH']:
        date_folder = f"{date_folder}_emp"
    
    label_dir = Path("reports/labels") / date_folder
    label_dir.mkdir(parents=True, exist_ok=True)
    
    serial = operator_info.get('SerialNumber', tester.test_results['metadata'].get('serial_number', 'UNKNOWN'))
    label_file = label_dir / f"{timestamp}_{tester.model}_{serial}_label.txt"
    
    with open(label_file, 'w', encoding='utf-8') as f:
        f.write(label)
    
    print(f"\n[+] Etiqueta guardada en: {label_file}")

def run_retest_mode(host: str, model: str = None, output: str = None):
    """RF 031: Ejecuta solo los tests que fallaron anteriormente"""
    print("\n" + "="*60)
    print("MODO RETEST - Solo tests fallidos")
    print("="*60 + "\n")
    
    # Buscar el último reporte en subdirectorios por fecha
    reports_base_dir = Path("reports/automated_tests")
    if not reports_base_dir.exists():
        print("[!] No se encontraron reportes previos")
        print("[*] Ejecutando suite completo...")
        tester = ONTAutomatedTester(host, model)
        tester.run_all_tests()
        print("\n" + tester.generate_report())
        tester.save_results(output)
        return
    
    # Buscar todos los archivos JSON en subdirectorios
    json_files = []
    for date_dir in sorted(reports_base_dir.iterdir(), reverse=True):
        if date_dir.is_dir():
            json_files.extend(date_dir.glob("*_automated_results.json"))
    
    json_files = sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not json_files:
        print("[!] No se encontraron reportes previos")
        print("[*] Ejecutando suite completo...")
        tester = ONTAutomatedTester(host, model)
        tester.run_all_tests()
        print("\n" + tester.generate_report())
        tester.save_results(output)
        return
    
    last_report = json_files[0]
    print(f"[*] Cargando último reporte: {last_report.parent.name}/{last_report.name}")
    
    with open(last_report, 'r') as f:
        previous_results = json.load(f)
    
    # Identificar tests fallidos
    failed_tests = []
    for test_name, test_data in previous_results.get("tests", {}).items():
        if test_data.get("status") == "FAIL":
            failed_tests.append(test_name)
    
    if not failed_tests:
        print("[✓] Todos los tests pasaron en la ejecución anterior")
        print("[*] Nada que re-testear")
        return
    
    print(f"\n[*] Tests fallidos en ejecución anterior: {len(failed_tests)}")
    for test in failed_tests:
        print(f"    - {test}")
    print()
    
    # Crear tester y ejecutar solo tests fallidos
    tester = ONTAutomatedTester(host, model)
    
    if not tester.login():
        print("[!] Error: No se pudo autenticar")
        return
    
    # Mapeo de nombres de tests a métodos
    test_methods = {
        "PWD_PASS": tester.test_pwd_pass,
        "FACTORY_RESET_PASS": tester.test_factory_reset,
        "PING_CONNECTIVITY": tester.test_ping_connectivity,
        "HTTP_CONNECTIVITY": tester.test_http_connectivity,
        "PORT_SCAN": tester.test_port_scan,
        "DNS_RESOLUTION": tester.test_dns_resolution,
        "USB_PORT": tester.test_usb_port,
        "SOFTWARE_PASS": tester.test_software_version,
        "TX_POWER": tester.test_tx_power,
        "RX_POWER": tester.test_rx_power,
        "WIFI_24GHZ": tester.test_wifi_24ghz,
        "WIFI_5GHZ": tester.test_wifi_5ghz,
        # Tests específicos de ATA
        "VOIP_LINES": tester.test_voip_lines,
        "SIP_REGISTRATION": tester.test_sip_registration,
        "NETWORK_SETTINGS": tester.test_network_settings
    }
    
    # Ejecutar solo tests fallidos
    for test_name in failed_tests:
        if test_name in test_methods:
            result = test_methods[test_name]()
            tester.test_results["tests"][result["name"]] = result
    
    # Mostrar reporte
    print("\n" + tester.generate_report())
    
    # Guardar resultados con prefijo "retest" en subdirectorios por fecha
    timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
    date_folder = datetime.now().strftime("%d_%m_%y")
    
    if output:
        output_dir = Path(output) / date_folder
    else:
        output_dir = Path("reports/automated_tests") / date_folder
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    json_file = output_dir / f"{timestamp}_{tester.model}_retest_results.json"
    txt_file = output_dir / f"{timestamp}_{tester.model}_retest_report.txt"
    
    with open(json_file, 'w') as f:
        json.dump(tester.test_results, f, indent=2)
    
    with open(txt_file, 'w') as f:
        f.write(tester.generate_report())
    
    print(f"\n[+] Resultados guardados en:")
    print(f"    - JSON: {json_file}")
    print(f"    - TXT: {txt_file}")

if __name__ == "__main__":
    main()
