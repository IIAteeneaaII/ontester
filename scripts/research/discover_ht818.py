#!/usr/bin/env python3
"""
Script de descubrimiento para GRANDSTREAM HT818
ATA (Adaptador Telefónico Analógico) empresarial
"""

import requests
import json
import argparse
from datetime import datetime
from typing import Dict, Any, List
from urllib.parse import urljoin
import re

requests.packages.urllib3.disable_warnings()


class GrandstreamHT818Discovery:
    """Descubridor de información del Grandstream HT818"""
    
    def __init__(self, host: str, username: str = 'admin', password: str = 'admin'):
        self.host = host
        self.username = username
        self.password = password
        self.base_url = f"http://{host}"
        self.session = requests.Session()
        self.device_info = {}
        
    def check_accessibility(self) -> bool:
        """Verifica si el dispositivo es accesible"""
        print("\n" + "="*80)
        print("VERIFICACIÓN DE ACCESIBILIDAD")
        print("="*80)
        print(f"Host: {self.host}")
        
        try:
            response = requests.get(
                self.base_url,
                timeout=5,
                verify=False,
                allow_redirects=True
            )
            
            print(f"[+] Dispositivo accesible")
            print(f"    Status: {response.status_code}")
            print(f"    Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            
            # Detectar servidor
            server = response.headers.get('Server', 'Unknown')
            print(f"    Server: {server}")
            
            # Buscar información del dispositivo en la respuesta
            if 'grandstream' in response.text.lower() or 'ht818' in response.text.lower():
                print(f"[+] Confirmado: Dispositivo Grandstream detectado")
            
            return True
            
        except requests.exceptions.Timeout:
            print(f"[-] Timeout al conectar con {self.host}")
            return False
        except requests.exceptions.ConnectionError:
            print(f"[-] No se pudo conectar a {self.host}")
            return False
        except Exception as e:
            print(f"[-] Error: {e}")
            return False
    
    def discover_endpoints(self) -> Dict[str, Any]:
        """Descubre endpoints comunes del Grandstream HT818"""
        print("\n" + "="*80)
        print("DESCUBRIMIENTO DE ENDPOINTS")
        print("="*80)
        
        # Endpoints comunes de dispositivos Grandstream
        endpoints = [
            # Páginas web principales
            "/",
            "/index.html",
            "/login.html",
            "/main.html",
            "/status.html",
            "/info.html",
            
            # CGI/Scripts
            "/cgi-bin/login",
            "/cgi-bin/dologin",
            "/cgi-bin/api.values.get",
            "/cgi-bin/api.values.set",
            "/cgi-bin/api-sys_operation",
            "/cgi-bin/api-get_profile_name",
            "/cgi-bin/api-get_line_status",
            
            # APIs
            "/api",
            "/api/status",
            "/api/info",
            "/api/config",
            "/goform/login",
            "/manager",
            
            # Archivos de configuración
            "/cfg",
            "/config.xml",
            "/config",
            
            # AJAX/JSON endpoints
            "/ajax",
            "/json",
            "/data.json",
            
            # Directorios comunes
            "/images",
            "/js",
            "/css",
        ]
        
        results = {}
        accessible = []
        
        for i, endpoint in enumerate(endpoints, 1):
            url = urljoin(self.base_url, endpoint)
            
            try:
                response = self.session.get(
                    url,
                    auth=(self.username, self.password),
                    timeout=3,
                    verify=False,
                    allow_redirects=False
                )
                
                status = response.status_code
                
                if status == 200:
                    print(f"[{i}/{len(endpoints)}] ✓ {endpoint} - {status}")
                    accessible.append(endpoint)
                    
                    results[endpoint] = {
                        "accessible": True,
                        "status": status,
                        "content_type": response.headers.get('Content-Type', ''),
                        "size": len(response.content),
                        "has_json": self._is_json(response),
                        "has_html": 'text/html' in response.headers.get('Content-Type', '')
                    }
                    
                elif status in [301, 302, 303, 307, 308]:
                    location = response.headers.get('Location', '')
                    print(f"[{i}/{len(endpoints)}] → {endpoint} - {status} (redirect to {location})")
                    results[endpoint] = {
                        "accessible": True,
                        "status": status,
                        "redirect": location
                    }
                    
                elif status == 401:
                    print(f"[{i}/{len(endpoints)}] 🔒 {endpoint} - {status} (auth required)")
                    results[endpoint] = {
                        "accessible": False,
                        "status": status,
                        "auth_required": True
                    }
                    
                else:
                    results[endpoint] = {
                        "accessible": False,
                        "status": status
                    }
                    
            except Exception as e:
                results[endpoint] = {
                    "accessible": False,
                    "error": str(e)
                }
        
        print(f"\n[+] Endpoints accesibles: {len(accessible)}/{len(endpoints)}")
        
        return results
    
    def _is_json(self, response) -> bool:
        """Verifica si la respuesta es JSON"""
        try:
            response.json()
            return True
        except:
            return False
    
    def extract_device_info(self) -> Dict[str, Any]:
        """Extrae información básica del dispositivo"""
        print("\n" + "="*80)
        print("EXTRACCIÓN DE INFORMACIÓN DEL DISPOSITIVO")
        print("="*80)
        
        info = {
            "model": "HT818",
            "manufacturer": "Grandstream"
        }
        
        # Intentar obtener información de la página principal
        try:
            response = self.session.get(
                self.base_url,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            html = response.text
            
            # Buscar patrones comunes
            patterns = {
                'model': r'(HT\d{3}[A-Z]?)',
                'firmware': r'(?:Firmware|Version|Ver\.?)\s*:?\s*([0-9]+\.[0-9]+\.[0-9]+\.?[0-9]*)',
                'mac_address': r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
                'ip_address': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                'serial': r'(?:Serial|S/N)\s*:?\s*([A-Z0-9]{10,})',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    info[key] = match.group(1) if match.groups() else match.group(0)
                    print(f"[+] {key.replace('_', ' ').title()}: {info[key]}")
            
        except Exception as e:
            print(f"[-] Error extrayendo información: {e}")
        
        return info
    
    def test_api_endpoints(self) -> Dict[str, Any]:
        """Prueba endpoints de API específicos de Grandstream"""
        print("\n" + "="*80)
        print("PRUEBA DE ENDPOINTS API")
        print("="*80)
        
        api_tests = [
            # API de valores
            {
                "name": "Get Values",
                "url": "/cgi-bin/api.values.get",
                "method": "GET",
                "params": {}
            },
            {
                "name": "System Operation",
                "url": "/cgi-bin/api-sys_operation",
                "method": "GET",
                "params": {}
            },
            {
                "name": "Line Status",
                "url": "/cgi-bin/api-get_line_status",
                "method": "GET",
                "params": {}
            },
            {
                "name": "Profile Name",
                "url": "/cgi-bin/api-get_profile_name",
                "method": "GET",
                "params": {}
            },
        ]
        
        results = {}
        
        for test in api_tests:
            print(f"\n[*] Probando: {test['name']}")
            url = urljoin(self.base_url, test['url'])
            
            try:
                if test['method'] == 'GET':
                    response = self.session.get(
                        url,
                        params=test['params'],
                        auth=(self.username, self.password),
                        timeout=5,
                        verify=False
                    )
                else:
                    response = self.session.post(
                        url,
                        data=test['params'],
                        auth=(self.username, self.password),
                        timeout=5,
                        verify=False
                    )
                
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    # Intentar parsear respuesta
                    content_type = response.headers.get('Content-Type', '')
                    
                    if 'json' in content_type:
                        try:
                            data = response.json()
                            print(f"    ✓ JSON response")
                            print(f"    Keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}")
                            results[test['name']] = {
                                "success": True,
                                "data": data
                            }
                        except:
                            pass
                    else:
                        text = response.text[:200]
                        print(f"    Response (first 200 chars): {text}")
                        results[test['name']] = {
                            "success": True,
                            "data": response.text
                        }
                else:
                    results[test['name']] = {
                        "success": False,
                        "status": response.status_code
                    }
                    
            except Exception as e:
                print(f"    Error: {e}")
                results[test['name']] = {
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    def scan_ports(self) -> Dict[int, bool]:
        """Escanea puertos comunes de dispositivos VoIP"""
        print("\n" + "="*80)
        print("ESCANEO DE PUERTOS COMUNES")
        print("="*80)
        
        # Puertos comunes en dispositivos VoIP/ATA
        ports = {
            80: "HTTP",
            443: "HTTPS",
            8080: "HTTP Alternate",
            8443: "HTTPS Alternate",
            5060: "SIP",
            5061: "SIP TLS",
            69: "TFTP",
            161: "SNMP",
            22: "SSH",
            23: "Telnet",
        }
        
        results = {}
        
        for port, service in ports.items():
            try:
                import socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.host, port))
                sock.close()
                
                if result == 0:
                    print(f"[+] Port {port} ({service}): OPEN")
                    results[port] = True
                else:
                    results[port] = False
                    
            except Exception as e:
                results[port] = False
        
        open_ports = [p for p, open in results.items() if open]
        print(f"\n[+] Puertos abiertos: {len(open_ports)}")
        
        return results
    
    def run_full_discovery(self) -> Dict[str, Any]:
        """Ejecuta descubrimiento completo"""
        print("\n" + "="*80)
        print("DESCUBRIMIENTO COMPLETO - GRANDSTREAM HT818")
        print("="*80)
        print(f"Target: {self.host}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 1. Verificar accesibilidad
        if not self.check_accessibility():
            print("\n[-] Dispositivo no accesible. Abortando.")
            return None
        
        # 2. Escanear puertos
        ports = self.scan_ports()
        
        # 3. Descubrir endpoints
        endpoints = self.discover_endpoints()
        
        # 4. Extraer información del dispositivo
        device_info = self.extract_device_info()
        
        # 5. Probar APIs
        api_results = self.test_api_endpoints()
        
        # Resumen
        print("\n" + "="*80)
        print("RESUMEN DE DESCUBRIMIENTO")
        print("="*80)
        
        accessible_endpoints = [e for e, r in endpoints.items() if r.get('accessible')]
        working_apis = [a for a, r in api_results.items() if r.get('success')]
        open_ports = [p for p, open in ports.items() if open]
        
        print(f"\n✓ Endpoints accesibles: {len(accessible_endpoints)}")
        print(f"✓ APIs funcionales: {len(working_apis)}")
        print(f"✓ Puertos abiertos: {len(open_ports)}")
        
        if device_info:
            print(f"\nInformación del dispositivo:")
            for key, value in device_info.items():
                print(f"  - {key}: {value}")
        
        # Guardar resultados
        output = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "device_info": device_info,
            "ports": ports,
            "endpoints": endpoints,
            "api_results": api_results,
            "summary": {
                "accessible_endpoints": accessible_endpoints,
                "working_apis": working_apis,
                "open_ports": open_ports
            }
        }
        
        filename = f"ht818_discovery_{datetime.now().strftime('%d_%m_%y_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Resultados guardados en: {filename}")
        
        # Generar reporte de texto
        self._generate_report(output, filename.replace('.json', '.txt'))
        
        return output
    
    def _generate_report(self, data: Dict[str, Any], filename: str):
        """Genera reporte en texto"""
        report = []
        report.append("="*80)
        report.append("REPORTE DE DESCUBRIMIENTO - GRANDSTREAM HT818")
        report.append("="*80)
        report.append(f"Host: {self.host}")
        report.append(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Información del dispositivo
        if data.get('device_info'):
            report.append("INFORMACIÓN DEL DISPOSITIVO:")
            report.append("-" * 80)
            for key, value in data['device_info'].items():
                report.append(f"  {key}: {value}")
            report.append("")
        
        # Puertos
        report.append("PUERTOS ABIERTOS:")
        report.append("-" * 80)
        for port, is_open in data.get('ports', {}).items():
            if is_open:
                report.append(f"  Port {port}: OPEN")
        report.append("")
        
        # Endpoints accesibles
        report.append("ENDPOINTS ACCESIBLES:")
        report.append("-" * 80)
        for endpoint in data['summary']['accessible_endpoints']:
            report.append(f"  {endpoint}")
        report.append("")
        
        # APIs funcionales
        if data['summary']['working_apis']:
            report.append("APIs FUNCIONALES:")
            report.append("-" * 80)
            for api in data['summary']['working_apis']:
                report.append(f"  {api}")
            report.append("")
        
        report.append("="*80)
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        print(f"[+] Reporte guardado en: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description='Descubrimiento de información del Grandstream HT818'
    )
    parser.add_argument('--host', type=str, required=True,
                        help='Dirección IP del HT818')
    parser.add_argument('--username', type=str, default='admin',
                        help='Usuario (default: admin)')
    parser.add_argument('--password', type=str, default='admin',
                        help='Contraseña (default: admin)')
    
    args = parser.parse_args()
    
    discoverer = GrandstreamHT818Discovery(args.host, args.username, args.password)
    discoverer.run_full_discovery()


if __name__ == "__main__":
    main()
