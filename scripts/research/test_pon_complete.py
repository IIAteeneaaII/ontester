#!/usr/bin/env python3
"""
Script completo para obtener información PON del ONT HG6145F
Incluye login web completo y extracción detallada de datos ópticos
"""

import requests
import json
import hashlib
import re
import argparse
from datetime import datetime
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()


class ONTPONTester:
    """Tester completo para información PON/Óptica del ONT"""
    
    def __init__(self, host: str, username: str = 'root', password: str = 'admin'):
        self.host = host
        self.username = username
        self.password = password
        self.base_url = f"http://{host}"
        self.session = requests.Session()
        self.sessionid = None
        self.logged_in = False
        
    def _get_password_hash(self, password: str) -> str:
        """Genera el hash MD5 de la contraseña"""
        return hashlib.md5(password.encode()).hexdigest()
    
    def login(self) -> bool:
        """Realiza login completo en la interfaz web del ONT"""
        print("\n" + "="*80)
        print("AUTENTICACIÓN EN ONT")
        print("="*80)
        print(f"Host: {self.host}")
        print(f"Usuario: {self.username}")
        
        login_url = f"{self.base_url}/cgi-bin/login"
        
        # Preparar datos de login
        password_hash = self._get_password_hash(self.password)
        
        login_data = {
            'user': self.username,
            'password': password_hash,
            'login': 'Login'
        }
        
        try:
            # Método 1: POST a /cgi-bin/login
            print("\n[*] Intentando login POST...")
            response = self.session.post(
                login_url,
                data=login_data,
                timeout=10,
                verify=False,
                allow_redirects=True
            )
            
            print(f"    Status: {response.status_code}")
            print(f"    Cookies: {dict(self.session.cookies)}")
            
            # Verificar si el login fue exitoso
            if response.status_code == 200:
                # Buscar sessionid en cookies
                cookies = dict(self.session.cookies)
                if 'sessionid' in cookies:
                    self.sessionid = cookies['sessionid']
                    print(f"[+] SessionID de cookie: {self.sessionid}")
                    self.logged_in = True
                    return True
                
                # Buscar en el contenido
                if 'sessionid' in response.text.lower():
                    print("[+] Login exitoso (detectado en respuesta)")
                    self.logged_in = True
                    return True
            
            # Método 2: Usar HTTP Basic Auth y obtener sessionid por AJAX
            print("\n[*] Intentando autenticación alternativa...")
            ajax_url = f"{self.base_url}/cgi-bin/ajax"
            
            params = {
                'ajaxmethod': 'get_refresh_sessionid',
                '_': str(int(datetime.now().timestamp() * 1000))
            }
            
            response = self.session.get(
                ajax_url,
                params=params,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                self.sessionid = data.get('sessionid')
                print(f"[+] SessionID via AJAX: {self.sessionid}")
                
                # Configurar auth para todas las peticiones
                self.session.auth = (self.username, self.password)
                self.logged_in = True
                return True
            
            print("[-] No se pudo autenticar")
            return False
            
        except Exception as e:
            print(f"[-] Error en login: {e}")
            return False
    
    def _make_ajax_request(self, method: str, params: dict = None) -> Dict[str, Any]:
        """Realiza una petición AJAX con sesión autenticada"""
        ajax_url = f"{self.base_url}/cgi-bin/ajax"
        
        request_params = params or {}
        request_params['ajaxmethod'] = method
        request_params['_'] = str(int(datetime.now().timestamp() * 1000))
        
        if self.sessionid:
            request_params['sessionid'] = self.sessionid
        
        try:
            response = self.session.get(
                ajax_url,
                params=request_params,
                timeout=10,
                verify=False
            )
            
            result = {
                "status": response.status_code,
                "success": response.status_code == 200
            }
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    result["data"] = data
                    
                    # Actualizar sessionid si viene en la respuesta
                    if 'sessionid' in data and data['sessionid']:
                        self.sessionid = data['sessionid']
                    
                except:
                    result["data"] = response.text
                    result["raw"] = True
            else:
                result["error"] = response.text[:200]
            
            return result
            
        except Exception as e:
            return {
                "status": 0,
                "success": False,
                "error": str(e)
            }
    
    def get_pon_info(self) -> Optional[Dict[str, Any]]:
        """Obtiene información PON completa"""
        print("\n" + "="*80)
        print("INFORMACIÓN PON/ÓPTICA")
        print("="*80)
        
        result = self._make_ajax_request('get_pon_info')
        
        if result['success']:
            data = result.get('data', {})
            
            if data.get('session_valid') == 0:
                print("[-] Sesión no válida para get_pon_info")
                return None
            
            print("[+] Información PON obtenida exitosamente")
            return data
        else:
            print(f"[-] Error al obtener información PON: {result.get('error', 'Unknown')}")
            return None
    
    def scrape_pon_page(self) -> Optional[Dict[str, Any]]:
        """Scrape directo de la página PON del ONT"""
        print("\n[*] Intentando scraping de página PON...")
        
        pon_urls = [
            f"{self.base_url}/html/status/pon_info.html",
            f"{self.base_url}/html/status/optical_info.html",
            f"{self.base_url}/html/status/status.html",
            f"{self.base_url}/status.html",
            f"{self.base_url}/cgi-bin/status"
        ]
        
        for url in pon_urls:
            try:
                print(f"\n[*] Probando: {url}")
                response = self.session.get(url, timeout=5, verify=False)
                
                if response.status_code == 200:
                    print(f"    [OK] Página accesible")
                    
                    # Buscar información PON en el HTML
                    html = response.text
                    
                    # Patrones comunes para información PON
                    patterns = {
                        'tx_power': [
                            r'TX[_ ]?Power[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?',
                            r'Transmit[_ ]?Power[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?',
                            r'Potencia[_ ]?TX[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?'
                        ],
                        'rx_power': [
                            r'RX[_ ]?Power[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?',
                            r'Receive[_ ]?Power[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?',
                            r'Potencia[_ ]?RX[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?'
                        ],
                        'olt_rx_power': [
                            r'OLT[_ ]?RX[_ ]?Power[:\s]+([+-]?\d+\.?\d*)\s*(dBm|mW)?'
                        ],
                        'temperature': [
                            r'Temperature[:\s]+(\d+\.?\d*)\s*(°C|C)?',
                            r'Temperatura[:\s]+(\d+\.?\d*)\s*(°C|C)?'
                        ],
                        'voltage': [
                            r'Voltage[:\s]+(\d+\.?\d*)\s*V',
                            r'Voltaje[:\s]+(\d+\.?\d*)\s*V'
                        ],
                        'bias_current': [
                            r'Bias[_ ]?Current[:\s]+(\d+\.?\d*)\s*(mA)?',
                            r'Corriente[:\s]+(\d+\.?\d*)\s*(mA)?'
                        ]
                    }
                    
                    pon_data = {}
                    
                    for key, pattern_list in patterns.items():
                        for pattern in pattern_list:
                            match = re.search(pattern, html, re.IGNORECASE)
                            if match:
                                pon_data[key] = match.group(1)
                                if len(match.groups()) > 1 and match.group(2):
                                    pon_data[f"{key}_unit"] = match.group(2)
                                break
                    
                    if pon_data:
                        return pon_data
                    
            except Exception as e:
                print(f"    [-] Error: {e}")
                continue
        
        return None
    
    def test_all_pon_methods(self) -> Dict[str, Any]:
        """Prueba todos los métodos relacionados con PON"""
        print("\n" + "="*80)
        print("DESCUBRIMIENTO DE MÉTODOS PON")
        print("="*80)
        
        pon_methods = [
            "get_pon_info",
            "get_pon_status",
            "get_optical_info",
            "get_optical_status",
            "get_optical_power",
            "get_pon_link_info",
            "get_poninfo",
            "get_ont_info",
            "get_ont_status",
            "get_fiber_info",
            "get_gpon_info",
            "get_epon_info",
            "get_olt_info",
            "get_transceiver_info",
            "get_sfp_info",
            "get_ddm_info",  # Digital Diagnostic Monitoring
        ]
        
        results = {}
        
        for i, method in enumerate(pon_methods, 1):
            print(f"\n[{i}/{len(pon_methods)}] Probando: {method}")
            
            result = self._make_ajax_request(method)
            
            if result['success']:
                data = result.get('data', {})
                session_valid = data.get('session_valid', 'N/A')
                has_data = len(data.keys()) > 2
                
                print(f"    [OK] Status: {result['status']}")
                print(f"         session_valid: {session_valid}")
                print(f"         Campos: {list(data.keys())}")
                
                if has_data:
                    print("         ✓ TIENE DATOS ADICIONALES")
                    for key, value in data.items():
                        if key not in ['sessionid', 'session_valid']:
                            print(f"           - {key}: {value}")
                
                results[method] = {
                    "accessible": True,
                    "has_data": has_data,
                    "data": data
                }
            else:
                print(f"    [--] Status: {result.get('status', 'Error')}")
                results[method] = {
                    "accessible": False,
                    "status": result.get('status')
                }
        
        return results
    
    def parse_optical_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parsea y convierte valores ópticos a unidades estándar"""
        parsed = {}
        
        # Campos comunes de potencia óptica
        power_fields = {
            'tx_power': 'TX Power',
            'rx_power': 'RX Power',
            'olt_rx_power': 'OLT RX Power',
            'TxPower': 'TX Power',
            'RxPower': 'RX Power',
            'TransmitPower': 'TX Power',
            'ReceivePower': 'RX Power'
        }
        
        for field, label in power_fields.items():
            if field in data:
                value = data[field]
                parsed[label] = {
                    'raw': value,
                    'value': self._parse_power_value(value),
                    'unit': 'dBm'
                }
        
        # Temperatura
        temp_fields = ['temperature', 'Temperature', 'temp']
        for field in temp_fields:
            if field in data:
                value = data[field]
                parsed['Temperature'] = {
                    'raw': value,
                    'value': self._parse_numeric_value(value),
                    'unit': '°C'
                }
                break
        
        # Voltaje
        volt_fields = ['voltage', 'Voltage', 'volt']
        for field in volt_fields:
            if field in data:
                value = data[field]
                parsed['Voltage'] = {
                    'raw': value,
                    'value': self._parse_numeric_value(value),
                    'unit': 'V'
                }
                break
        
        # Corriente
        current_fields = ['bias_current', 'BiasCurrent', 'current']
        for field in current_fields:
            if field in data:
                value = data[field]
                parsed['Bias Current'] = {
                    'raw': value,
                    'value': self._parse_numeric_value(value),
                    'unit': 'mA'
                }
                break
        
        return parsed
    
    def _parse_power_value(self, value: str) -> Optional[float]:
        """Parsea valor de potencia óptica"""
        try:
            # Extraer número
            match = re.search(r'([+-]?\d+\.?\d*)', str(value))
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def _parse_numeric_value(self, value: str) -> Optional[float]:
        """Parsea valor numérico genérico"""
        try:
            match = re.search(r'(\d+\.?\d*)', str(value))
            if match:
                return float(match.group(1))
        except:
            pass
        return None
    
    def format_pon_report(self, pon_data: Dict[str, Any]) -> str:
        """Genera un reporte formateado de la información PON"""
        report = []
        report.append("\n" + "="*80)
        report.append("REPORTE DE INFORMACIÓN PON/ÓPTICA")
        report.append("="*80)
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Host: {self.host}")
        report.append("")
        
        if not pon_data:
            report.append("[-] No se pudo obtener información PON")
            return "\n".join(report)
        
        # Parsear valores ópticos
        parsed = self.parse_optical_values(pon_data)
        
        if parsed:
            report.append("PARÁMETROS ÓPTICOS:")
            report.append("-" * 80)
            
            # TX Power
            if 'TX Power' in parsed:
                tx = parsed['TX Power']
                report.append(f"  TX Power (Potencia de Transmisión):")
                report.append(f"    Valor: {tx['value']} {tx['unit']}")
                report.append(f"    Raw: {tx['raw']}")
            
            # RX Power
            if 'RX Power' in parsed:
                rx = parsed['RX Power']
                report.append(f"\n  RX Power (Potencia de Recepción):")
                report.append(f"    Valor: {rx['value']} {rx['unit']}")
                report.append(f"    Raw: {rx['raw']}")
            
            # OLT RX Power
            if 'OLT RX Power' in parsed:
                olt_rx = parsed['OLT RX Power']
                report.append(f"\n  OLT RX Power (Potencia recibida por OLT):")
                report.append(f"    Valor: {olt_rx['value']} {olt_rx['unit']}")
                report.append(f"    Raw: {olt_rx['raw']}")
            
            # Temperatura
            if 'Temperature' in parsed:
                temp = parsed['Temperature']
                report.append(f"\n  Temperatura del transceptor:")
                report.append(f"    Valor: {temp['value']} {temp['unit']}")
                report.append(f"    Raw: {temp['raw']}")
            
            # Voltaje
            if 'Voltage' in parsed:
                volt = parsed['Voltage']
                report.append(f"\n  Voltaje:")
                report.append(f"    Valor: {volt['value']} {volt['unit']}")
                report.append(f"    Raw: {volt['raw']}")
            
            # Corriente
            if 'Bias Current' in parsed:
                current = parsed['Bias Current']
                report.append(f"\n  Corriente de polarización:")
                report.append(f"    Valor: {current['value']} {current['unit']}")
                report.append(f"    Raw: {current['raw']}")
        
        # Datos adicionales
        report.append("\n" + "-" * 80)
        report.append("DATOS RAW COMPLETOS:")
        report.append("-" * 80)
        for key, value in pon_data.items():
            report.append(f"  {key}: {value}")
        
        report.append("="*80)
        
        return "\n".join(report)
    
    def run_full_analysis(self) -> Dict[str, Any]:
        """Ejecuta análisis completo de información PON"""
        print("\n" + "="*80)
        print("ANÁLISIS COMPLETO DE INFORMACIÓN PON")
        print("="*80)
        print(f"Host: {self.host}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Login
        if not self.login():
            print("\n[-] No se pudo autenticar. Abortando.")
            return None
        
        # 2. Obtener información PON via AJAX
        pon_data = self.get_pon_info()
        
        # 3. Probar todos los métodos PON
        all_methods = self.test_all_pon_methods()
        
        # 4. Intentar scraping si AJAX no funciona
        scraped_data = None
        if not pon_data or pon_data.get('session_valid') == 0:
            print("\n[*] Intentando obtener datos via scraping...")
            scraped_data = self.scrape_pon_page()
        
        # 5. Consolidar datos
        final_data = pon_data or scraped_data or {}
        
        # 6. Generar reporte
        report_text = self.format_pon_report(final_data)
        print(report_text)
        
        # 7. Guardar resultados
        output = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "authentication": {
                "logged_in": self.logged_in,
                "sessionid": self.sessionid
            },
            "pon_info_ajax": pon_data,
            "pon_info_scraped": scraped_data,
            "all_methods_tested": all_methods,
            "final_data": final_data,
            "report": report_text
        }
        
        filename = f"pon_complete_analysis_{datetime.now().strftime('%d_%m_%y_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Resultados guardados en: {filename}")
        
        # También guardar reporte en txt
        txt_filename = filename.replace('.json', '.txt')
        with open(txt_filename, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        print(f"[+] Reporte guardado en: {txt_filename}")
        
        return output


def main():
    parser = argparse.ArgumentParser(
        description='Obtiene información PON/Óptica completa del ONT HG6145F'
    )
    parser.add_argument('--host', type=str, default='192.168.100.1',
                        help='Dirección IP del ONT (default: 192.168.100.1)')
    parser.add_argument('--username', type=str, default='root',
                        help='Usuario para autenticación (default: root)')
    parser.add_argument('--password', type=str, default='admin',
                        help='Contraseña para autenticación (default: admin)')
    
    args = parser.parse_args()
    
    tester = ONTPONTester(args.host, args.username, args.password)
    tester.run_full_analysis()


if __name__ == "__main__":
    main()
