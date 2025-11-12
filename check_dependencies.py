#!/usr/bin/env python3
"""
Script para verificar dependencias del proyecto ONT/ATA Testing Suite
"""

import sys
import subprocess
from importlib.metadata import version, PackageNotFoundError

# Definir dependencias requeridas con versiones mínimas
REQUIRED_PACKAGES = {
    'requests': '2.32.0',
    'beautifulsoup4': '4.14.0',
    'paramiko': '4.0.0',
    'telnetlib3': '2.0.8',
    'pyserial': '3.5',
    'urllib3': '2.5.0'
}

def parse_version(version_string):
    """Convierte string de versión a tupla para comparación"""
    try:
        return tuple(map(int, version_string.split('.')[:3]))
    except:
        return (0, 0, 0)

def check_python_version():
    """Verifica la versión de Python"""
    print("\n" + "="*70)
    print("VERIFICACIÓN DE PYTHON")
    print("="*70)
    
    required = (3, 8, 0)
    current = sys.version_info[:3]
    
    print(f"Versión requerida: Python {'.'.join(map(str, required))}+")
    print(f"Versión instalada: Python {'.'.join(map(str, current))}")
    
    if current >= required:
        print("✅ Python: OK")
        return True
    else:
        print("❌ Python: VERSIÓN INSUFICIENTE")
        print(f"   Por favor actualice a Python {'.'.join(map(str, required))} o superior")
        return False

def check_packages():
    """Verifica todas las dependencias"""
    print("\n" + "="*70)
    print("VERIFICACIÓN DE DEPENDENCIAS")
    print("="*70)
    
    all_ok = True
    results = []
    
    for package, min_version in REQUIRED_PACKAGES.items():
        try:
            installed_version = version(package)
            installed_tuple = parse_version(installed_version)
            required_tuple = parse_version(min_version)
            
            if installed_tuple >= required_tuple:
                status = "✅ OK"
                results.append((package, installed_version, min_version, True))
            else:
                status = "⚠️ ACTUALIZAR"
                all_ok = False
                results.append((package, installed_version, min_version, False))
            
            print(f"{status:12} {package:20} (instalado: {installed_version}, mínimo: {min_version})")
            
        except PackageNotFoundError:
            print(f"❌ FALTA    {package:20} (mínimo: {min_version})")
            all_ok = False
            results.append((package, None, min_version, False))
    
    return all_ok, results

def suggest_fixes(results):
    """Sugiere comandos para instalar/actualizar paquetes"""
    missing = [r for r in results if r[1] is None]
    outdated = [r for r in results if r[1] is not None and not r[3]]
    
    if missing or outdated:
        print("\n" + "="*70)
        print("ACCIONES RECOMENDADAS")
        print("="*70)
        
        if missing:
            print("\n📦 Paquetes faltantes:")
            packages = ' '.join([r[0] for r in missing])
            print(f"\n   pip install {packages}")
        
        if outdated:
            print("\n🔄 Paquetes desactualizados:")
            packages = ' '.join([r[0] for r in outdated])
            print(f"\n   pip install --upgrade {packages}")
        
        print("\n💡 O instalar todo desde requirements.txt:")
        print("\n   pip install -r requirements.txt")
        print("   pip install --upgrade -r requirements.txt")

def main():
    print("\n╔══════════════════════════════════════════════════════════════════╗")
    print("║     ONT/ATA Testing Suite - Verificación de Dependencias        ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    
    # Verificar Python
    python_ok = check_python_version()
    
    # Verificar paquetes
    packages_ok, results = check_packages()
    
    # Resumen
    print("\n" + "="*70)
    print("RESUMEN")
    print("="*70)
    
    if python_ok and packages_ok:
        print("\n✅ TODAS LAS DEPENDENCIAS ESTÁN CORRECTAS")
        print("\n🚀 El sistema está listo para usar")
    else:
        print("\n⚠️ SE REQUIEREN ACTUALIZACIONES")
        suggest_fixes(results)
    
    print("\n" + "="*70)
    
    return 0 if (python_ok and packages_ok) else 1

if __name__ == "__main__":
    sys.exit(main())
