
def solicitar_registro_sua(mac: str):
    # Primero verificar el registro en la BD
    # Si en stations activo=0, entonces solicitar acceso, sino no hacer nada
    print(f"SOLICITANDO REGISTRO con el ID: {mac}")