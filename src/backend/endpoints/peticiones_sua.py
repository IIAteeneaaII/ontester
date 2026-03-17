from src.backend.sua_client.sua_acceso import ensure_certs_from_sua, verificar_estado_estacion


def solicitar_registro_sua(mac: str):
    ok = verificar_estado_estacion()
    if ok :
        print("Estación autenticada ok")
    else:
        print(f"SOLICITANDO REGISTRO con el ID: {mac}")
        ok = ensure_certs_from_sua()
        if ok:
            print("solicitud de registro enviada")
        else:
            print("not ok :c")