#!/usr/bin/env python3
"""
Inspecciona la pagina principal del ONT para identificar formularios y acciones
"""

import requests
import re
from bs4 import BeautifulSoup
import json
import argparse

requests.packages.urllib3.disable_warnings()

def inspect_main_page(host: str, username: str = "root", password: str = "admin"):
    """Inspecciona la pagina principal del ONT"""
    
    url = f"http://{host}/index.html"
    auth = (username, password)
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    }
    
    print(f"\n[*] Inspeccionando {url}\n")
    
    response = requests.get(url, auth=auth, headers=headers, verify=False, timeout=10)
    
    if response.status_code != 200:
        print(f"[!] Error: Status {response.status_code}")
        return
    
    html = response.text
    
    # Guardar HTML completo
    with open("index_page.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("[+] HTML guardado en: index_page.html")
    
    # Buscar frames/iframes
    soup = BeautifulSoup(html, 'html.parser')
    
    print("\n" + "="*80)
    print("FRAMES / IFRAMES:")
    print("="*80)
    frames = soup.find_all(['frame', 'iframe'])
    for frame in frames:
        print(f"  - {frame.name}: {frame.get('src', 'NO SRC')} (name={frame.get('name', 'NO NAME')})")
    
    # Buscar formularios
    print("\n" + "="*80)
    print("FORMULARIOS:")
    print("="*80)
    forms = soup.find_all('form')
    for i, form in enumerate(forms, 1):
        print(f"\nFormulario {i}:")
        print(f"  Action: {form.get('action', 'NO ACTION')}")
        print(f"  Method: {form.get('method', 'GET')}")
        print(f"  Inputs:")
        for inp in form.find_all(['input', 'select', 'textarea']):
            print(f"    - {inp.get('type', 'text')}: {inp.get('name', 'NO NAME')} = {inp.get('value', '')}")
    
    # Buscar scripts
    print("\n" + "="*80)
    print("SCRIPTS:")
    print("="*80)
    scripts = soup.find_all('script')
    for i, script in enumerate(scripts, 1):
        if script.get('src'):
            print(f"  [{i}] External: {script.get('src')}")
        elif script.string and len(script.string) > 50:
            print(f"  [{i}] Inline: {len(script.string)} caracteres")
            # Guardar scripts grandes
            with open(f"script_{i}.js", "w", encoding="utf-8") as f:
                f.write(script.string)
            print(f"      Guardado en: script_{i}.js")
    
    # Buscar URLs en JavaScript
    print("\n" + "="*80)
    print("URLs EN JAVASCRIPT:")
    print("="*80)
    url_pattern = r'["\']/([\w/\.]+\.(?:html|htm|asp|jsp|php|cgi|gch))["\']'
    urls_found = set(re.findall(url_pattern, html))
    for url in sorted(urls_found):
        print(f"  - /{url}")
    
    # Buscar API calls
    print("\n" + "="*80)
    print("POSIBLES API ENDPOINTS:")
    print("="*80)
    api_pattern = r'["\']/(api/[\w/]+)["\']'
    apis_found = set(re.findall(api_pattern, html))
    for api in sorted(apis_found):
        print(f"  - /{api}")
    
    # Buscar XMLHttpRequest / fetch
    print("\n" + "="*80)
    print("AJAX CALLS:")
    print("="*80)
    if 'XMLHttpRequest' in html:
        print("  [+] Usa XMLHttpRequest")
    if 'fetch(' in html:
        print("  [+] Usa fetch()")
    if 'axios' in html.lower():
        print("  [+] Usa axios")
    if 'jquery' in html.lower():
        print("  [+] Usa jQuery")
    
    # Resultados
    results = {
        "frames": [{"src": f.get('src'), "name": f.get('name')} for f in frames],
        "forms": len(forms),
        "scripts": len(scripts),
        "urls_found": list(urls_found),
        "apis_found": list(apis_found)
    }
    
    with open("page_inspection.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    
    print("\n[+] Resultados guardados en: page_inspection.json\n")

def main():
    parser = argparse.ArgumentParser(description='Inspecciona pagina principal del ONT')
    parser.add_argument('--host', required=True, help='IP del ONT')
    parser.add_argument('--user', default='root', help='Usuario (default: root)')
    parser.add_argument('--password', default='admin', help='Password (default: admin)')
    
    args = parser.parse_args()
    
    inspect_main_page(args.host, args.user, args.password)

if __name__ == "__main__":
    main()
