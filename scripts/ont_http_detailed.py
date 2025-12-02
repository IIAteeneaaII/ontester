#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
from typing import Dict, Any, Optional

# Agregar el directorio src al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.protocols.http_client import HTTPClient

class ONTHttpAnalyzer:
    """Clase para realizar pruebas HTTP detalladas en la ONT"""
    
    def __init__(self, host: str = "192.168.100.1"):
        self.host = host
        self.client = HTTPClient(host)
        self.results = {
            'device_info': {},
            'available_apis': {},
            'security': {},
            'services': {}
        }

    def analyze_device_info(self):
        """Analiza información básica del dispositivo"""
        print("\n=== Análisis de Información del Dispositivo ===")
        
        # APIs conocidas
        apis = [
            '/get_device_name',
            '/get_operator',
            '/pon_link_info_inter.html',
            '/wifi_info_inter.html',
            '/wifi_info_inter5g.html'
        ]
        
        for api in apis:
            try:
                print(f"\nProbando {api}...")
                response, body = self.client.get(api)
                self.results['available_apis'][api] = {
                    'status': response['status'],
                    'content_type': response['headers'].get('content-type', ''),
                    'body_length': len(body) if body else 0
                }
                
                if response['status'] == 200:
                    print("- Accesible")
                    # Intentar parsear JSON si es una API
                    if api.startswith('/get_'):
                        try:
                            data = json.loads(body)
                            self.results['device_info'].update(data)
                            print(f"- Datos: {json.dumps(data, indent=2)}")
                        except:
                            pass
                else:
                    print(f"- No accesible (código {response['status']})")
            except Exception as e:
                print(f"Error: {str(e)}")
                self.results['available_apis'][api] = {'error': str(e)}

    def analyze_security_headers(self):
        """Analiza los headers de seguridad"""
        print("\n=== Análisis de Headers de Seguridad ===")
        
        response, _ = self.client.get('/')
        if response['status'] == 200:
            security_headers = {
                'X-Frame-Options': 'Protección contra clickjacking',
                'X-Content-Type-Options': 'Prevención de MIME sniffing',
                'X-XSS-Protection': 'Protección XSS del navegador',
                'Content-Security-Policy': 'Políticas de seguridad de contenido',
                'Strict-Transport-Security': 'Forzar HTTPS',
                'Access-Control-Allow-Origin': 'Configuración CORS'
            }
            
            print("\nHeaders de seguridad encontrados:")
            for header, description in security_headers.items():
                if header.lower() in response['headers']:
                    value = response['headers'][header.lower()]
                    print(f"- {header}: {value}")
                    self.results['security'][header] = value
                else:
                    print(f"- {header}: No presente")
                    self.results['security'][header] = None

    def analyze_available_services(self):
        """Analiza los servicios disponibles"""
        print("\n=== Análisis de Servicios Disponibles ===")
        
        # Servicios comunes en ONTs
        services = {
            'wifi': ['/wifi_info_inter.html', '/wifi_info_inter5g.html'],
            'pon': ['/pon_link_info_inter.html'],
            'voip': ['/voice_info_inter.html'],
            'ethernet': ['/ethernetPorts.html'],
            'dhcp': ['/dhcp_user_list_inter.html'],
            'management': ['/admin_management_inter.html']
        }
        
        for service, paths in services.items():
            print(f"\nVerificando servicio {service}:")
            service_status = {'available': False, 'paths': {}}
            
            for path in paths:
                try:
                    response, _ = self.client.get(path)
                    accessible = response['status'] == 200
                    service_status['paths'][path] = {
                        'status': response['status'],
                        'accessible': accessible
                    }
                    if accessible:
                        service_status['available'] = True
                    print(f"- {path}: {'Accesible' if accessible else 'No accesible'}")
                except Exception as e:
                    print(f"- Error en {path}: {str(e)}")
                    service_status['paths'][path] = {'error': str(e)}
            
            self.results['services'][service] = service_status

    def run_analysis(self):
        """Ejecuta el análisis completo"""
        print("=== ONT Tester - Análisis HTTP Detallado ===")
        
        self.analyze_device_info()
        self.analyze_security_headers()
        self.analyze_available_services()
        
        # Guardar resultados
        output_file = 'ont_http_analysis.json'
        with open(output_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\nAnálisis completado. Resultados guardados en {output_file}")
        return self.results

def main():
    analyzer = ONTHttpAnalyzer()
    analyzer.run_analysis()

if __name__ == "__main__":
    main()