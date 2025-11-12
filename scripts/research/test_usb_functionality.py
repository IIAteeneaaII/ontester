#!/usr/bin/env python3
"""
Script para probar la funcionalidad USB del ONT HG6145F
Basado en el método AJAX get_usb_info descubierto
"""

import requests
import json
import argparse
from datetime import datetime
from typing import Dict, Any

requests.packages.urllib3.disable_warnings()


class ONTUSBTester:
    """Tester para funcionalidades USB del ONT"""
    
    def __init__(self, host: str, username: str = 'root', password: str = 'admin'):
        self.host = host
        self.username = username
        self.password = password
        self.ajax_url = f"http://{host}/cgi-bin/ajax"
        self.sessionid = None
        
    def _make_ajax_request(self, method: str, params: dict = None) -> Dict[str, Any]:
        """Realiza una petición AJAX al ONT"""
        request_params = params or {}
        request_params['ajaxmethod'] = method
        request_params['_'] = str(int(datetime.now().timestamp() * 1000))
        
        if self.sessionid:
            request_params['sessionid'] = self.sessionid
        
        try:
            response = requests.get(
                self.ajax_url,
                params=request_params,
                auth=(self.username, self.password),
                timeout=5,
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
                    
                    # Actualizar sessionid si está presente
                    if 'sessionid' in data:
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
    
    def get_session(self):
        """Obtiene una sesión válida del dispositivo"""
        print("\n[*] Obteniendo sessionid...")
        result = self._make_ajax_request('get_refresh_sessionid')
        
        if result['success']:
            sessionid = result['data'].get('sessionid')
            if sessionid:
                self.sessionid = sessionid
                print(f"[+] SessionID obtenido: {sessionid}")
                return True
        
        print("[-] No se pudo obtener sessionid")
        return False
    
    def get_usb_info(self) -> Dict[str, Any]:
        """Obtiene información sobre dispositivos USB conectados"""
        print("\n[*] Consultando información USB...")
        result = self._make_ajax_request('get_usb_info')
        
        if result['success']:
            print("[+] Información USB obtenida exitosamente")
            return result['data']
        else:
            print(f"[-] Error al obtener información USB: {result.get('error', 'Unknown')}")
            return None
    
    def test_usb_methods(self):
        """Prueba diferentes métodos AJAX relacionados con USB"""
        print("\n" + "="*80)
        print("PROBANDO MÉTODOS USB")
        print("="*80)
        
        usb_methods = [
            "get_usb_info",
            "get_usb_status",
            "get_usb_devices",
            "get_usb_storage",
            "get_usb_list",
            "get_storage_info",
            "get_storage_list",
            "get_mount_info",
            "get_disk_info",
            "get_samba_status",
            "get_dlna_status",
            "get_ftp_status",
            "get_usb_app_status",
        ]
        
        results = []
        
        for i, method in enumerate(usb_methods, 1):
            print(f"\n[{i}/{len(usb_methods)}] Probando: {method}")
            result = self._make_ajax_request(method)
            
            if result['success']:
                print(f"    [OK] Status: {result['status']}")
                data = result.get('data', {})
                
                if isinstance(data, dict):
                    # Mostrar campos principales
                    for key in data.keys():
                        if key not in ['sessionid', 'session_valid']:
                            value = data[key]
                            if isinstance(value, str) and len(value) > 50:
                                value = value[:50] + "..."
                            print(f"         {key}: {value}")
                
                results.append({
                    "method": method,
                    "accessible": True,
                    "data": data
                })
            else:
                print(f"    [--] Status: {result['status']}")
                results.append({
                    "method": method,
                    "accessible": False,
                    "status": result['status']
                })
        
        return results
    
    def test_usb_with_params(self):
        """Prueba métodos USB con diferentes parámetros"""
        print("\n" + "="*80)
        print("PROBANDO MÉTODOS USB CON PARÁMETROS")
        print("="*80)
        
        test_cases = [
            # Información básica
            {"method": "get_usb_info", "params": {}},
            {"method": "get_usb_info", "params": {"device": "usb1"}},
            {"method": "get_usb_info", "params": {"port": "1"}},
            
            # Storage
            {"method": "get_storage_info", "params": {}},
            {"method": "get_storage_info", "params": {"device": "sda1"}},
            
            # Servicios
            {"method": "get_samba_status", "params": {}},
            {"method": "get_dlna_status", "params": {}},
            {"method": "get_ftp_status", "params": {}},
        ]
        
        results = []
        
        for i, test_case in enumerate(test_cases, 1):
            method = test_case['method']
            params = test_case['params']
            
            print(f"\n[{i}/{len(test_cases)}] {method}")
            if params:
                print(f"    Parámetros: {params}")
            
            result = self._make_ajax_request(method, params)
            
            if result['success']:
                print(f"    [OK] Response recibido")
                results.append({
                    "method": method,
                    "params": params,
                    "accessible": True,
                    "data": result.get('data')
                })
            else:
                print(f"    [--] No accesible")
                results.append({
                    "method": method,
                    "params": params,
                    "accessible": False,
                    "status": result.get('status')
                })
        
        return results
    
    def run_full_test(self):
        """Ejecuta todas las pruebas USB"""
        print("\n" + "="*80)
        print("TEST DE FUNCIONALIDAD USB - ONT HG6145F")
        print("="*80)
        print(f"Host: {self.host}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Obtener sesión
        self.get_session()
        
        # Obtener información básica USB
        usb_info = self.get_usb_info()
        
        # Probar todos los métodos USB
        method_results = self.test_usb_methods()
        
        # Probar métodos con parámetros
        param_results = self.test_usb_with_params()
        
        # Resumen
        print("\n" + "="*80)
        print("RESUMEN DE PRUEBAS USB")
        print("="*80)
        
        accessible_methods = [r for r in method_results if r.get('accessible')]
        print(f"\nMétodos accesibles: {len(accessible_methods)}/{len(method_results)}")
        
        if accessible_methods:
            print("\nMétodos que funcionan:")
            for method in accessible_methods:
                print(f"  - {method['method']}")
        
        # Guardar resultados
        output = {
            "timestamp": datetime.now().isoformat(),
            "host": self.host,
            "basic_usb_info": usb_info,
            "method_discovery": method_results,
            "param_tests": param_results,
            "summary": {
                "total_methods_tested": len(method_results),
                "accessible_methods": len(accessible_methods),
                "methods_with_params": len(param_results)
            }
        }
        
        output_file = f"usb_test_results_{datetime.now().strftime('%d_%m_%y_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        print(f"\n[+] Resultados guardados en: {output_file}")
        
        return output


def main():
    parser = argparse.ArgumentParser(
        description='Prueba la funcionalidad USB del ONT HG6145F'
    )
    parser.add_argument('--host', type=str, default='192.168.100.1',
                        help='Dirección IP del ONT (default: 192.168.100.1)')
    parser.add_argument('--username', type=str, default='root',
                        help='Usuario para autenticación (default: root)')
    parser.add_argument('--password', type=str, default='admin',
                        help='Contraseña para autenticación (default: admin)')
    parser.add_argument('--quick', action='store_true',
                        help='Solo obtener información básica USB')
    
    args = parser.parse_args()
    
    tester = ONTUSBTester(args.host, args.username, args.password)
    
    if args.quick:
        # Solo información básica
        tester.get_session()
        usb_info = tester.get_usb_info()
        
        if usb_info:
            print("\nInformación USB:")
            print(json.dumps(usb_info, indent=2, ensure_ascii=False))
    else:
        # Test completo
        tester.run_full_test()


if __name__ == "__main__":
    main()
