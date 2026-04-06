from src.backend.sua_client.sua_acceso import ensure_certs_from_sua, verificar_estado_estacion, reclamar_llave_sua


def solicitar_registro_sua(mac: str):
    ok = verificar_estado_estacion()
    if ok :
        print("Estación autenticada ok")
        return None
    else:
        
        
        if reclamar_llave_sua():
            return None
        print(f"SOLICITANDO REGISTRO con el ID: {mac}")
        result = ensure_certs_from_sua()
        if result is True:
            print("solicitud de registro enviada")
            
        elif result is None:
            print("[SUA] Certificados ya existen y estación autenticada, no es necesario solicitar registro")
        else:
            print("not ok :c")

    return result