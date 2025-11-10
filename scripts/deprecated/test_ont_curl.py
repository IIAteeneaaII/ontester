#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json

# Agregar el directorio src al path de Python
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from backend.protocols.http_client import HTTPClient

def test_ont_like_curl():
    """Prueba las mismas peticiones que funcionaron con curl"""
    print("\n=== Pruebas emulando curl ===")
    client = HTTPClient("192.168.100.1")
    results = {}

    # Test 1: GET básico
    print("\n1. GET básico HTTP/1.1")
    response, body = client.get('/')
    results['basic_get'] = {
        'status': response['status'],
        'headers': response['headers'],
        'body_length': len(body) if body else 0
    }
    print(f"Estado: {response['status']}")

    # Test 2: HEAD request
    print("\n2. HEAD request")
    headers = {'User-Agent': 'curl/8.13.0'}
    response, _ = client._send_request('HEAD', '/', headers)
    results['head_request'] = {
        'status': response['status'],
        'headers': response['headers']
    }
    print(f"Estado: {response['status']}")

    # Test 3: POST con Content-Length: 0
    print("\n3. POST con Content-Length: 0")
    headers = {
        'User-Agent': 'curl/8.13.0',
        'Content-Length': '0'
    }
    response, body = client.post('/', headers=headers)
    results['empty_post'] = {
        'status': response['status'],
        'headers': response['headers'],
        'body_length': len(body) if body else 0
    }
    print(f"Estado: {response['status']}")

    # Test 4: GET con User-Agent específico
    print("\n4. GET con User-Agent Mozilla")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response, body = client.get('/', headers)
    results['mozilla_get'] = {
        'status': response['status'],
        'headers': response['headers'],
        'body_length': len(body) if body else 0
    }
    print(f"Estado: {response['status']}")

    return results

def main():
    """Función principal"""
    print("=== ONT Tester - Pruebas emulando curl ===")
    
    results = {
        'curl_tests': test_ont_like_curl()
    }

    # Guardar resultados
    with open('curl_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\nPruebas completadas. Resultados guardados en curl_results.json")

if __name__ == "__main__":
    main()