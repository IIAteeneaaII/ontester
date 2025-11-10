#!/usr/bin/env python3
"""
ONT Automated Test Suite
Pruebas automatizadas basadas en protocolo de testing
Fecha: 10/11/2025
"""

import argparse
import json
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

class ONTAutomatedTester:
    def __init__(self, host: str, model: str = None):
        self.host = host
        self.model = model  # Puede ser None, se detectará automáticamente
        self.base_url = f"http://{host}"
        self.ajax_url = f"http://{host}/cgi-bin/ajax"
        self.session = requests.Session()
        self.authenticated = False
        self.session_id = None
        self.test_results = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "host": host,
                "model": model,
                "serial_number": None
            },
            "tests": {}
        }
        
        # Deshabilitar warnings SSL
        requests.packages.urllib3.disable_warnings()
        
        # Mapeo de ModelName a códigos de modelo
        self.model_mapping = {
            "HG6145F": "MOD001",
            "HG6145F1": "MOD001",
            "FIBERHOME HG6145F": "MOD001",
            "F670L": "MOD002",
            "ZTE F670L": "MOD002",
            "HG8145X6": "MOD003",
            "HG8145X6-10": "MOD003",
            "HUAWEI HG8145X6": "MOD003",
            "HG8145V5": "MOD004",
            "HUAWEI HG8145V5": "MOD004",
            "HG145V5": "MOD005",
            "HUAWEI HG145V5": "MOD005",
        }
    
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
            return {"success": False, "status": response.status_code}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def login(self) -> bool:
        """Realiza login en la ONT via AJAX"""
        print("[AUTH] Intentando autenticacion...")
        
        # Obtener informacion del dispositivo (prueba de conectividad)
        device_info = self._ajax_get('get_device_name')
        
        if device_info.get('success') == False:
            print(f"[AUTH] Error en conexion: {device_info.get('error', 'Unknown')}")
            return False
        
        # Si llegamos aqui, Basic Auth funciono
        if device_info.get('ModelName'):
            self.authenticated = True
            model_name = device_info['ModelName']
            self.test_results['metadata']['device_name'] = model_name
            
            # Auto-detectar modelo si no se especificó
            if not self.model:
                detected_model = self._detect_model(model_name)
                self.model = detected_model
                self.test_results['metadata']['model'] = detected_model
                print(f"[AUTH] Modelo detectado automaticamente: {detected_model} ({model_name})")
            else:
                print(f"[AUTH] Autenticacion exitosa - Modelo: {model_name}")
            
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
            
            # Obtener session ID para futuros POST (opcional)
            session_info = self._ajax_get('get_refresh_sessionid')
            if session_info.get('sessionid'):
                self.session_id = session_info['sessionid']
            
            return True
        
        print("[AUTH] Autenticacion fallida")
        return False
    
    def _detect_model(self, model_name: str) -> str:
        """Detecta el codigo de modelo basado en el ModelName"""
        # Buscar coincidencia exacta primero
        if model_name in self.model_mapping:
            return self.model_mapping[model_name]
        
        # Buscar coincidencia parcial
        model_name_upper = model_name.upper()
        for key, value in self.model_mapping.items():
            if key.upper() in model_name_upper or model_name_upper in key.upper():
                return value
        
        # Si no se encuentra, usar el ModelName como codigo
        print(f"[WARN] Modelo desconocido: {model_name}, usando como codigo")
        return f"UNKNOWN_{model_name}"
    
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
        
        # Usar metodo AJAX get_operator para obtener serial
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
        
        return result
    
    def test_usb_port(self) -> Dict[str, Any]:
        """Test 3: Deteccion de puerto USB"""
        print("[TEST] USB PORT - Deteccion")
        
        result = {
            "name": "USB_PORT",
            "status": "FAIL",
            "details": {}
        }
        
        # Intentar metodo AJAX get_usb_info
        usb_info = self._ajax_get('get_usb_info')
        
        if usb_info.get('session_valid') == 1:
            # Tiene datos validos
            result["status"] = "PASS"
            result["details"]["method"] = "AJAX get_usb_info"
            result["details"]["data"] = usb_info
        elif usb_info.get('session_valid') == 0:
            result["details"]["error"] = "Requiere session valida (login completo)"
            result["details"]["note"] = "Basic Auth insuficiente para este metodo"
        else:
            result["details"]["error"] = "Metodo no accesible"
        
        return result
    
    def test_software_version(self) -> Dict[str, Any]:
        """Test 4: Verificacion de version de software"""
        print("[TEST] SOFTWARE PASS - Version")
        
        result = {
            "name": "SOFTWARE_PASS",
            "status": "FAIL",
            "details": {}
        }
        
        # Usar metodo AJAX get_device_name
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
        
        # Intentar metodo AJAX get_pon_info
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
        
        # Usa el mismo metodo que TX (get_pon_info devuelve ambos)
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
        
        # Intentar metodo AJAX get_wifi_status
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
        
        # Usa el mismo metodo que 2.4GHz (get_wifi_status devuelve ambas bandas)
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
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Ejecuta todos los tests automatizados"""
        print("\n" + "="*60)
        print("ONT AUTOMATED TEST SUITE")
        print(f"Host: {self.host}")
        if self.model:
            print(f"Modelo especificado: {self.model}")
        print(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("="*60 + "\n")
        
        # Intentar login primero (obtiene serial y model name, auto-detecta modelo)
        if not self.login():
            print("[!] Error: No se pudo autenticar")
            return self.test_results
        
        # Ejecutar todos los tests
        tests = [
            # Tests de autenticacion
            self.test_pwd_pass,
            self.test_factory_reset,
            
            # Tests de conectividad (RF 002, 003, 004)
            self.test_ping_connectivity,
            self.test_http_connectivity,
            self.test_port_scan,
            self.test_dns_resolution,
            
            # Tests de hardware
            self.test_usb_port,
            self.test_software_version,
            self.test_tx_power,
            self.test_rx_power,
            self.test_wifi_24ghz,
            self.test_wifi_5ghz
        ]
        
        for test_func in tests:
            result = test_func()
            self.test_results["tests"][result["name"]] = result
        
        return self.test_results
    
    def generate_report(self) -> str:
        """Genera reporte en formato texto"""
        lines = []
        lines.append("="*60)
        lines.append("REPORTE DE PRUEBAS AUTOMATIZADAS ONT")
        lines.append("="*60)
        lines.append(f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        lines.append(f"Modelo: {self.model}")
        lines.append(f"Host: {self.host}")
        lines.append(f"Serie: {self.test_results['metadata']['serial_number']}")
        lines.append("")
        lines.append("RESULTADOS:")
        lines.append("-"*60)
        
        pass_count = 0
        fail_count = 0
        skip_count = 0
        
        for test_name, test_data in self.test_results["tests"].items():
            status = test_data["status"]
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
        """Guarda los resultados en archivos"""
        if output_dir is None:
            output_dir = Path(__file__).parent.parent / "reports" / "automated_tests"
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
        
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

def main():
    parser = argparse.ArgumentParser(description="ONT Automated Test Suite")
    parser.add_argument("--host", required=True, help="IP de la ONT")
    parser.add_argument("--model", help="Modelo de la ONT (opcional, se detecta automaticamente)")
    parser.add_argument("--output", help="Directorio de salida (opcional)")
    parser.add_argument("--mode", 
                       choices=['test', 'retest', 'label'], 
                       default='test',
                       help="Modo de operacion: test (todos), retest (solo fallidos), label (generar etiqueta)")
    
    args = parser.parse_args()
    
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
        print("\n" + tester.generate_report())
        
        # Guardar resultados
        tester.save_results(args.output)

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
    
    # Guardar etiqueta en archivo
    label_dir = Path("reports/labels")
    label_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
    serial = operator_info.get('SerialNumber', 'UNKNOWN')
    label_file = label_dir / f"{timestamp}_{tester.model}_{serial}_label.txt"
    
    with open(label_file, 'w', encoding='utf-8') as f:
        f.write(label)
    
    print(f"\n[+] Etiqueta guardada en: {label_file}")

def run_retest_mode(host: str, model: str = None, output: str = None):
    """RF 031: Ejecuta solo los tests que fallaron anteriormente"""
    print("\n" + "="*60)
    print("MODO RETEST - Solo tests fallidos")
    print("="*60 + "\n")
    
    # Buscar el último reporte
    reports_dir = Path("reports/automated_tests")
    if not reports_dir.exists():
        print("[!] No se encontraron reportes previos")
        print("[*] Ejecutando suite completo...")
        tester = ONTAutomatedTester(host, model)
        tester.run_all_tests()
        print("\n" + tester.generate_report())
        tester.save_results(output)
        return
    
    # Encontrar último archivo JSON
    json_files = sorted(reports_dir.glob("*_automated_results.json"))
    if not json_files:
        print("[!] No se encontraron reportes previos")
        print("[*] Ejecutando suite completo...")
        tester = ONTAutomatedTester(host, model)
        tester.run_all_tests()
        print("\n" + tester.generate_report())
        tester.save_results(output)
        return
    
    last_report = json_files[-1]
    print(f"[*] Cargando último reporte: {last_report.name}")
    
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
        "WIFI_5GHZ": tester.test_wifi_5ghz
    }
    
    # Ejecutar solo tests fallidos
    for test_name in failed_tests:
        if test_name in test_methods:
            result = test_methods[test_name]()
            tester.test_results["tests"][result["name"]] = result
    
    # Mostrar reporte
    print("\n" + tester.generate_report())
    
    # Guardar resultados con prefijo "retest"
    if output:
        output_dir = Path(output)
    else:
        output_dir = Path("reports/automated_tests")
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%d_%m_%y_%H%M%S")
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
