#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import socket
import ssl
import json
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse

class HTTPClient:
    """Cliente HTTP personalizado para interactuar con ONTs"""
    
    def __init__(self, host: str, port: int = 80, timeout: int = 10, verify_ssl: bool = False):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.verify_ssl = verify_ssl
        self.last_response: Dict[str, Any] = {}

    def _create_socket(self, use_ssl: bool = False) -> socket.socket:
        """Crea y configura un socket"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        if use_ssl:
            context = ssl.create_default_context()
            if not self.verify_ssl:
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=self.host)
            
        return sock

    def _send_request(self, method: str, path: str, headers: Dict[str, str] = None, 
                     data: str = None, use_ssl: bool = False, auth: str = None) -> Tuple[Dict[str, Any], str]:
        """Envía una solicitud HTTP y retorna la respuesta"""
        if headers is None:
            headers = {}
            
        # Headers exactamente como curl
        default_headers = {
            'User-Agent': 'curl/8.13.0',
            'Accept': '*/*',
            'Host': self.host,
            'Connection': 'keep-alive'
        }
        
        # Combinar headers
        headers = {**default_headers, **headers}
        
        # Agregar autenticación si se proporciona
        if auth:
            headers['Authorization'] = auth
            
        sock = self._create_socket(use_ssl)
        try:
            sock.connect((self.host, self.port))
            
            # Replicar exactamente el formato de curl
            request = f"{method} {path} HTTP/1.1\r\n"
            request += f"Host: {self.host}\r\n"
            request += "User-Agent: curl/8.13.0\r\n"
            request += "Accept: */*\r\n"
            
            # Agregar otros headers si existen
            for key, value in headers.items():
                if key.lower() not in ['host', 'user-agent', 'accept']:
                    request += f"{key}: {value}\r\n"
            
            # Terminar los headers con CRLF
            request += "\r\n"
            
            # Enviar como bytes en una sola operación
            sock.send(request.encode('ascii'))
            
            # Enviar datos si existen
            if data:
                sock.send(data.encode('ascii'))
            
            # Recibir la respuesta con timeout más corto
            sock.settimeout(5)
            response = b""
            try:
                while True:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                    if b"\r\n\r\n" in response and not data:  # Si no hay datos POST, terminar después de headers
                        break
            except socket.timeout:
                if not response:
                    raise  # Re-raise si no recibimos nada
                # Si ya tenemos datos, continuar con el procesamiento
                
            return self._parse_response(response.decode('utf-8', errors='ignore'))
            
        finally:
            sock.close()

    def _parse_response(self, response: str) -> Tuple[Dict[str, Any], str]:
        """Parsea la respuesta HTTP"""
        # Separar headers del body
        header_end = response.find('\r\n\r\n')
        headers_raw = response[:header_end]
        body = response[header_end + 4:]
        
        # Parsear la línea de estado
        status_line, *header_lines = headers_raw.split('\r\n')
        version, status, *reason = status_line.split(' ')
        
        # Parsear headers
        headers = {}
        for line in header_lines:
            if ': ' in line:
                key, value = line.split(': ', 1)
                headers[key.lower()] = value
        
        parsed_response = {
            'status': int(status),
            'reason': ' '.join(reason),
            'headers': headers,
            'version': version,
            'body': body
        }
        
        return parsed_response, body

    def get(self, path: str = '/', headers: Dict[str, str] = None) -> Tuple[Dict[str, Any], str]:
        """Realiza una solicitud GET"""
        return self._send_request('GET', path, headers)

    def post(self, path: str = '/', data: str = None, 
             headers: Dict[str, str] = None) -> Tuple[Dict[str, Any], str]:
        """Realiza una solicitud POST"""
        if headers is None:
            headers = {}
        headers['Content-Type'] = headers.get('Content-Type', 'application/json')
        return self._send_request('POST', path, headers, data)

    def options(self, path: str = '/', headers: Dict[str, str] = None) -> Tuple[Dict[str, Any], str]:
        """Realiza una solicitud OPTIONS"""
        return self._send_request('OPTIONS', path, headers)

    def with_basic_auth(self, username: str, password: str) -> 'HTTPClient':
        """Configura autenticación básica"""
        import base64
        auth_string = base64.b64encode(f"{username}:{password}".encode()).decode()
        return self._send_request('GET', '/', auth=f'Basic {auth_string}')

    def with_digest_auth(self, username: str, password: str, path: str = '/') -> 'HTTPClient':
        """Configura autenticación digest"""
        # Primera solicitud para obtener el nonce
        response, _ = self._send_request('GET', path)
        if response['status'] != 401 or 'www-authenticate' not in response['headers']:
            return None

        # Parsear el header WWW-Authenticate
        import hashlib
        import time
        import uuid

        auth_header = response['headers']['www-authenticate']
        if not auth_header.startswith('Digest '):
            return None

        # Extraer parámetros del header
        params = {}
        for param in auth_header[7:].split(','):
            if '=' in param:
                key, value = param.strip().split('=', 1)
                params[key] = value.strip('"')

        # Generar respuesta digest
        nonce = params.get('nonce', '')
        realm = params.get('realm', '')
        qop = params.get('qop', '')
        
        if qop == 'auth':
            nc = '00000001'
            cnonce = str(uuid.uuid4())
            
            ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode()).hexdigest()
            ha2 = hashlib.md5(f"GET:{path}".encode()).hexdigest()
            
            if qop:
                response = hashlib.md5(
                    f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode()
                ).hexdigest()
            else:
                response = hashlib.md5(f"{ha1}:{nonce}:{ha2}".encode()).hexdigest()

            auth_response = (
                f'Digest username="{username}", realm="{realm}", nonce="{nonce}", '
                f'uri="{path}", response="{response}", qop={qop}, nc={nc}, cnonce="{cnonce}"'
            )
            
            return self._send_request('GET', path, auth=auth_response)
        
        return None

    def test_connection(self) -> Dict[str, Any]:
        """Prueba la conexión al dispositivo"""
        try:
            response, _ = self.get('/')
            return {
                'status': 'success',
                'code': response['status'],
                'server': response['headers'].get('server', 'Unknown')
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }

    def get_device_info(self) -> Dict[str, Any]:
        """Intenta obtener información del dispositivo"""
        common_paths = ['/', '/info', '/status', '/device_info', '/deviceinfo']
        device_info = {}
        
        for path in common_paths:
            try:
                response, body = self.get(path)
                if response['status'] == 200:
                    device_info[path] = {
                        'status_code': response['status'],
                        'content_type': response['headers'].get('content-type', 'Unknown'),
                        'server': response['headers'].get('server', 'Unknown'),
                        'body_length': len(body)
                    }
            except:
                continue
                
        return device_info
