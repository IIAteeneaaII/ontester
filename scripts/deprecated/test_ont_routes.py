#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json

# Agregar el directorio src al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.protocols.http_client import HTTPClient

def test_specific_routes():
    """Prueba las rutas específicas detectadas en la ONT"""
    print("\n=== Pruebas de Rutas Específicas ===")
    client = HTTPClient("192.168.100.1")
    results = {}

    # Rutas detectadas en el HTML
    html_routes = {
        'login_routes': [
            '/html/login_inter.html',
            '/html/login_3bb.html',
            '/html/login_pldt.html',
            '/public/index.html',
            '/html/login_paltel.html',
            '/html/login_ais.html',
            '/html/login_mytm.html',
            '/html/login_ed.html',
            '/html/login_romania.html',
            '/html/login_magyar.html',
            '/html/login_bz_intelbras.html',
            '/new_ui/login_es_digi.html',
            '/new_ui/login.html',
            '/html/login_mex_netwey.html'
        ],
        'js_routes': [
            '/js/jquery.js',
            '/js/xhr.js',
            '/js/versionControl.js',
            '/js/access.js'
        ],
        'api_routes': [
            '/get_device_name',
            '/get_operator'
        ]
    }

    # Probar cada categoría de rutas
    for category, routes in html_routes.items():
        print(f"\nProbando {category}:")
        results[category] = {}
        
        for route in routes:
            try:
                print(f"  Probando {route}...")
                response, body = client.get(route)
                results[category][route] = {
                    'status': response['status'],
                    'headers': response['headers'],
                    'body_length': len(body) if body else 0
                }
                
                # Si es una ruta API, mostrar el contenido de la respuesta
                if category == 'api_routes' and response['status'] == 200:
                    try:
                        results[category][route]['json'] = json.loads(body)
                        print(f"    Respuesta JSON: {json.dumps(results[category][route]['json'], indent=2)}")
                    except:
                        print("    No es una respuesta JSON válida")
                
                print(f"    Estado: {response['status']}")
                print(f"    Longitud: {len(body) if body else 0} bytes")
                
            except Exception as e:
                print(f"  Error en {route}: {str(e)}")
                results[category][route] = {'error': str(e)}

    # Probar rutas con diferentes User-Agents
    user_agents = {
        'browser': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'mobile': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1',
        'curl': 'curl/8.13.0',
        'ont': 'GPON-ONT-Management/1.0'
    }

    print("\nProbando rutas API con diferentes User-Agents:")
    results['user_agent_tests'] = {}
    
    for agent_name, agent_value in user_agents.items():
        print(f"\nProbando con {agent_name}:")
        results['user_agent_tests'][agent_name] = {}
        
        for route in html_routes['api_routes']:
            try:
                headers = {'User-Agent': agent_value}
                response, body = client.get(route, headers)
                results['user_agent_tests'][agent_name][route] = {
                    'status': response['status'],
                    'headers': response['headers'],
                    'body_length': len(body) if body else 0
                }
                print(f"  {route}: {response['status']}")
            except Exception as e:
                print(f"  Error en {route}: {str(e)}")
                results['user_agent_tests'][agent_name][route] = {'error': str(e)}

    return results

def main():
    """Función principal"""
    print("=== ONT Tester - Pruebas de Rutas Específicas ===")
    
    results = {
        'route_tests': test_specific_routes()
    }

    # Guardar resultados
    with open('route_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\nPruebas completadas. Resultados guardados en route_analysis.json")

if __name__ == "__main__":
    main()