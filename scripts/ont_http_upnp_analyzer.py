#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import socket
import concurrent.futures
from urllib.parse import urlparse

# Agregar el directorio src al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.protocols.http_client import HTTPClient
from backend.protocols.upnp_client import UPnPClient

def test_auth_combination(client: HTTPClient, username: str, password: str, auth_type: str = 'basic'):
    """Prueba una combinación de autenticación"""
    try:
        if auth_type == 'basic':
            response, body = client.with_basic_auth(username, password)
        else:
            response, body = client.with_digest_auth(username, password)
        return {
            'status': response['status'],
            'headers': response['headers'],
            'body': body
        }
    except Exception as e:
        return {'error': str(e)}

def analyze_http_detailed():
    """Análisis detallado del servicio HTTP"""
    print("\n=== Análisis Detallado HTTP ===")
    client = HTTPClient("192.168.100.1")
    results = {
        'basic_info': {},
        'paths': {},
        'methods': {},
        'headers': {},
        'auth_tests': {}
    }
    
    # Pruebas de autenticación con credenciales conocidas
    print("Probando autenticación conocida: root/admin")
    auth_result = test_auth_combination(client, "root", "admin")
    results['auth_tests']['known_credentials'] = auth_result
    
    # Headers específicos de ONT/TR-069
    ont_headers = {
        'User-Agent': 'ONT Tester/1.0',
        'X-Requested-With': 'XMLHttpRequest',
        'SOAPAction': '"urn:dslforum-org:service:DeviceConfig:1#GetDeviceInfo"',
        'Content-Type': 'text/xml; charset="utf-8"'
    }
    print("Probando headers específicos de ONT")
    
    # 1. Probar rutas comunes de ONTs
    common_paths = [
        '/',                    # Raíz
        '/status',             # Estado
        '/info',              # Información
        '/admin',             # Administración
        '/login',             # Login
        '/device',            # Info del dispositivo
        '/management',        # Gestión
        '/network',           # Configuración de red
        '/system',            # Sistema
        '/diagnostic',        # Diagnósticos
        '/ont',              # Específico ONT
        '/gpon',             # Configuración GPON
        '/wifi',             # Configuración WiFi
        '/voip',             # Configuración VoIP
        '/wan',              # Configuración WAN
        '/lan',              # Configuración LAN
        '/firewall',         # Firewall
        '/maintenance',      # Mantenimiento
        '/backup',           # Backup/Restore
        '/upgrade',          # Actualización
        '/reboot',           # Reinicio
        '/reset',            # Reset
        '/log'               # Logs
    ]
    
    print("\nProbando rutas comunes...")
    for path in common_paths:
        try:
            response, body = client.get(path)
            results['paths'][path] = {
                'status': response['status'],
                'headers': response['headers'],
                'content_length': len(body) if body else 0,
                'server': response['headers'].get('server', 'Unknown')
            }
            print(f"Ruta {path}: Status {response['status']}")
        except Exception as e:
            print(f"Error en ruta {path}: {str(e)}")
            continue

    # 2. Probar diferentes métodos HTTP
    test_methods = ['GET', 'POST', 'HEAD', 'OPTIONS']
    print("\nProbando métodos HTTP...")
    for method in test_methods:
        try:
            if method == 'GET':
                response, _ = client.get('/')
            elif method == 'POST':
                response, _ = client.post('/')
            elif method == 'HEAD':
                response, _ = client.get('/', headers={'Connection': 'close'})
            elif method == 'OPTIONS':
                response, _ = client.options('/')
                
            results['methods'][method] = {
                'status': response['status'],
                'headers': response['headers']
            }
            print(f"Método {method}: Status {response['status']}")
        except Exception as e:
            print(f"Error en método {method}: {str(e)}")
            continue

    return results

def analyze_upnp_detailed():
    """Análisis detallado del servicio UPnP"""
    print("\n=== Análisis Detallado UPnP ===")
    client = UPnPClient()
    results = {
        'devices': [],
        'services': [],
        'details': {}
    }
    
    # 1. Descubrimiento múltiple para obtener toda la información posible
    print("\nRealizando múltiples descubrimientos UPnP...")
    for i in range(3):
        devices = client.discover()
        for device in devices:
            if device.get('ip') == '192.168.100.1':
                results['devices'].append(device)
                
                # Intentar obtener descripción del dispositivo
                if 'location' in device:
                    try:
                        device_info = client.get_device_info(device['location'])
                        if device_info:
                            results['details'][f'attempt_{i}'] = device_info
                    except Exception as e:
                        print(f"Error obteniendo detalles: {str(e)}")
                
                # Intentar listar servicios
                try:
                    services = client.list_services(device.get('location', ''))
                    if services:
                        results['services'].extend(services)
                except Exception as e:
                    print(f"Error listando servicios: {str(e)}")
        
        time.sleep(1)  # Esperar entre intentos
    
    return results

def main():
    """Función principal"""
    print("ONT Tester - Análisis Profundo HTTP y UPnP")
    print("==========================================")
    
    all_results = {
        'http': None,
        'upnp': None
    }
    
    try:
        # 1. Análisis HTTP detallado
        all_results['http'] = analyze_http_detailed()
        
        # 2. Análisis UPnP detallado
        all_results['upnp'] = analyze_upnp_detailed()
        
        # Guardar resultados
        with open('analysis_results.json', 'w') as f:
            json.dump(all_results, f, indent=2)
            print("\nResultados guardados en 'analysis_results.json'")
        
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()