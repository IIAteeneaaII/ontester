#!/usr/bin/env python3
"""
Script exhaustivo para extraer información del Grandstream HT818
Prueba TODOS los métodos conocidos de extracción de información
"""

import requests
import json
import re
import base64
from datetime import datetime
from typing import Dict, Any
from urllib.parse import urljoin
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()


class GrandstreamInfoExtractor:
    """Extractor exhaustivo de información del Grandstream"""
    
    def __init__(self, host: str, username: str = 'admin', password: str = 'admin'):
        self.host = host
        self.username = username
        self.password = password
        self.base_url = f"http://{host}"
        self.session = requests.Session()
        self.device_info = {}
        
    def test_all_methods(self):
        """Prueba TODOS los métodos posibles de extracción"""
        print("\n" + "="*80)
        print("EXTRACCIÓN EXHAUSTIVA - GRANDSTREAM HT818")
        print("="*80)
        print(f"Host: {self.host}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        methods = [
            ("Método 1", self.method_1_basic_auth_html),
            ("Método 2", self.method_2_status_pages),
            ("Método 3", self.method_3_cgi_endpoints),
            ("Método 4", self.method_4_ajax_style),
            ("Método 5", self.method_5_xml_config),
            ("Método 6", self.method_6_json_api),
            ("Método 7", self.method_7_snmp_info),
            ("Método 8", self.method_8_upnp_discovery),
            ("Método 9", self.method_9_sip_headers),
            ("Método 10", self.method_10_telnet_banner),
            ("Método 11", self.method_11_header_analysis),
            ("Método 12", self.method_12_javascript_parsing),
        ]
        
        results = {}
        
        for method_name, method_func in methods:
            print(f"\n{'='*80}")
            print(f"{method_name}: {method_func.__doc__}")
            print("="*80)
            
            try:
                result = method_func()
                results[method_name] = result
                
                if result and result.get('data'):
                    print(f"✓ DATOS ENCONTRADOS:")
                    for key, value in result['data'].items():
                        print(f"  - {key}: {value}")
                else:
                    print("✗ Sin datos")
                    
            except Exception as e:
                print(f"✗ Error: {e}")
                results[method_name] = {"error": str(e)}
        
        return results
    
    def method_1_basic_auth_html(self):
        """Parseo HTML con autenticación básica"""
        try:
            response = self.session.get(
                self.base_url,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            if response.status_code != 200:
                return {"success": False, "status": response.status_code}
            
            html = response.text
            soup = BeautifulSoup(html, 'html.parser')
            
            data = {}
            
            # Buscar en tablas
            for table in soup.find_all('table'):
                for row in table.find_all('tr'):
                    cells = row.find_all(['td', 'th'])
                    if len(cells) >= 2:
                        key = cells[0].get_text(strip=True)
                        value = cells[1].get_text(strip=True)
                        if key and value:
                            data[key] = value
            
            # Buscar en texto con patrones
            patterns = {
                'MAC Address': r'MAC[:\s]+([0-9A-Fa-f:]{17})',
                'Model': r'Model[:\s]+([A-Z0-9\-]+)',
                'Firmware': r'(?:Firmware|Version)[:\s]+([0-9\.]+)',
                'Serial': r'(?:Serial|S/N)[:\s]+([A-Z0-9]+)',
                'Product': r'Product[:\s]+(.+?)(?:<|$)',
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, html, re.IGNORECASE)
                if match:
                    data[key] = match.group(1).strip()
            
            # Buscar meta tags
            for meta in soup.find_all('meta'):
                if meta.get('name') and meta.get('content'):
                    data[f"meta_{meta['name']}"] = meta['content']
            
            return {"success": True, "data": data, "method": "HTML Parsing"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def method_2_status_pages(self):
        """Páginas de status comunes"""
        status_urls = [
            '/status.html',
            '/index.html',
            '/main.html',
            '/system_status.html',
            '/device_info.html',
            '/sysinfo.html',
        ]
        
        all_data = {}
        
        for url in status_urls:
            try:
                response = self.session.get(
                    urljoin(self.base_url, url),
                    auth=(self.username, self.password),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200:
                    print(f"  → {url} accesible")
                    
                    # Extraer info
                    patterns = {
                        'mac': r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})',
                        'model': r'(?:Model|Product)[:\s]*([A-Z]{2}\d{3,4}[A-Z]?)',
                        'firmware': r'(?:Firmware|Software Version)[:\s]*([0-9\.]+)',
                        'serial': r'(?:Serial Number|S/N)[:\s]*([A-Z0-9]{10,})',
                    }
                    
                    for key, pattern in patterns.items():
                        match = re.search(pattern, response.text, re.IGNORECASE)
                        if match:
                            all_data[f"{url}_{key}"] = match.group(0)
                            
            except:
                pass
        
        return {"success": bool(all_data), "data": all_data, "method": "Status Pages"}
    
    def method_3_cgi_endpoints(self):
        """Endpoints CGI específicos de Grandstream"""
        cgi_endpoints = [
            '/cgi-bin/api.values.get',
            '/cgi-bin/api-get_device_info',
            '/cgi-bin/api-get_mac',
            '/cgi-bin/api-get_model',
            '/cgi-bin/api-sys_info',
            '/cgi-bin/status',
            '/cgi-bin/device_info',
            '/goform/status',
            '/goform/SystemInfo',
        ]
        
        data = {}
        
        for endpoint in cgi_endpoints:
            try:
                # GET
                response = self.session.get(
                    urljoin(self.base_url, endpoint),
                    auth=(self.username, self.password),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200 and len(response.text) > 0:
                    print(f"  ✓ {endpoint} responde")
                    
                    # Intentar parsear JSON
                    try:
                        json_data = response.json()
                        data[endpoint] = json_data
                    except:
                        # Si no es JSON, buscar patrones
                        text = response.text[:500]
                        if 'MAC' in text or 'model' in text.lower():
                            data[endpoint] = text
                
                # También probar POST
                response = self.session.post(
                    urljoin(self.base_url, endpoint),
                    auth=(self.username, self.password),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200 and len(response.text) > 0:
                    print(f"  ✓ {endpoint} (POST) responde")
                    try:
                        json_data = response.json()
                        data[f"{endpoint}_POST"] = json_data
                    except:
                        pass
                        
            except:
                pass
        
        return {"success": bool(data), "data": data, "method": "CGI Endpoints"}
    
    def method_4_ajax_style(self):
        """Estilo AJAX pero para Grandstream"""
        ajax_methods = [
            'getDeviceInfo',
            'getSystemInfo',
            'getMacAddress',
            'getModelName',
            'getVersion',
            'getStatus',
            'device_info',
            'system_info',
        ]
        
        endpoints = [
            '/cgi-bin/api',
            '/cgi-bin/ajax',
            '/api',
            '/ajax',
        ]
        
        data = {}
        
        for endpoint in endpoints:
            for method in ajax_methods:
                try:
                    # Probar con diferentes formatos
                    params_formats = [
                        {'action': method},
                        {'method': method},
                        {'cmd': method},
                        {'request': method},
                    ]
                    
                    for params in params_formats:
                        response = self.session.get(
                            urljoin(self.base_url, endpoint),
                            params=params,
                            auth=(self.username, self.password),
                            timeout=2,
                            verify=False
                        )
                        
                        if response.status_code == 200 and len(response.text) > 10:
                            try:
                                json_data = response.json()
                                if json_data:
                                    print(f"  ✓ {endpoint}?{list(params.keys())[0]}={method}")
                                    data[f"{endpoint}_{method}"] = json_data
                            except:
                                pass
                except:
                    pass
        
        return {"success": bool(data), "data": data, "method": "AJAX Style"}
    
    def method_5_xml_config(self):
        """Archivos de configuración XML"""
        xml_urls = [
            '/config.xml',
            '/cfg',
            '/cfg.xml',
            '/system.xml',
            '/device.xml',
        ]
        
        data = {}
        
        for url in xml_urls:
            try:
                response = self.session.get(
                    urljoin(self.base_url, url),
                    auth=(self.username, self.password),
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200 and ('xml' in response.headers.get('Content-Type', '') or '<?xml' in response.text):
                    print(f"  ✓ {url} (XML encontrado)")
                    data[url] = response.text[:1000]  # Primeros 1000 chars
                    
            except:
                pass
        
        return {"success": bool(data), "data": data, "method": "XML Config"}
    
    def method_6_json_api(self):
        """APIs JSON modernas"""
        json_endpoints = [
            '/api/v1/device',
            '/api/v1/system',
            '/api/device',
            '/api/system',
            '/api/info',
            '/v1/device',
            '/v1/system',
            '/rest/device',
            '/rest/system',
        ]
        
        data = {}
        
        for endpoint in json_endpoints:
            try:
                response = self.session.get(
                    urljoin(self.base_url, endpoint),
                    auth=(self.username, self.password),
                    headers={'Accept': 'application/json'},
                    timeout=3,
                    verify=False
                )
                
                if response.status_code == 200:
                    try:
                        json_data = response.json()
                        if json_data:
                            print(f"  ✓ {endpoint}")
                            data[endpoint] = json_data
                    except:
                        pass
            except:
                pass
        
        return {"success": bool(data), "data": data, "method": "JSON API"}
    
    def method_7_snmp_info(self):
        """Información vía SNMP (si está habilitado)"""
        # Requeriría pysnmp, por ahora solo documentar
        return {
            "success": False, 
            "data": {},
            "method": "SNMP",
            "note": "SNMP requiere librería adicional - Puerto 161"
        }
    
    def method_8_upnp_discovery(self):
        """Descubrimiento UPnP"""
        try:
            import socket
            
            SSDP_ADDR = "239.255.255.250"
            SSDP_PORT = 1900
            SSDP_MX = 2
            SSDP_ST = "ssdp:all"
            
            msg = "\r\n".join([
                'M-SEARCH * HTTP/1.1',
                f'HOST: {SSDP_ADDR}:{SSDP_PORT}',
                'MAN: "ssdp:discover"',
                f'MX: {SSDP_MX}',
                f'ST: {SSDP_ST}',
                '', ''
            ])
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            sock.settimeout(3)
            sock.sendto(msg.encode(), (SSDP_ADDR, SSDP_PORT))
            
            responses = []
            try:
                while True:
                    data, addr = sock.recvfrom(1024)
                    if addr[0] == self.host:
                        responses.append(data.decode())
            except socket.timeout:
                pass
            
            return {"success": bool(responses), "data": {"responses": responses}, "method": "UPnP"}
            
        except Exception as e:
            return {"success": False, "error": str(e), "method": "UPnP"}
    
    def method_9_sip_headers(self):
        """Headers SIP si hay servidor SIP expuesto"""
        return {
            "success": False,
            "data": {},
            "method": "SIP Headers",
            "note": "SIP requiere librería SIP - Puerto 5060"
        }
    
    def method_10_telnet_banner(self):
        """Banner de telnet"""
        try:
            import socket
            
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.host, 23))
            banner = sock.recv(1024).decode('utf-8', errors='ignore')
            sock.close()
            
            print(f"  ✓ Banner telnet recibido")
            
            return {"success": True, "data": {"banner": banner}, "method": "Telnet Banner"}
            
        except Exception as e:
            return {"success": False, "error": str(e), "method": "Telnet Banner"}
    
    def method_11_header_analysis(self):
        """Análisis exhaustivo de headers HTTP"""
        try:
            response = self.session.get(
                self.base_url,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            headers_info = dict(response.headers)
            
            # Buscar información en headers personalizados
            interesting_headers = {}
            for key, value in headers_info.items():
                if any(word in key.lower() for word in ['device', 'model', 'version', 'serial', 'grandstream']):
                    interesting_headers[key] = value
            
            return {
                "success": bool(interesting_headers),
                "data": {
                    "all_headers": headers_info,
                    "interesting": interesting_headers
                },
                "method": "HTTP Headers"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def method_12_javascript_parsing(self):
        """Parseo de archivos JavaScript"""
        try:
            response = self.session.get(
                self.base_url,
                auth=(self.username, self.password),
                timeout=5,
                verify=False
            )
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            js_data = {}
            
            # Buscar scripts inline
            for script in soup.find_all('script'):
                if script.string:
                    # Buscar variables con información del dispositivo
                    patterns = {
                        'deviceModel': r'deviceModel\s*=\s*["\']([^"\']+)["\']',
                        'deviceMAC': r'(?:mac|macAddress)\s*=\s*["\']([^"\']+)["\']',
                        'firmwareVersion': r'(?:firmware|version)\s*=\s*["\']([^"\']+)["\']',
                        'serialNumber': r'serialNumber\s*=\s*["\']([^"\']+)["\']',
                    }
                    
                    for key, pattern in patterns.items():
                        match = re.search(pattern, script.string, re.IGNORECASE)
                        if match:
                            js_data[key] = match.group(1)
            
            # Buscar archivos JS externos
            for script in soup.find_all('script', src=True):
                try:
                    js_url = urljoin(self.base_url, script['src'])
                    js_response = self.session.get(js_url, timeout=3, verify=False)
                    
                    if js_response.status_code == 200:
                        # Buscar patrones en JS externo
                        if 'HT818' in js_response.text or 'Grandstream' in js_response.text:
                            js_data[f"file_{script['src']}"] = "Contains device info"
                except:
                    pass
            
            return {"success": bool(js_data), "data": js_data, "method": "JavaScript Parsing"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}


def main():
    import sys
    
    host = sys.argv[1] if len(sys.argv) > 1 else "192.168.100.1"
    username = sys.argv[2] if len(sys.argv) > 2 else "admin"
    password = sys.argv[3] if len(sys.argv) > 3 else "admin"
    
    extractor = GrandstreamInfoExtractor(host, username, password)
    results = extractor.test_all_methods()
    
    # Consolidar resultados
    print("\n" + "="*80)
    print("CONSOLIDACIÓN DE RESULTADOS")
    print("="*80)
    
    successful_methods = [m for m, r in results.items() if r.get('success')]
    print(f"\nMétodos exitosos: {len(successful_methods)}/12")
    
    all_device_info = {}
    
    for method, result in results.items():
        if result.get('success') and result.get('data'):
            print(f"\n[{method}] Datos encontrados:")
            for key, value in result['data'].items():
                print(f"  {key}: {value}")
                all_device_info[f"{method}_{key}"] = value
    
    # Guardar resultados
    output = {
        "timestamp": datetime.now().isoformat(),
        "host": host,
        "detailed_results": results,
        "consolidated_info": all_device_info,
        "summary": {
            "total_methods": 12,
            "successful_methods": len(successful_methods),
            "methods_with_data": successful_methods
        }
    }
    
    filename = f"grandstream_exhaustive_{datetime.now().strftime('%d_%m_%y_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[+] Resultados guardados en: {filename}")
    
    # Conclusión
    print("\n" + "="*80)
    print("CONCLUSIÓN")
    print("="*80)
    
    if len(successful_methods) == 0:
        print("\n⚠️  NINGÚN MÉTODO EXITOSO")
        print("\nPosibles causas:")
        print("  1. El dispositivo NO es un Grandstream HT818")
        print("  2. La IP es de otro dispositivo (ONT, router, etc.)")
        print("  3. El HT818 está detrás de NAT/gateway")
        print("  4. Credenciales incorrectas")
    else:
        print(f"\n✓ {len(successful_methods)} método(s) exitoso(s)")
        print("\nInformación extraída del dispositivo real en esa IP")


if __name__ == "__main__":
    main()
