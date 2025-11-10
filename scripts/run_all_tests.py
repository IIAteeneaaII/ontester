#!/usr/bin/env python3
import argparse
import json
import sys
import os
from datetime import datetime
import subprocess
from pathlib import Path

class ONTTesterSuite:
    # Modelos soportados oficialmente
    SUPPORTED_MODELS = {
        'MOD001': 'FIBERHOME HG6145F',
        'MOD002': 'ZTE F670L',
        'MOD003': 'HUAWEI HG8145X6-10',
        'MOD004': 'HUAWEI HG8145V5',
        'MOD005': 'HUAWEI HG145V5 SMALL'
    }

    def __init__(self, host, model):
        if model.upper() not in self.SUPPORTED_MODELS:
            raise ValueError(f"Modelo no soportado. Modelos soportados: {', '.join(self.SUPPORTED_MODELS.keys())}")
        
        self.host = host
        self.model = model.upper()
        self.date_prefix = datetime.now().strftime("%d_%m_%y")
        self.timestamp = datetime.now().strftime("%H%M%S")
        self.report_dir = self._create_report_directory()
        self.results = {
            "metadata": {
                "date": datetime.now().isoformat(),
                "host": host,
                "model": model,
                "timestamp": self.timestamp
            },
            "tests": {}
        }

    def _create_report_directory(self):
        base_dir = Path(__file__).parent.parent / "reports"
        report_dir = base_dir / f"{self.date_prefix}_{self.model}" / self.timestamp
        report_dir.mkdir(parents=True, exist_ok=True)
        return report_dir

    def _run_test(self, script_name, args=None):
        if args is None:
            args = []
        
        script_path = Path(__file__).parent / script_name
        cmd = [sys.executable, str(script_path), "--host", self.host] + args

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return {
                "status": "success",
                "output": result.stdout,
                "error": None
            }
        except subprocess.CalledProcessError as e:
            return {
                "status": "error",
                "output": e.stdout,
                "error": e.stderr
            }

    def run_all_tests(self):
        print("[*] Ejecutando prueba de conectividad basica...")
        self.results["tests"]["basic"] = self._run_test("ont_basic_tester.py")
        
        print("[*] Ejecutando analisis de protocolos...")
        self.results["tests"]["protocols"] = self._run_test("test_protocols.py")
        
        print("[*] Ejecutando pruebas de red...")
        self.results["tests"]["network"] = self._run_test("ont_network_tester.py")
        
        print("[*] Ejecutando analisis HTTP detallado...")
        self.results["tests"]["http"] = self._run_test(
            "ont_http_detailed.py",
            ["--model", self.model]
        )
        
        print("[*] Ejecutando analisis UPnP...")
        self.results["tests"]["upnp"] = self._run_test("ont_http_upnp_analyzer.py")

    def generate_report(self):
        report = [
            f"# Reporte de Pruebas ONT - {self.model}",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            "",
            "## Resumen de Errores",
            ""
        ]

        has_errors = False
        for test_name, result in self.results["tests"].items():
            if result["status"] == "error":
                has_errors = True
                error_msg = result['error'].split('\n')[0]
                report.append(f"- [ERROR] {test_name}: {error_msg}")
            elif result.get("output") and "timed out" in result["output"]:
                has_errors = True
                report.append(f"- [TIMEOUT] {test_name}")
        
        if not has_errors:
            report.append("No se detectaron errores criticos")

        report.extend([
            "",
            "## Informacion General",
            f"- Modelo: {self.model}",
            f"- Host: {self.host}",
            "",
            "## Resultados de las Pruebas",
            ""
        ])

        for test_name, result in self.results["tests"].items():
            report.append(f"### {test_name.title()}")
            report.append(f"Estado: [{'OK' if result['status'] == 'success' else 'FAIL'}] {result['status']}")
            report.append("")
            
            if result["status"] == "success":
                report.append("```")
                report.append(result["output"])
                report.append("```")
            else:
                report.append("Error encontrado:")
                report.append("```")
                report.append(result["error"])
                report.append("```")
            report.append("")

        return "\n".join(report)

    def save_results(self):
        json_path = self.report_dir / f"{self.date_prefix}_{self.model}_{self.timestamp}_results.json"
        with open(json_path, "w") as f:
            json.dump(self.results, f, indent=2)

        md_path = self.report_dir / f"{self.date_prefix}_{self.model}_{self.timestamp}_report.md"
        with open(md_path, "w") as f:
            f.write(self.generate_report())

        print(f"\n[+] Resultados guardados en:")
        print(f"    - JSON: {json_path}")
        print(f"    - Reporte: {md_path}")

def check_dependencies():
    missing = []
    
    # Verificar nmap ejecutable
    nmap_path = "C:\\Program Files (x86)\\Nmap\\nmap.exe"
    if not os.path.exists(nmap_path):
        missing.append("nmap")
    
    # Verificar python packages
    required_packages = ["requests", "scapy"]
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)
            
    # Verificar python-nmap con ruta completa
    try:
        import nmap
    except:
        missing.append("python-nmap")
    
    if missing:
        print("\n[ERROR] Faltan dependencias necesarias:")
        for dep in missing:
            if dep == "nmap":
                print("   - nmap: Necesario instalar nmap en el sistema")
                print("     Windows: https://nmap.org/download.html")
                print("     Linux: sudo apt install nmap")
            else:
                print(f"   - {dep}: pip install {dep}")
        print("\nPor favor, instala las dependencias y vuelve a intentarlo.")
        sys.exit(1)

def main():
    print("[INFO] Verificando dependencias...")
    check_dependencies()
    
    parser = argparse.ArgumentParser(description="Suite de pruebas para ONT")
    parser.add_argument("--host", required=True, help="IP de la ONT")
    parser.add_argument("--model", required=True, help="Modelo de la ONT")
    args = parser.parse_args()

    tester = ONTTesterSuite(args.host, args.model)
    
    print(f"[+] Iniciando pruebas para ONT {args.model} en {args.host}")
    print(f"[+] Los resultados se guardaran en: {tester.report_dir}\n")
    
    tester.run_all_tests()
    tester.save_results()

if __name__ == "__main__":
    main()