#!/usr/bin/env python3
"""
Función para calcular Serial Number Físico - MOD001 implementado
"""

def calculate_physical_sn_mod001(sn_logical: str) -> str:
    """
    Calcula SN Físico para MOD001 (Fiberhome HG6145F)
    Patrón: "FHTT"(HEX) + Suffix sin modificar
    """
    if not sn_logical.startswith("FH"):
        return None
    
    prefix = sn_logical[:4]  # "FHTT"
    suffix = sn_logical[4:]   # "9E222B98" (ya en HEX)
    
    prefix_hex = ''.join([format(ord(c), '02X') for c in prefix])
    
    return prefix_hex + suffix


if __name__ == "__main__":
    print("="*60)
    print("CALCULADORA DE SN FÍSICO - MOD001")
    print("="*60)
    
    # Test MOD001
    sn_log = "FHTT9E222B98"
    sn_phy_expected = "464854549E222B98"
    
    calculated = calculate_physical_sn_mod001(sn_log)
    match = "✅ CORRECTO" if calculated == sn_phy_expected else "❌ ERROR"
    
    print(f"\nSN Lógico:           {sn_log}")
    print(f"SN Físico calculado: {calculated}")
    print(f"SN Físico esperado:  {sn_phy_expected}")
    print(f"\nResultado: {match}")
    
    print("\n" + "="*60)
    print("FÓRMULA:")
    print('  SN_Físico = ASCII_to_HEX("FHTT") + Suffix')
    print('  donde Suffix ya está en formato hexadecimal')
    print("="*60)
