from src.backend.sua_client.sua_acceso import ensure_certs_from_sua

def solicitar_registro_sua(mac: str):
    print(f"SOLICITANDO REGISTRO con el ID: {mac}")
    ok = ensure_certs_from_sua()
    if ok:
        print("ok")
    else:
        print("not ok :c")