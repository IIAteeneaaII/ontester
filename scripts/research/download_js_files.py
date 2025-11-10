#!/usr/bin/env python3
"""
Descarga archivos JavaScript del ONT para analizar endpoints
"""

import requests
import argparse

requests.packages.urllib3.disable_warnings()

def download_js_files(host: str, username: str = "root", password: str = "admin"):
    """Descarga archivos JS del ONT"""
    
    base_url = f"http://{host}"
    auth = (username, password)
    
    js_files = [
        "/js/jquery.js",
        "/js/xhr.js",
        "/js/versionControl.js",
        "/js/access.js"
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
    }
    
    for js_file in js_files:
        url = f"{base_url}{js_file}"
        print(f"\n[*] Descargando {js_file}...")
        
        try:
            response = requests.get(url, auth=auth, headers=headers, verify=False, timeout=10)
            
            if response.status_code == 200:
                filename = js_file.split('/')[-1]
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                print(f"[+] Guardado en: {filename} ({len(response.text)} bytes)")
            else:
                print(f"[!] Error {response.status_code}")
        except Exception as e:
            print(f"[!] Error: {e}")

def main():
    parser = argparse.ArgumentParser(description='Descarga archivos JS del ONT')
    parser.add_argument('--host', required=True, help='IP del ONT')
    parser.add_argument('--user', default='root', help='Usuario (default: root)')
    parser.add_argument('--password', default='admin', help='Password (default: admin)')
    
    args = parser.parse_args()
    
    download_js_files(args.host, args.user, args.password)

if __name__ == "__main__":
    main()
