#!/usr/bin/env python3
"""
Utilidad para visualizar la estructura de reportes organizados por fecha.
Muestra un resumen de los reportes y etiquetas generados.
"""

import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def format_date(date_str: str) -> str:
    """Convierte formato dd_mm_yy a formato legible"""
    try:
        day, month, year = date_str.split('_')
        return f"{day}/{month}/20{year}"
    except:
        return date_str

def get_file_info(file_path: Path) -> dict:
    """Extrae información del archivo por su nombre"""
    name = file_path.stem
    parts = name.split('_')
    
    info = {
        'timestamp': '_'.join(parts[:3]) if len(parts) >= 3 else 'unknown',
        'model': None,
        'type': 'unknown',
        'serial': None
    }
    
    # Detectar tipo de reporte
    if 'automated' in name:
        info['type'] = 'automated'
    elif 'retest' in name:
        info['type'] = 'retest'
    elif 'label' in name:
        info['type'] = 'label'
    
    # Buscar modelo
    for part in parts:
        if part.startswith('MOD'):
            info['model'] = part
            break
    
    # Buscar serial (última parte antes de la extensión)
    if 'label' in name and len(parts) > 4:
        info['serial'] = parts[-1]
    
    return info

def view_reports():
    """Muestra estructura de reportes organizados"""
    base_dir = Path(__file__).parent.parent / "reports"
    
    if not base_dir.exists():
        print("[!] Directorio de reportes no encontrado")
        return
    
    print("="*70)
    print("ESTRUCTURA DE REPORTES - ONT/ATA Testing Suite")
    print("="*70)
    print()
    
    # AUTOMATED TESTS
    automated_dir = base_dir / "automated_tests"
    if automated_dir.exists():
        print("📊 REPORTES DE PRUEBAS AUTOMATIZADAS")
        print("-"*70)
        
        date_dirs = sorted([d for d in automated_dir.iterdir() if d.is_dir()])
        
        if not date_dirs:
            print("   (sin reportes)")
        
        total_reports = 0
        for date_dir in date_dirs:
            files = list(date_dir.glob("*.json"))
            
            if files:
                print(f"\n📅 {format_date(date_dir.name)}")
                
                # Agrupar por modelo
                by_model = defaultdict(list)
                for file in files:
                    info = get_file_info(file)
                    by_model[info['model']].append(info)
                
                for model, reports in sorted(by_model.items()):
                    automated = sum(1 for r in reports if r['type'] == 'automated')
                    retest = sum(1 for r in reports if r['type'] == 'retest')
                    
                    parts = []
                    if automated:
                        parts.append(f"{automated} test{'s' if automated != 1 else ''}")
                    if retest:
                        parts.append(f"{retest} retest{'s' if retest != 1 else ''}")
                    
                    print(f"   • {model}: {', '.join(parts)}")
                    total_reports += len(reports)
        
        print(f"\n   Total: {total_reports} reportes")
    
    print()
    
    # LABELS
    labels_dir = base_dir / "labels"
    if labels_dir.exists():
        print("🏷️  ETIQUETAS DE IDENTIFICACIÓN")
        print("-"*70)
        
        date_dirs = sorted([d for d in labels_dir.iterdir() if d.is_dir()])
        
        if not date_dirs:
            print("   (sin etiquetas)")
        
        total_labels = 0
        for date_dir in date_dirs:
            files = list(date_dir.glob("*.txt"))
            
            if files:
                print(f"\n📅 {format_date(date_dir.name)}")
                
                # Agrupar por modelo
                by_model = defaultdict(list)
                for file in files:
                    info = get_file_info(file)
                    if info['model']:
                        by_model[info['model']].append(info)
                
                for model, labels in sorted(by_model.items()):
                    print(f"   • {model}: {len(labels)} etiqueta{'s' if len(labels) != 1 else ''}")
                    total_labels += len(labels)
        
        print(f"\n   Total: {total_labels} etiquetas")
    
    print()
    print("="*70)
    
    # Estadísticas generales
    print("\n📈 ESTADÍSTICAS GENERALES")
    print("-"*70)
    
    # Contar modelos únicos
    all_models = set()
    if automated_dir.exists():
        for date_dir in automated_dir.iterdir():
            if date_dir.is_dir():
                for file in date_dir.glob("*.json"):
                    info = get_file_info(file)
                    if info['model']:
                        all_models.add(info['model'])
    
    if labels_dir.exists():
        for date_dir in labels_dir.iterdir():
            if date_dir.is_dir():
                for file in date_dir.glob("*.txt"):
                    info = get_file_info(file)
                    if info['model']:
                        all_models.add(info['model'])
    
    if all_models:
        print(f"\n   Modelos testeados: {', '.join(sorted(all_models))}")
    
    # Última actividad
    all_dates = set()
    if automated_dir.exists():
        all_dates.update([d.name for d in automated_dir.iterdir() if d.is_dir()])
    if labels_dir.exists():
        all_dates.update([d.name for d in labels_dir.iterdir() if d.is_dir()])
    
    if all_dates:
        latest_date = sorted(all_dates)[-1]
        print(f"   Última actividad: {format_date(latest_date)}")
    
    print()

def view_latest_reports(count: int = 5):
    """Muestra los últimos N reportes generados"""
    base_dir = Path(__file__).parent.parent / "reports" / "automated_tests"
    
    if not base_dir.exists():
        print("[!] No hay reportes disponibles")
        return
    
    print("="*70)
    print(f"ÚLTIMOS {count} REPORTES GENERADOS")
    print("="*70)
    print()
    
    # Recolectar todos los archivos JSON
    all_reports = []
    for date_dir in base_dir.iterdir():
        if date_dir.is_dir():
            for file in date_dir.glob("*.json"):
                all_reports.append(file)
    
    # Ordenar por fecha de modificación
    all_reports.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    for i, report in enumerate(all_reports[:count], 1):
        info = get_file_info(report)
        mod_time = datetime.fromtimestamp(report.stat().st_mtime)
        
        type_icon = "🔄" if info['type'] == 'retest' else "✅"
        
        print(f"{i}. {type_icon} {info['model']} - {info['type'].upper()}")
        print(f"   📁 {report.parent.name}/{report.name}")
        print(f"   🕐 {mod_time.strftime('%d/%m/%Y %H:%M:%S')}")
        print()

def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--latest':
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        view_latest_reports(count)
    else:
        view_reports()

if __name__ == "__main__":
    main()
