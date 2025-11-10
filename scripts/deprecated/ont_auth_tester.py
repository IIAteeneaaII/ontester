#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import socket
import base64
from urllib.parse import urlparse

# Agregar el directorio src al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.protocols.http_client import HTTPClient
from backend.protocols.upnp_client import UPnPClient

def test_ont_auth():
    """Prueba de autenticación específica para ONT"""
    print("\n=== Pruebas de Autenticación ONT ===")
    client = HTTPClient("192.168.100.1")
    results = {}

    # Autenticación Basic con credenciales conocidas
    auth_string = base64.b64encode("root:admin".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth_string}',
        'User-Agent': 'ONT Tester/1.0',
        'Accept': '*/*'
    }

    # Probar rutas comunes con autenticación
    test_paths = [
        '/',
        '/status',
        '/info',
        '/device',
        '/management'
    ]

    for path in test_paths:
        try:
            print(f"\nProbando ruta {path} con autenticación...")
            response, body = client.get(path, headers=headers)
            results[path] = {
                'status': response['status'],
                'headers': response['headers'],
                'body_length': len(body) if body else 0
            }
            print(f"Estado: {response['status']}")
        except Exception as e:
            print(f"Error en {path}: {str(e)}")
            results[path] = {'error': str(e)}

    return results

def test_upnp_ports():
    """Prueba puertos alternativos UPnP"""
    print("\n=== Pruebas de Puertos UPnP ===")
    target_ip = "192.168.100.1"
    results = {}

    test_ports = [1900, 2869, 5000, 49152, 49153, 49154]
    
    for port in test_ports:
        print(f"\nProbando puerto UPnP {port}...")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((target_ip, port))
            
            if result == 0:
                print(f"Puerto {port} está abierto")
                # Intentar obtener información del servicio
                try:
                    sock.send(b"GET / HTTP/1.1\r\nHost: " + target_ip.encode() + b"\r\n\r\n")
                    response = sock.recv(1024)
                    results[port] = {
                        'status': 'open',
                        'response': response.decode('utf-8', errors='ignore')
                    }
                except:
                    results[port] = {'status': 'open', 'response': None}
            else:
                print(f"Puerto {port} está cerrado")
                results[port] = {'status': 'closed'}
            
            sock.close()
        except Exception as e:
            print(f"Error probando puerto {port}: {str(e)}")
            results[port] = {'error': str(e)}

    return results

def main():
    """Función principal"""
    print("=== ONT Tester - Pruebas de Autenticación y UPnP ===")
    
    results = {
        'auth_tests': test_ont_auth(),
        'upnp_tests': test_upnp_ports()
    }

    # Guardar resultados
    with open('auth_upnp_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\nPruebas completadas. Resultados guardados en auth_upnp_results.json")

if __name__ == "__main__":
    main()