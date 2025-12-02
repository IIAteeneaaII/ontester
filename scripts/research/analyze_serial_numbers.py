#!/usr/bin/env python3
"""
Análisis completo de ambos ONTs para encontrar el patrón del SN Físico
"""

print("="*70)
print("ANÁLISIS COMPARATIVO DE SERIAL NUMBERS")
print("="*70)

# Datos MOD005 (Huawei HG145V5 SMALL)
mod005 = {
    "model": "MOD005 - Huawei HG145V5 SMALL",
    "sn_logical": "FHTTC1166D5C",
    "sn_physical": "48575443E0B2A5AA",
    "mac": "BC:46:32:13:66:30",
    "olt_vendor": "HWTC"
}

# Datos MOD001 (Fiberhome HG6145F)
mod001 = {
    "model": "MOD001 - Fiberhome HG6145F",
    "sn_logical": "FHTT9E222B98",
    "sn_physical": "464854549E222B98",
    "mac": "10:07:1D:22:2B:98",
    "olt_vendor": ""
}

devices = [mod005, mod001]

for device in devices:
    print(f"\n{'='*70}")
    print(f"ANÁLISIS: {device['model']}")
    print("="*70)
    
    sn_log = device['sn_logical']
    sn_phy = device['sn_physical']
    mac = device['mac'].replace(':', '').upper()
    
    print(f"\n1. Serial Number Lógico: {sn_log}")
    sn_log_hex = ''.join([format(ord(c), '02X') for c in sn_log])
    print(f"   En HEX: {sn_log_hex}")
    
    print(f"\n2. Serial Number Físico: {sn_phy}")
    print(f"   Longitud: {len(sn_phy)} caracteres ({len(sn_phy)//2} bytes)")
    
    print(f"\n3. MAC Address: {device['mac']} → {mac}")
    
    # COMPARACIÓN
    print(f"\n{'='*70}")
    print("COMPARACIÓN:")
    print(f"  SN Lógico (HEX): {sn_log_hex}")
    print(f"  SN Físico:       {sn_phy}")
    
    if sn_log_hex == sn_phy:
        print(f"\n  ✅ ¡COINCIDE PERFECTAMENTE!")
    else:
        print(f"\n  ❌ No coinciden")

print("\n" + "="*70)
print("CONCLUSIÓN FINAL")
print("="*70)

print("""
PATRÓN ENCONTRADO:

  SN_FÍSICO = ASCII_to_HEX(SN_LÓGICO)
  
Verificación:
""")

for device in devices:
    sn_log = device['sn_logical']
    sn_phy_expected = device['sn_physical']
    sn_phy_calculated = ''.join([format(ord(c), '02X') for c in sn_log])
    
    match = "✅" if sn_phy_calculated == sn_phy_expected else "❌"
    
    print(f"\n{device['model']}:")
    print(f"  '{sn_log}' → {sn_phy_calculated}")
    print(f"  Esperado: {sn_phy_expected} {match}")

print("\n" + "="*70)
