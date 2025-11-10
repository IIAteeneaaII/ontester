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
from backend.protocols.snmp_client import SNMPClient

def test_upnp_detailed():
    """Prueba detallada de UPnP"""
    print("\n=== Análisis Detallado UPnP ===")
    client = UPnPClient()
    
    print("\nRealizando múltiples descubrimientos UPnP para obtener más información...")
    all_devices = []
    all_services = set()
    
    # Realizar múltiples intentos de descubrimiento
    for _ in range(3):
        devices = client.discover()
        for device in devices:
            if device.get('ip') == '192.168.100.1':
                all_devices.append(device)
                if 'headers' in device:
                    for key, value in device['headers'].items():
                        if 'service' in key.lower() or 'service' in str(value).lower():
                            all_services.add(value)
        time.sleep(1)  # Esperar entre intentos
    
    # Filtrar información única del ONT
    ont_devices = [d for d in all_devices if d.get('ip') == '192.168.100.1']
    
    if ont_devices:
        ont = ont_devices[0]
        print("\nInformación del ONT:")
        print(f"IP: {ont['ip']}")
        print(f"Sistema: {ont.get('server', 'Desconocido')}")
        print(f"Ubicación: {ont.get('location', 'Desconocida')}")
        
        # Intentar obtener más detalles del dispositivo
        if 'location' in ont:
            print("\nObteniendo descripción del dispositivo...")
            device_info = client.get_device_info(ont['location'])
            print(json.dumps(device_info, indent=2))
            
            print("\nBuscando servicios disponibles...")
            services = client.list_services(ont['location'])
            print(json.dumps(services, indent=2))

def test_snmp():
    """Prueba conexiones SNMP"""
    print("\n=== Pruebas SNMP ===")
    
    # Comunidades SNMP comunes para probar
    communities = ['public', 'private', 'router', 'admin', 'community']
    
    for community in communities:
        print(f"\nProbando comunidad SNMP: {community}")
        client = SNMPClient("192.168.100.1", community=community)
        
        # Probar conexión
        result = client.test_connection()
        print(f"Resultado: {json.dumps(result, indent=2)}")
        
        if result.get('status') == 'success':
            # Si tenemos acceso, obtener más información
            print("\nObteniendo información del dispositivo...")
            device_info = client.get_device_info()
            print(json.dumps(device_info, indent=2))
            break

def analyze_system_info():
    """Analiza información del sistema operativo"""
    print("\n=== Análisis del Sistema Operativo y Puertos ===")
    
    # Recopilar información de todas las fuentes
    system_info = {
        'os_details': [],
        'services': [],
        'open_ports': [],
        'upnp_services': [],
        'http_info': {}
    }
    
    # 1. Información desde UPnP
    client = UPnPClient()
    devices = client.discover()
    ont_devices = [d for d in devices if d.get('ip') == '192.168.100.1']
    
    if ont_devices:
        ont = ont_devices[0]
        if 'server' in ont:
            system_info['os_details'].append({
                'source': 'UPnP',
                'info': ont['server']
            })
            
        # Extraer servicios UPnP
        if 'headers' in ont:
            for key, value in ont['headers'].items():
                if 'service' in key.lower() or 'service' in str(value).lower():
                    system_info['upnp_services'].append(value)
    
    # 2. Escaneo extensivo de puertos
    print("\nRealizando escaneo extensivo de puertos...")
    
    # Puertos comunes y específicos de ONTs
    common_ports = [
        21, 22, 23, 53, 80, 443,  # Puertos estándar
        8080, 8443, 161, 162,     # Puertos alternativos
        69, 4567, 5000, 7547,     # Puertos específicos de ONT
        49152, 49153, 49154,      # Puertos UPnP comunes
        8181, 8200, 9000, 9100    # Puertos de gestión comunes
    ]
    
    # Puertos dinámicos que podrían estar en uso
    dynamic_ports = range(49152, 49162)  # Rango común para UPnP
    all_ports = list(set(common_ports + list(dynamic_ports)))
    
    # Escanear puertos en paralelo para mayor velocidad
    def check_port(port):
        try:
            sock = socket.create_connection(("192.168.100.1", port), timeout=1)
            service_info = {
                'port': port,
                'service': 'unknown'
            }
            
            # Intentar identificar el servicio
            if port == 80 or port == 8080:
                try:
                    sock.send(b"HEAD / HTTP/1.0\r\n\r\n")
                    response = sock.recv(1024).decode('utf-8', errors='ignore')
                    service_info['service'] = 'http'
                    service_info['banner'] = response.split('\r\n')[0]
                except:
                    pass
            
            sock.close()
            return service_info
        except:
            return None
    
    print("Escaneando puertos (esto puede tomar un minuto)...")
    open_ports = []
    
    # Usar múltiples hilos para el escaneo
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_port = {executor.submit(check_port, port): port for port in all_ports}
        for future in concurrent.futures.as_completed(future_to_port):
            result = future.result()
            if result:
                open_ports.append(result)
                print(f"Puerto abierto encontrado: {result['port']}")
    
    system_info['open_ports'] = open_ports
    
    # 3. Análisis HTTP detallado
    print("\nRealizando análisis HTTP detallado...")
    http_client = HTTPClient("192.168.100.1")
    
    # Probar diferentes rutas comunes
    common_paths = ['/', '/status', '/info', '/admin', '/device', '/router', '/ont']
    for path in common_paths:
        try:
            response, body = http_client.get(path)
            if response['status'] == 200:
                system_info['http_info'][path] = {
                    'status': response['status'],
                    'headers': response['headers'],
                    'content_length': len(body) if body else 0
                }
        except:
            continue
    
    # Mostrar resultados
    print("\nInformación del Sistema:")
    print(json.dumps(system_info, indent=2))

def main():
    """Función principal"""
    print("ONT Tester - Análisis Detallado")
    print("================================")
    
    try:
        # 1. Prueba detallada de UPnP
        test_upnp_detailed()
        
        # 2. Prueba de SNMP
        test_snmp()
        
        # 3. Análisis del sistema
        analyze_system_info()
        
    except Exception as e:
        print(f"\nError: {str(e)}")

if __name__ == "__main__":
    main()